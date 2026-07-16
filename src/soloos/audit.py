"""Audit log: JSONL append-only + SQLite index.

Design notes on integrity:
- The JSONL file is the source of truth. The SQLite index is a rebuildable
  cache and MUST NOT be treated as authoritative.
- If the DB write fails after the JSONL append succeeds, we still return the
  content_hash — the JSONL record is durable and the index can be rebuilt
  from disk with `soloos audit reindex`.
- If the file write fails, no DB row is inserted (order: file-first).
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import get_config
from .db import connect

log = logging.getLogger(__name__)


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
    """Append a record to today's JSONL + index in SQLite. Returns content hash.

    Raises OSError only if JSONL append fails. SQLite index failures are
    logged and swallowed (rebuild via reindex).
    """
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
    body_line = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
    content_hash = "sha256:" + hashlib.sha256(body_line.encode("utf-8")).hexdigest()[:16]
    record["hash"] = content_hash
    final_line = json.dumps(record, ensure_ascii=False, separators=(",", ":"))

    path = _today_file()
    # File write is the source of truth. Fsync for durability.
    with path.open("a", encoding="utf-8") as f:
        offset = f.tell()
        f.write(final_line + "\n")
        f.flush()
        try:
            import os as _os
            _os.fsync(f.fileno())
        except (OSError, AttributeError):
            pass  # non-POSIX filesystems

    # Index insert — best-effort.
    try:
        conn = connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                """INSERT OR REPLACE INTO audit_events
                (id, ts, actor, action_type, target, status, policy_rule,
                 cost_krw, file_path, line_offset, content_hash)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (id, ts_epoch, actor, action_type, target, status, policy_rule,
                 cost_krw, str(path), offset, content_hash),
            )
            conn.execute("COMMIT")
        finally:
            conn.close()
    except Exception as exc:  # noqa: BLE001
        log.error("audit index insert failed (JSONL still durable): %s", exc)

    return content_hash


def search(
    *,
    actor: str | None = None,
    action_type: str | None = None,
    since_epoch: int | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    conn = connect()
    try:
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
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_event(event_id: str) -> dict[str, Any] | None:
    """Return the full JSONL audit record, including extras, for an event id."""
    index_row = _get_index_row(event_id)
    if index_row:
        record = _read_jsonl_record(Path(index_row["file_path"]), index_row["line_offset"])
        if record and record.get("id") == event_id:
            return record

    cfg = get_config()
    for jsonl in sorted(cfg.audit_dir().glob("*.jsonl"), reverse=True):
        with jsonl.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if record.get("id") == event_id:
                    return record
    return None


def _get_index_row(event_id: str) -> dict[str, Any] | None:
    conn = connect()
    try:
        row = conn.execute("SELECT * FROM audit_events WHERE id=?", (event_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def _read_jsonl_record(path: Path, offset: int) -> dict[str, Any] | None:
    try:
        with path.open("r", encoding="utf-8") as f:
            f.seek(offset)
            line = f.readline()
    except OSError:
        return None
    try:
        return json.loads(line)
    except json.JSONDecodeError:
        return None


def reindex() -> int:
    """Rebuild audit_events index from JSONL files. Returns records indexed."""
    cfg = get_config()
    conn = connect()
    count = 0
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("DELETE FROM audit_events")
        for jsonl in sorted(cfg.audit_dir().glob("*.jsonl")):
            offset = 0
            with jsonl.open("r", encoding="utf-8") as f:
                for line in f:
                    line_bytes = len(line.encode("utf-8"))
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        offset += line_bytes
                        continue
                    ts_iso = rec.get("ts", "")
                    try:
                        ts_epoch = int(datetime.fromisoformat(ts_iso.replace("Z", "+00:00")).timestamp())
                    except ValueError:
                        ts_epoch = 0
                    conn.execute(
                        """INSERT OR REPLACE INTO audit_events
                        (id, ts, actor, action_type, target, status, policy_rule,
                         cost_krw, file_path, line_offset, content_hash)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                        (
                            rec.get("id"), ts_epoch, rec.get("actor"),
                            rec.get("action_type"), rec.get("target"),
                            rec.get("status"), rec.get("policy_rule"),
                            rec.get("cost_krw", 0),
                            str(jsonl), offset, rec.get("hash"),
                        ),
                    )
                    count += 1
                    offset += line_bytes
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()
    return count
