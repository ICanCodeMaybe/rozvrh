import os
import sqlite3

DEFAULT_DB_PATH = "./rozvrh.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS blocks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    start       TEXT NOT NULL,
    end         TEXT NOT NULL,
    label       TEXT NOT NULL DEFAULT '',
    color       TEXT NOT NULL DEFAULT '#4a90d9',
    source      TEXT NOT NULL DEFAULT 'ui'
);
"""


def get_db_path() -> str:
    return os.environ.get("ROZVRH_DB", DEFAULT_DB_PATH)


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    conn = connect()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def list_blocks_in_range(conn: sqlite3.Connection, start: str, end: str) -> list[sqlite3.Row]:
    # overlap = block.start < range_end AND block.end > range_start
    return conn.execute(
        "SELECT * FROM blocks WHERE start < ? AND end > ? ORDER BY start, id",
        (end, start),
    ).fetchall()


def get_block(conn: sqlite3.Connection, block_id: int) -> sqlite3.Row | None:
    row = conn.execute("SELECT * FROM blocks WHERE id = ?", (block_id,)).fetchone()
    assert row is None or isinstance(row, sqlite3.Row)
    return row


def insert_block(
    conn: sqlite3.Connection, start: str, end: str, label: str, color: str
) -> sqlite3.Row:
    cur = conn.execute(
        "INSERT INTO blocks (start, end, label, color) VALUES (?, ?, ?, ?)",
        (start, end, label, color),
    )
    conn.commit()
    assert cur.lastrowid is not None
    row = get_block(conn, cur.lastrowid)
    assert row is not None, "inserted block vanished"
    return row


def update_block(
    conn: sqlite3.Connection,
    block_id: int,
    fields: dict[str, str],
) -> sqlite3.Row | None:
    # keys become SQL column names; callers must pass only model_dump() keys,
    # never user-controlled strings
    sets = ", ".join(f"{name} = ?" for name in fields)
    params = list(fields.values()) + [block_id]
    conn.execute(f"UPDATE blocks SET {sets} WHERE id = ?", params)
    conn.commit()
    return get_block(conn, block_id)


def delete_block(conn: sqlite3.Connection, block_id: int) -> bool:
    cur = conn.execute("DELETE FROM blocks WHERE id = ?", (block_id,))
    conn.commit()
    return cur.rowcount > 0
