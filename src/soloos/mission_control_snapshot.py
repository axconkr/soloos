"""Export live SoloOS runtime state for the web Mission Control dashboard."""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

from .config import get_config

RUNTIME_TABLES = ("agents", "actions", "workflows", "workflow_steps", "approvals", "audit_events")


def export_snapshot(
    *,
    db_path: Path | None = None,
    out_path: Path | None = None,
    limit: int = 25,
) -> dict[str, Any]:
    """Read SoloOS SQLite state and write a browser-readable JSON snapshot."""
    cfg = get_config(reload=True)
    db_path = db_path or cfg.db_path
    out_path = out_path or Path("apps/web/public/soloos-snapshot.json")
    out_path = Path(out_path)

    snapshot: dict[str, Any] = {
        "generated_at": int(time.time()),
        "db_path": str(Path(db_path).resolve()),
        "counts": {},
        "agents": [],
        "actions": [],
        "workflows": [],
        "workflow_steps": [],
        "approvals": [],
        "audit_events": [],
    }

    if not Path(db_path).exists():
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
        return snapshot

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        for table in RUNTIME_TABLES:
            snapshot["counts"][table] = _count(conn, table)
        snapshot["agents"] = _rows(
            conn,
            """SELECT id, name, mission, tier, tone, authority_json, kpi_json,
                      skills_json, status, updated_at
               FROM agents ORDER BY id LIMIT ?""",
            (limit,),
            json_fields=("authority_json", "kpi_json", "skills_json"),
        )
        snapshot["actions"] = _rows(
            conn,
            """SELECT id, ts, actor, action_type, target, params_json, policy_rule,
                      status, cost_krw, latency_ms, snapshot_ref, created_at, completed_at
               FROM actions ORDER BY ts DESC, id DESC LIMIT ?""",
            (limit,),
            json_fields=("params_json",),
        )
        snapshot["workflows"] = _rows(
            conn,
            """SELECT id, created_at, updated_at, source_action_id, actor,
                      workflow_type, title, params_json, status
               FROM workflows ORDER BY created_at DESC, id DESC LIMIT ?""",
            (limit,),
            json_fields=("params_json",),
        )
        snapshot["workflow_steps"] = _rows(
            conn,
            """SELECT id, workflow_id, step_order, actor, action_type, target,
                      params_json, status, created_at, completed_at, output_ref, output_text
               FROM workflow_steps ORDER BY created_at DESC, step_order ASC LIMIT ?""",
            (limit,),
            json_fields=("params_json",),
        )
        snapshot["approvals"] = _rows(
            conn,
            """SELECT id, created_at, agent_id, action_type, target, preview_url,
                      cost_krw, risk, policy_rule, status, decided_at, decided_by,
                      comment, audit_id, params_json
               FROM approvals ORDER BY created_at DESC, id DESC LIMIT ?""",
            (limit,),
            json_fields=("params_json",),
        )
        snapshot["audit_events"] = _rows(
            conn,
            """SELECT id, ts, actor, action_type, target, status, policy_rule,
                      cost_krw, file_path, line_offset, content_hash
               FROM audit_events ORDER BY ts DESC, id DESC LIMIT ?""",
            (limit,),
        )
    finally:
        conn.close()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    return snapshot


def _count(conn: sqlite3.Connection, table: str) -> int:
    try:
        return int(conn.execute(f"SELECT COUNT(*) AS c FROM {table}").fetchone()["c"])
    except sqlite3.Error:
        return 0


def _rows(
    conn: sqlite3.Connection,
    sql: str,
    params: tuple[Any, ...] = (),
    *,
    json_fields: tuple[str, ...] = (),
) -> list[dict[str, Any]]:
    try:
        rows = conn.execute(sql, params).fetchall()
    except sqlite3.Error:
        return []
    return [_decode_json_fields(dict(row), json_fields) for row in rows]


def _decode_json_fields(row: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    for field in fields:
        if field not in row:
            continue
        value = row[field]
        alias = field.removesuffix("_json")
        try:
            row[alias] = json.loads(value or ("[]" if field == "skills_json" else "{}"))
        except json.JSONDecodeError:
            row[alias] = value
        del row[field]
    return row
