"""Audit log: JSONL append-only + SQLite index.

Every mutating action must be recorded via `emit()`.
"""
from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import get_config
from .db import connect


def _today_file() -> Path:
    cfg = get_config()
    return cfg.audit_dir() / f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.jsonl"


def emit(
    *,
    id: str,
    actor: str,
    action_type: str,
    target: str | None = None,
    status: str = "success",
    policy_rule: str | None = None,
    cost_krw: int = 0,
    extras: dict[str, Any] | None = None,
) -> str:
    """Append a record to today's JSONL + index in SQLite. Returns content hash."""
    ts_iso = datetime.now(timezone.utc).isoformat()
    ts_epoch = int(time.time())
    record: dict[str, Any] = {
        "ts": ts_iso,
        "id": id,
        "actor": actor,
        "action_type": action_type,
        "target": target,
        "status": status,
        "policy_rule": policy_rule,
        "cost_krw": cost_krw,
    }
    if extras:
        record["extras"] = extras
    line = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
    content_hash = "sha256:" + hashlib.sha256(line.encode("utf-8")).hexdigest()[:16]
    record["hash"] = content_hash
    line = json.dumps(record, ensure_ascii=False, separators=(",", ":"))

    path = _today_file()
    with path.open("a", encoding="utf-8") as f:
        offset = f.tell()
        f.write(line + "\n")

    conn = connect()
    with conn:
        conn.execute(
            """INSERT OR REPLACE INTO audit_events
            (id, ts, actor, action_type, target, status, policy_rule, cost_krw, file_path, line_offset, content_hash)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (id, ts_epoch, actor, action_type, target, status, policy_rule, cost_krw, str(path), offset, content_hash),
        )
    conn.close()
    return content_hash


def search(
    *,
    actor: str | None = None,
    action_type: str | None = None,
    since_epoch: int | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    conn = connect()
    q = "SELECT * FROM audit_events WHERE 1=1"
    params: list[Any] = []
    if actor:
        q += " AND actor = ?"
        params.append(actor)
    if action_type:
        q += " AND action_type = ?"
        params.append(action_type)
    if since_epoch:
        q += " AND ts >= ?"
        params.append(since_epoch)
    q += " ORDER BY ts DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]
