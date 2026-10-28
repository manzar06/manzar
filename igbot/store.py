"""SQLite storage: de-duplication, DM history, rate limiting and an action log."""

import sqlite3
import threading
import time

from .config import settings

_lock = threading.Lock()
_conn: sqlite3.Connection | None = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS processed (event_id TEXT PRIMARY KEY, ts REAL);
CREATE TABLE IF NOT EXISTS dm_history (sender_id TEXT, role TEXT, text TEXT, ts REAL);
CREATE TABLE IF NOT EXISTS actions (
    ts REAL, kind TEXT, event_id TEXT, user TEXT, text TEXT, sentiment TEXT,
    intent TEXT, action TEXT, reply TEXT, private_reply TEXT, reason TEXT,
    posted INTEGER, error TEXT
);
"""


def conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(settings.db_path, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.executescript(SCHEMA)
    return _conn


def claim(event_id: str) -> bool:
    """Returns True the first time an event is seen. Instagram can deliver webhooks twice."""
    with _lock:
        cur = conn().execute("INSERT OR IGNORE INTO processed VALUES (?, ?)", (event_id, time.time()))
        conn().commit()
        return cur.rowcount == 1


def add_dm(sender_id: str, role: str, text: str) -> None:
    with _lock:
        conn().execute("INSERT INTO dm_history VALUES (?, ?, ?, ?)", (sender_id, role, text, time.time()))
        conn().commit()


def dm_history(sender_id: str, limit: int = 10) -> list[tuple[str, str]]:
    rows = conn().execute(
        "SELECT role, text FROM dm_history WHERE sender_id = ? ORDER BY ts DESC LIMIT ?", (sender_id, limit)
    ).fetchall()
    return [(r["role"], r["text"]) for r in reversed(rows)]


def posts_last_hour() -> int:
    row = conn().execute(
        "SELECT COUNT(*) FROM actions WHERE posted = 1 AND ts > ?", (time.time() - 3600,)
    ).fetchone()
    return row[0]


def log_action(**fields) -> None:
    cols = ["kind", "event_id", "user", "text", "sentiment", "intent", "action",
            "reply", "private_reply", "reason", "posted", "error"]
    values = [time.time()] + [fields.get(c) for c in cols]
    with _lock:
        conn().execute(f"INSERT INTO actions VALUES ({', '.join('?' * len(values))})", values)
        conn().commit()


def recent_actions(limit: int = 50) -> list[dict]:
    rows = conn().execute("SELECT * FROM actions ORDER BY ts DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]
