import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query

from backend import db
from backend.auth import require_api_key
from backend.models import TODO_SOURCE, BlockIn, BlockOut, BlockPatch

router = APIRouter(prefix="/api/blocks", dependencies=[Depends(require_api_key)])


def row_to_out(row: sqlite3.Row) -> BlockOut:
    return BlockOut(
        id=row["id"],
        start=row["start"],
        end=row["end"],
        label=row["label"],
        color=row["color"],
        source=row["source"],
    )


@router.get("", response_model=list[BlockOut])
def list_blocks(
    start: str = Query(alias="from"),
    end: str = Query(alias="to"),
) -> list[BlockOut]:
    if start >= end:
        raise HTTPException(status_code=422, detail="from must be before to")
    conn = db.connect()
    try:
        rows = db.list_blocks_in_range(conn, start, end)
        return [row_to_out(row) for row in rows]
    finally:
        conn.close()


@router.post("", response_model=BlockOut, status_code=201)
def create_block(block: BlockIn) -> BlockOut:
    # Unscheduled parking-lot blocks are stored as a zero-length sentinel.
    if block.source == TODO_SOURCE:
        block = block.model_copy(update={"end": block.start})
    elif block.end == block.start:
        raise HTTPException(status_code=422, detail="end must be after start")
    conn = db.connect()
    try:
        row = db.insert_block(
            conn,
            start=block.start,
            end=block.end,
            label=block.label,
            color=block.color,
            source=block.source,
        )
        return row_to_out(row)
    finally:
        conn.close()


@router.patch("/{block_id}", response_model=BlockOut)
def patch_block(block_id: int, patch: BlockPatch) -> BlockOut:
    fields = {k: v for k, v in patch.model_dump().items() if v is not None}
    if not fields:
        raise HTTPException(status_code=422, detail="no fields to update")
    conn = db.connect()
    try:
        row = db.get_block(conn, block_id)
        if row is None:
            raise HTTPException(status_code=404, detail="block not found")
        # Scheduling a TODO block means clearing the sentinel: drop the source
        # marker and let start/end move it onto the grid. Unscheduling (source
        # -> todo) collapses the block back to the zero-length sentinel at its
        # current start.
        if fields.get("source") == TODO_SOURCE and "start" not in fields and "end" not in fields:
            fields["end"] = row["start"]
        if "start" in fields or "end" in fields:
            if row["source"] == TODO_SOURCE:
                fields.setdefault("source", "ui")
                fields["end"] = fields.get("end", fields["start"])
            start = fields.get("start", row["start"])
            end = fields.get("end", row["end"])
            if end <= start and fields.get("source") != TODO_SOURCE:
                raise HTTPException(status_code=422, detail="end must be after start")
        row = db.update_block(conn, block_id, fields)
        assert row is not None, "block vanished during update"
        return row_to_out(row)
    finally:
        conn.close()


@router.delete("/{block_id}", status_code=204)
def delete_block(block_id: int) -> None:
    conn = db.connect()
    try:
        if not db.delete_block(conn, block_id):
            raise HTTPException(status_code=404, detail="block not found")
    finally:
        conn.close()


@router.get("/todo", response_model=list[BlockOut])
def list_todo_blocks() -> list[BlockOut]:
    conn = db.connect()
    try:
        return [row_to_out(row) for row in db.list_todo_blocks(conn)]
    finally:
        conn.close()
