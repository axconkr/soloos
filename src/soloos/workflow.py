"""Minimal Workflow Engine service.

MVP scope: create ordered workflow steps from an agent action so the executor can
move from a single success flag to a visible multi-step queue.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

from . import audit
from .agent_runner import AgentRunner, DraftContentRequest, default_agent_runner
from .config import get_config
from .db import connect
from .ids import next_id


@dataclass(frozen=True)
class WorkflowRecord:
    id: str
    created_at: int
    updated_at: int
    source_action_id: str | None
    actor: str
    workflow_type: str
    title: str | None
    params: dict[str, Any]
    status: str
    step_count: int


@dataclass(frozen=True)
class WorkflowStepRecord:
    id: str
    workflow_id: str
    step_order: int
    actor: str
    action_type: str
    target: str | None
    params: dict[str, Any]
    status: str
    created_at: int
    completed_at: int | None
    output_ref: str | None = None
    output_text: str | None = None


@dataclass(frozen=True)
class WorkflowStepRunResult:
    workflow_id: str
    step_id: str
    step_order: int
    status: str
    output: str
    output_ref: str


@dataclass(frozen=True)
class StepExecutionOutput:
    text: str
    ref: str
    runner: str = "deterministic"
    warning: str | None = None


class WorkflowService:

    """Create and inspect simple ordered workflows."""

    def __init__(self, agent_runner: AgentRunner | None = None) -> None:
        self.agent_runner = agent_runner or default_agent_runner()

    def create_content_plan(
        self,
        *,
        source_action_id: str,
        actor: str,
        params: dict[str, Any],
    ) -> WorkflowRecord:
        count = int(params.get("count") or 1)
        if count < 1:
            count = 1
        workflow_id = next_id("WF")
        step_ids = [next_id("WS") for _ in range(count)]
        now = int(time.time())
        title = _content_workflow_title(params, count)
        params_json = json.dumps(params, ensure_ascii=False, sort_keys=True)

        conn = connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                """INSERT INTO workflows
                (id, created_at, updated_at, source_action_id, actor, workflow_type,
                 title, params_json, status)
                VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    workflow_id,
                    now,
                    now,
                    source_action_id,
                    actor,
                    "content_plan",
                    title,
                    params_json,
                    "pending",
                ),
            )
            for step_order in range(1, count + 1):
                step_params = {
                    "title": f"Blog draft {step_order}",
                    "type": params.get("type", "content"),
                    "period": params.get("period"),
                    "source_action_id": source_action_id,
                }
                conn.execute(
                    """INSERT INTO workflow_steps
                    (id, workflow_id, step_order, actor, action_type, target,
                     params_json, status, created_at)
                    VALUES (?,?,?,?,?,?,?,?,?)""",
                    (
                        step_ids[step_order - 1],
                        workflow_id,
                        step_order,
                        actor,
                        "draft_content",
                        f"workflow:{workflow_id}:step:{step_order}",
                        json.dumps(step_params, ensure_ascii=False, sort_keys=True),
                        "pending",
                        now,
                    ),
                )
            conn.execute("COMMIT")
        except Exception:
            try:
                conn.execute("ROLLBACK")
            except Exception:
                pass
            raise
        finally:
            conn.close()

        return WorkflowRecord(
            id=workflow_id,
            created_at=now,
            updated_at=now,
            source_action_id=source_action_id,
            actor=actor,
            workflow_type="content_plan",
            title=title,
            params=params,
            status="pending",
            step_count=count,
        )

    def list_workflows(self, *, limit: int = 20) -> list[WorkflowRecord]:
        conn = connect()
        try:
            rows = conn.execute(
                """SELECT w.*, COUNT(s.id) AS step_count
                FROM workflows w
                LEFT JOIN workflow_steps s ON s.workflow_id = w.id
                GROUP BY w.id
                ORDER BY w.created_at DESC, w.id DESC
                LIMIT ?""",
                (limit,),
            ).fetchall()
        finally:
            conn.close()
        return [_row_to_workflow(row) for row in rows]

    def list_steps(self, workflow_id: str) -> list[WorkflowStepRecord]:
        conn = connect()
        try:
            rows = conn.execute(
                "SELECT * FROM workflow_steps WHERE workflow_id=? ORDER BY step_order",
                (workflow_id,),
            ).fetchall()
        finally:
            conn.close()
        return [_row_to_step(row) for row in rows]

    def run_next_step(self, workflow_id: str) -> WorkflowStepRunResult | None:
        """Run the oldest pending step for a workflow and update workflow status."""
        step = self._claim_next_pending_step(workflow_id)
        if step is None:
            return None

        now = int(time.time())
        try:
            step_output = execute_step_stub(step, agent_runner=self.agent_runner)
            output = step_output.text
            output_ref = step_output.ref
            runner = step_output.runner
            runner_warning = step_output.warning
            status = "success"
        except Exception as exc:  # noqa: BLE001
            output = f"Step execution failed: {exc}"
            output_ref = f"workflow-output://{workflow_id}/{step.id}/failed"
            runner = "unknown"
            runner_warning = None
            status = "failed"

        conn = connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                """UPDATE workflow_steps
                SET status=?, completed_at=?, output_ref=?, output_text=?
                WHERE id=?""",
                (status, now, output_ref, output, step.id),
            )
            if status == "failed":
                workflow_status = "failed"
            else:
                pending_count = conn.execute(
                    """SELECT COUNT(*) AS c FROM workflow_steps
                    WHERE workflow_id=? AND status IN ('pending','running')""",
                    (workflow_id,),
                ).fetchone()["c"]
                workflow_status = "success" if pending_count == 0 else "running"
            conn.execute(
                "UPDATE workflows SET status=?, updated_at=? WHERE id=?",
                (workflow_status, now, workflow_id),
            )
            conn.execute("COMMIT")
        except Exception:
            try:
                conn.execute("ROLLBACK")
            except Exception:
                pass
            raise
        finally:
            conn.close()

        audit_extras = {
            "workflow_id": workflow_id,
            "step_id": step.id,
            "step_order": step.step_order,
            "step_action_type": step.action_type,
            "output_ref": output_ref,
            "output": output,
            "runner": runner,
        }
        if runner_warning:
            audit_extras["runner_warning"] = runner_warning

        audit.emit(
            id=f"STEP-{step.id}",
            actor=step.actor,
            action_type="workflow_step_run",
            target=f"workflow:{workflow_id}:step:{step.id}",
            status=status,
            extras=audit_extras,
        )

        return WorkflowStepRunResult(
            workflow_id=workflow_id,
            step_id=step.id,
            step_order=step.step_order,
            status=status,
            output=output,
            output_ref=output_ref,
        )

    def retry_step(self, workflow_id: str, step_id: str) -> WorkflowStepRecord | None:
        """Reset a failed workflow step to pending so the executor can run it again."""
        now = int(time.time())
        conn = connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                """SELECT * FROM workflow_steps
                WHERE workflow_id=? AND id=? AND status='failed'""",
                (workflow_id, step_id),
            ).fetchone()
            if row is None:
                conn.execute("COMMIT")
                return None
            conn.execute(
                """UPDATE workflow_steps
                SET status='pending', completed_at=NULL, output_ref=NULL, output_text=NULL
                WHERE workflow_id=? AND id=? AND status='failed'""",
                (workflow_id, step_id),
            )
            conn.execute(
                "UPDATE workflows SET status='pending', updated_at=? WHERE id=?",
                (now, workflow_id),
            )
            updated = conn.execute(
                "SELECT * FROM workflow_steps WHERE workflow_id=? AND id=?",
                (workflow_id, step_id),
            ).fetchone()
            conn.execute("COMMIT")
        except Exception:
            try:
                conn.execute("ROLLBACK")
            except Exception:
                pass
            raise
        finally:
            conn.close()

        retried = _row_to_step(updated)
        audit.emit(
            id=f"RETRY-{step_id}",
            actor="system:workflows",
            action_type="workflow_step_retry",
            target=f"workflow:{workflow_id}:step:{step_id}",
            status="pending",
            extras={
                "workflow_id": workflow_id,
                "step_id": step_id,
                "step_order": retried.step_order,
                "step_action_type": retried.action_type,
            },
        )
        return retried

    def _claim_next_pending_step(self, workflow_id: str) -> WorkflowStepRecord | None:
        conn = connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                """SELECT * FROM workflow_steps
                WHERE workflow_id=? AND status='pending'
                ORDER BY step_order ASC
                LIMIT 1""",
                (workflow_id,),
            ).fetchone()
            if row is None:
                conn.execute("COMMIT")
                return None
            conn.execute("UPDATE workflows SET status='running', updated_at=? WHERE id=?", (int(time.time()), workflow_id))
            conn.execute("UPDATE workflow_steps SET status='running' WHERE id=?", (row["id"],))
            claimed = conn.execute("SELECT * FROM workflow_steps WHERE id=?", (row["id"],)).fetchone()
            conn.execute("COMMIT")
        except Exception:
            try:
                conn.execute("ROLLBACK")
            except Exception:
                pass
            raise
        finally:
            conn.close()
        return _row_to_step(claimed)


def execute_step_stub(step: WorkflowStepRecord, *, agent_runner: AgentRunner | None = None) -> StepExecutionOutput:
    """Safe executor for workflow steps until live agent runners exist."""
    if step.action_type == "draft_content":
        return write_draft_content_output(step, agent_runner=agent_runner)
    text = f"Step executed: {step.action_type}"
    return StepExecutionOutput(text=text, ref=f"workflow-output://{step.workflow_id}/{step.id}", runner="deterministic")


def write_draft_content_output(
    step: WorkflowStepRecord,
    *,
    agent_runner: AgentRunner | None = None,
) -> StepExecutionOutput:
    """Write a markdown draft artifact for a content workflow step."""
    title = str(step.params.get("title", f"Step {step.step_order}"))
    content_type = str(step.params.get("type", "content"))
    period = str(step.params.get("period") or "unspecified")
    runner = agent_runner or default_agent_runner()
    request = DraftContentRequest(
        workflow_id=step.workflow_id,
        step_id=step.id,
        step_order=step.step_order,
        actor=step.actor,
        title=title,
        content_type=content_type,
        period=period,
        source_action_id=step.params.get("source_action_id"),
    )
    draft = runner.draft_content(request)
    output_dir = get_config().data_dir / "workspace" / "content" / step.workflow_id
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{step.id}.md"
    output_path.write_text(draft.markdown, encoding="utf-8")
    return StepExecutionOutput(
        text=draft.summary,
        ref=f"file://{output_path}",
        runner=draft.runner,
        warning=draft.warning,
    )


def _content_workflow_title(params: dict[str, Any], count: int) -> str:
    content_type = params.get("type", "content")
    period = params.get("period")
    suffix = f" for {period}" if period else ""
    return f"Create {count} {content_type} draft(s){suffix}"


def _row_to_workflow(row: Any) -> WorkflowRecord:
    return WorkflowRecord(
        id=row["id"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        source_action_id=row["source_action_id"],
        actor=row["actor"],
        workflow_type=row["workflow_type"],
        title=row["title"],
        params=json.loads(row["params_json"] or "{}"),
        status=row["status"],
        step_count=row["step_count"] if "step_count" in row.keys() else 0,
    )


def _row_to_step(row: Any) -> WorkflowStepRecord:
    return WorkflowStepRecord(
        id=row["id"],
        workflow_id=row["workflow_id"],
        step_order=row["step_order"],
        actor=row["actor"],
        action_type=row["action_type"],
        target=row["target"],
        params=json.loads(row["params_json"] or "{}"),
        status=row["status"],
        created_at=row["created_at"],
        completed_at=row["completed_at"],
        output_ref=row["output_ref"] if "output_ref" in row.keys() else None,
        output_text=row["output_text"] if "output_text" in row.keys() else None,
    )
