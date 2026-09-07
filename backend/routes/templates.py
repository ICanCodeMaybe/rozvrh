import sqlite3
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ValidationInfo, field_validator

from backend import db
from backend.auth import require_api_key
from backend.models import BlockOut, validate_color, validate_label
from backend.routes.blocks import row_to_out
from backend.routes.weeks import resolve_week_or_422, week_bounds, week_bounds_iso

router = APIRouter(prefix="/api/templates", dependencies=[Depends(require_api_key)])


class TemplateBlockIn(BaseModel):
    day_of_week: int
    start_time: str
    end_time: str
    label: str = ""
    color: str = "#4a90d9"

    @field_validator("day_of_week")
    @classmethod
    def valid_day(cls, value: int) -> int:
        if not 0 <= value <= 6:
            raise ValueError("day_of_week must be 0 (Mon)..6 (Sun)")
        return value

    @field_validator("start_time", "end_time")
    @classmethod
    def valid_hhmm(cls, value: str) -> str:
        if len(value) != 5 or value[2] != ":":
            raise ValueError("must be HH:MM")
        hh, mm = value.split(":")
        if not (hh.isdigit() and mm.isdigit() and 0 <= int(hh) <= 23 and int(mm) <= 59):
            raise ValueError(f"invalid time: {value}")
        return value

    @field_validator("end_time")
    @classmethod
    def end_after_start(cls, end: str, info: ValidationInfo) -> str:
        start = info.data.get("start_time")
        if start is not None and end <= start:
            raise ValueError("end_time must be after start_time")
        return end

    @field_validator("label")
    @classmethod
    def label_not_too_long(cls, value: str) -> str:
        return validate_label(value)

    @field_validator("color")
    @classmethod
    def color_is_hex(cls, value: str) -> str:
        return validate_color(value)


class TemplateIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    blocks: list[TemplateBlockIn]


class TemplateBlockOut(TemplateBlockIn):
    id: int


class TemplateOut(BaseModel):
    id: int
    name: str
    blocks: list[TemplateBlockOut]


def insert_template_blocks(
    conn: sqlite3.Connection, template_id: int, blocks: list[TemplateBlockIn]
) -> None:
    conn.executemany(
        "INSERT INTO template_blocks"
        " (template_id, day_of_week, start_time, end_time, label, color)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        [
            (template_id, b.day_of_week, b.start_time, b.end_time, b.label, b.color)
            for b in blocks
        ],
    )


def template_block_rows(conn: sqlite3.Connection, template_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM template_blocks WHERE template_id = ? ORDER BY day_of_week, start_time, id",
        (template_id,),
    ).fetchall()


def get_template(conn: sqlite3.Connection, template_id: int) -> sqlite3.Row | None:
    row = conn.execute("SELECT * FROM templates WHERE id = ?", (template_id,)).fetchone()
    assert row is None or isinstance(row, sqlite3.Row)
    return row


def to_out(conn: sqlite3.Connection, template_row: sqlite3.Row) -> TemplateOut:
    blocks = [
        TemplateBlockOut(
            id=row["id"],
            day_of_week=row["day_of_week"],
            start_time=row["start_time"],
            end_time=row["end_time"],
            label=row["label"],
            color=row["color"],
        )
        for row in template_block_rows(conn, template_row["id"])
    ]
    return TemplateOut(id=template_row["id"], name=template_row["name"], blocks=blocks)


@router.get("", response_model=list[TemplateOut])
def list_templates() -> list[TemplateOut]:
    conn = db.connect()
    try:
        rows = conn.execute("SELECT * FROM templates ORDER BY name").fetchall()
        return [to_out(conn, row) for row in rows]
    finally:
        conn.close()


@router.post("", response_model=TemplateOut, status_code=201)
def create_template(template: TemplateIn) -> TemplateOut:
    conn = db.connect()
    try:
        cur = conn.execute("INSERT INTO templates (name) VALUES (?)", (template.name,))
        template_id = cur.lastrowid
        assert template_id is not None
        insert_template_blocks(conn, template_id, template.blocks)
        conn.commit()
        row = get_template(conn, template_id)
        assert row is not None, "inserted template vanished"
        return to_out(conn, row)
    finally:
        conn.close()


@router.put("/{template_id}", response_model=TemplateOut)
def replace_template(template_id: int, template: TemplateIn) -> TemplateOut:
    conn = db.connect()
    try:
        row = get_template(conn, template_id)
        if row is None:
            raise HTTPException(status_code=404, detail="template not found")
        conn.execute("UPDATE templates SET name = ? WHERE id = ?", (template.name, template_id))
        conn.execute("DELETE FROM template_blocks WHERE template_id = ?", (template_id,))
        insert_template_blocks(conn, template_id, template.blocks)
        conn.commit()
        row = get_template(conn, template_id)
        assert row is not None, "template vanished during update"
        return to_out(conn, row)
    finally:
        conn.close()


@router.delete("/{template_id}", status_code=204)
def delete_template(template_id: int) -> None:
    conn = db.connect()
    try:
        cur = conn.execute("DELETE FROM templates WHERE id = ?", (template_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="template not found")
        conn.execute("DELETE FROM template_blocks WHERE template_id = ?", (template_id,))
        conn.commit()
    finally:
        conn.close()


@router.post("/{template_id}/apply/{iso_year}/{iso_week}", response_model=list[BlockOut])
def apply_template(template_id: int, iso_year: int, iso_week: int) -> list[BlockOut]:
    resolve_week_or_422(iso_year, iso_week)
    conn = db.connect()
    try:
        template = get_template(conn, template_id)
        if template is None:
            raise HTTPException(status_code=404, detail="template not found")
        week_start, _ = week_bounds(iso_year, iso_week)
        # overlap = any intersection with an existing block
        start_iso, end_iso = week_bounds_iso(iso_year, iso_week)
        existing = db.list_blocks_in_range(conn, start_iso, end_iso)
        created: list[BlockOut] = []
        for row in template_block_rows(conn, template_id):
            day = date.fromordinal(week_start.toordinal() + row["day_of_week"])
            start = day.isoformat() + "T" + row["start_time"]
            end = day.isoformat() + "T" + row["end_time"]
            if any(start < ex["end"] and end > ex["start"] for ex in existing):
                continue
            inserted = db.insert_block(conn, start, end, row["label"], row["color"])
            created.append(row_to_out(inserted))
            existing.append(inserted)
        return created
    finally:
        conn.close()
