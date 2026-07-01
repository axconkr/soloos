"""Sequential ID generator for domain entities (A-, AP-, C-, D-, ...)."""
from __future__ import annotations

from .db import connect

_COUNTER_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS id_counters (
  prefix TEXT PRIMARY KEY,
  next_value INTEGER NOT NULL DEFAULT 1
)
"""


def next_id(prefix: str) -> str:
    conn = connect()
    with conn:
        conn.execute(_COUNTER_TABLE_SQL)
        conn.execute("INSERT OR IGNORE INTO id_counters (prefix) VALUES (?)", (prefix,))
        row = conn.execute("SELECT next_value FROM id_counters WHERE prefix = ?", (prefix,)).fetchone()
        current = row["next_value"]
        conn.execute("UPDATE id_counters SET next_value = next_value + 1 WHERE prefix = ?", (prefix,))
    conn.close()
    return f"{prefix}-{current:04d}"
