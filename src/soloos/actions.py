"""Actions queue and minimal executor.

MVP M3 bridge: pulls `actions.status='pending'`, marks running, executes a
safe stub, then marks success/failed and emits audit.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

from . import audit
from .agents import AgentRecord, AgentsService
from .db import connect
from .ids import next_id
from .workflow import WorkflowService


@dataclass(frozen=True)
class ActionRecord:
    id: str
    ts: int
    actor: str
    action_type: str
    target: str | None
    params: dict[str, Any]
    policy_rule: str | None
    status: str
    cost_krw: int
    created_at: int | None
    completed_at: int | None
    latency_ms: int | None


@dataclass(frozen=True)
class ActionRunResult:
    id: str
    status: str
    output: str
    latency_ms: int


class ActionsService:
    """Queue reader + single-action executor."""

    def next_pending(self) -> ActionRecord | None:
        conn = connect()
        try:
            row = conn.execute(
                "SELECT * FROM actions WHERE status='pending' ORDER BY ts ASC, id ASC LIMIT 1"
            ).fetchone()
        finally:
            conn.close()
        return _row_to_action(row) if row else None

    def run_one(self) -> ActionRunResult | None:
        action = self._claim_next_pending()
        if action is None:
            return None

        started = time.perf_counter()
        snapshot_ref = None
        try:
            output, snapshot_ref = execute_agent(action)
            status = "success"
        except Exception as exc:  # noqa: BLE001
            output = f"agent execution failed: {exc}"
            status = "failed"
        latency_ms = int((time.perf_counter() - started) * 1000)
        completed_at = int(time.time())

        conn = connect()
        try:
            conn.execute(
                """UPDATE actions
                SET status=?, latency_ms=?, completed_at=?, snapshot_ref=?
                WHERE id=?""",
                (status, latency_ms, completed_at, snapshot_ref, action.id),
            )
        finally:
            conn.close()

        audit.emit(
            id=next_id("A"),
            actor="system:actions",
            action_type="action_run",
            target=f"action:{action.id}",
            status=status,
            policy_rule=action.policy_rule,
            cost_krw=action.cost_krw,
            extras={"output": output, "latency_ms": latency_ms, "snapshot_ref": snapshot_ref},
        )
        return ActionRunResult(action.id, status, output, latency_ms)

    def _claim_next_pending(self) -> ActionRecord | None:
        conn = connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT * FROM actions WHERE status='pending' ORDER BY ts ASC, id ASC LIMIT 1"
            ).fetchone()
            if row is None:
                conn.execute("COMMIT")
                return None
            now = int(time.time())
            conn.execute(
                "UPDATE actions SET status='running' WHERE id=? AND status='pending'",
                (row["id"],),
            )
            claimed = conn.execute("SELECT * FROM actions WHERE id=?", (row["id"],)).fetchone()
            conn.execute("COMMIT")
            action = _row_to_action(claimed)
            return ActionRecord(
                id=action.id,
                ts=action.ts,
                actor=action.actor,
                action_type=action.action_type,
                target=action.target,
                params=action.params,
                policy_rule=action.policy_rule,
                status="running",
                cost_krw=action.cost_krw,
                created_at=action.created_at or now,
                completed_at=action.completed_at,
                latency_ms=action.latency_ms,
            )
        except Exception:
            try:
                conn.execute("ROLLBACK")
            except Exception:
                pass
            raise
        finally:
            conn.close()


def execute_agent(action: ActionRecord) -> tuple[str, str]:
    """Dispatch a claimed action to the currently seeded active agent handler."""
    agent = AgentsService().get_active(action.actor)
    if agent is None:
        raise RuntimeError(f"active agent not found: {action.actor}")
    return execute_stub(action, agent)


def execute_stub(action: ActionRecord, agent: AgentRecord) -> tuple[str, str]:
    """Safe MVP per-agent executor placeholder until real runners exist."""
    if agent.id == "agent:growth" and action.action_type == "content_plan":
        workflow = WorkflowService().create_content_plan(
            source_action_id=action.id,
            actor=action.actor,
            params=action.params,
        )
        output = f"{agent.name} workflow {workflow.id} created with {workflow.step_count} pending draft_content step(s)"
        return output, f"workflow://{workflow.id}"

    slug = agent.id.removeprefix("agent:")
    output = f"{agent.name} stub executed {action.action_type} with params={json.dumps(action.params, ensure_ascii=False, sort_keys=True)}"
    snapshot_ref = f"agent-stub://{slug}/{action.id}"
    return output, snapshot_ref


def _row_to_action(row: Any) -> ActionRecord:
    return ActionRecord(
        id=row["id"],
        ts=row["ts"],
        actor=row["actor"],
        action_type=row["action_type"],
        target=row["target"],
        params=json.loads(row["params_json"] or "{}"),
        policy_rule=row["policy_rule"],
        status=row["status"],
        cost_krw=row["cost_krw"] or 0,
        created_at=row["created_at"],
        completed_at=row["completed_at"],
        latency_ms=row["latency_ms"],
    )
