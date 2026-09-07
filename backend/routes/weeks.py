from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException

from backend import db
from backend.auth import require_api_key
from backend.models import BlockOut
from backend.routes.blocks import row_to_out

router = APIRouter(prefix="/api/weeks", dependencies=[Depends(require_api_key)])


def iso_week_start(year: int, week: int) -> date:
    # ISO week 1 is the week containing the first Thursday of the year;
    # Jan 4 always lies in ISO week 1.
    jan4 = date(year, 1, 4)
    week1_monday = jan4 - timedelta(days=jan4.isoweekday() - 1)
    return week1_monday + timedelta(weeks=week - 1)


def week_bounds(year: int, week: int) -> tuple[date, date]:
    start = iso_week_start(year, week)
    return start, start + timedelta(days=7)


def week_bounds_iso(year: int, week: int) -> tuple[str, str]:
    """Week bounds as the ISO datetime strings the blocks table stores."""
    start, end = week_bounds(year, week)
    return start.isoformat() + "T00:00", end.isoformat() + "T00:00"


def resolve_week_or_422(iso_year: int, iso_week: int) -> tuple[date, date]:
    """Validated week bounds; raises the shared 422s for bad week numbers."""
    if not 1 <= iso_week <= 53:
        raise HTTPException(status_code=422, detail="iso_week must be 1..53")
    week_start, week_end = week_bounds(iso_year, iso_week)
    if week_start.isocalendar()[0] != iso_year:
        raise HTTPException(status_code=422, detail="iso_week does not exist in that year")
    return week_start, week_end


@router.get("/{iso_year}/{iso_week}", response_model=list[BlockOut])
def get_week(iso_year: int, iso_week: int) -> list[BlockOut]:
    resolve_week_or_422(iso_year, iso_week)
    conn = db.connect()
    try:
        start_iso, end_iso = week_bounds_iso(iso_year, iso_week)
        rows = db.list_blocks_in_range(conn, start_iso, end_iso)
        return [row_to_out(row) for row in rows]
    finally:
        conn.close()
