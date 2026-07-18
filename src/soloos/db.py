"""SQLite connection + migration runner."""
from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path

from .config import get_config

_ENV_MIG = os.getenv("SOLOOS_MIGRATIONS_DIR")
MIGRATIONS_DIR = Path(_ENV_MIG) if _ENV_MIG else Path(__file__).resolve().parents[2] / "migrations"


def connect() -> sqlite3.Connection:
    cfg = get_config()
    # timeout=10s to survive short WAL contention during concurrent tests/scripts
    conn = sqlite3.connect(str(cfg.db_path), timeout=10.0, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=10000")
    return conn


def _applied_versions(conn: sqlite3.Connection) -> set[int]:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations "
        "(version INTEGER PRIMARY KEY, applied_at INTEGER NOT NULL, description TEXT)"
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
        try:
            version = int(f.stem.split("_", 1)[0])
        except ValueError:
            continue
        if version in applied:
            continue
        sql = f.read_text(encoding="utf-8")
        desc = f.stem.split("_", 1)[1] if "_" in f.stem else f.stem
        # sqlite3.executescript() implicitly commits before running the script,
        # so an outer BEGIN/COMMIT would leave no active transaction. Migrations
        # are bootstrap-only; each migration file is idempotent and the version
        # marker is inserted immediately after a successful script run.
        conn.executescript(sql)
        conn.execute(
            "INSERT INTO schema_migrations (version, applied_at, description) VALUES (?,?,?)",
            (version, int(time.time()), desc),
        )
        newly_applied.append(version)
    conn.close()
    return newly_applied
