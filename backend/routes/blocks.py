import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query

from backend import db
from backend.auth import require_api_key
from backend.models import BlockIn, BlockOut, BlockPatch

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
    conn = db.connect()
    try:
        row = db.insert_block(conn, block.start, block.end, block.label, block.color)
        return row_to_out(row)
    finally:
        conn.close()


@router.patch("/{block_id}", response_model=BlockOut)
def patch_block(block_id: int, patch: BlockPatch) -> BlockOut:
    fields = {k: v for k, v in patch.model_dump().items() if v is not None}
    if not fields:
        raise HTTPException(status_code=422, detail="no fields to update")
    if "start" in fields and "end" in fields and fields["end"] <= fields["start"]:
        raise HTTPException(status_code=422, detail="end must be after start")
    conn = db.connect()
    try:
        row = db.get_block(conn, block_id)
        if row is None:
            raise HTTPException(status_code=404, detail="block not found")
        if "start" in fields or "end" in fields:
            start = fields.get("start", row["start"])
            end = fields.get("end", row["end"])
            if end <= start:
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
