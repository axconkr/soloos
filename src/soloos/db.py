"""SQLite connection + migration runner."""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path

from .config import get_config

import os

_ENV_MIG = os.getenv("SOLOOS_MIGRATIONS_DIR")
MIGRATIONS_DIR = Path(_ENV_MIG) if _ENV_MIG else Path(__file__).resolve().parents[2] / "migrations"


def connect() -> sqlite3.Connection:
    cfg = get_config()
    conn = sqlite3.connect(str(cfg.db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _applied_versions(conn: sqlite3.Connection) -> set[int]:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, applied_at INTEGER NOT NULL, description TEXT)"
    )
    rows = conn.execute("SELECT version FROM schema_migrations").fetchall()
    return {r["version"] for r in rows}


def migrate(migrations_dir: Path = MIGRATIONS_DIR) -> list[int]:
    """Apply all pending migrations. Returns list of applied versions."""
    conn = connect()
    applied = _applied_versions(conn)
    files = sorted(migrations_dir.glob("*.sql"))
    newly_applied: list[int] = []
    for f in files:
        # filename format: 0001_description.sql
        try:
            version = int(f.stem.split("_", 1)[0])
        except ValueError:
            continue
        if version in applied:
            continue
        sql = f.read_text(encoding="utf-8")
        desc = f.stem.split("_", 1)[1] if "_" in f.stem else f.stem
        with conn:
            conn.executescript(sql)
            conn.execute(
                "INSERT INTO schema_migrations (version, applied_at, description) VALUES (?,?,?)",
                (version, int(time.time()), desc),
            )
        newly_applied.append(version)
    conn.close()
    return newly_applied
