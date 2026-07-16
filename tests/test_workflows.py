"""Workflow Engine smoke tests."""
from __future__ import annotations

import json

import pytest
from click.testing import CliRunner


@pytest.fixture()
def isolated_env(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    db_path = data_dir / "soloos.sqlite"
    monkeypatch.setenv("SOLOOS_DATA_DIR", str(data_dir))
    monkeypatch.setenv("SOLOOS_DB_PATH", str(db_path))

    import soloos.config as cfg_mod

    cfg_mod.reset_config()
    from soloos.db import migrate

    migrate()
    yield data_dir
    cfg_mod.reset_config()


def test_create_content_plan_workflow_persists_ordered_steps(isolated_env):
    from soloos.workflow import WorkflowService
    from soloos.db import connect

    workflow = WorkflowService().create_content_plan(
        source_action_id="A-0001",
        actor="agent:growth",
        params={"type": "blog", "count": 3, "period": "this_week"},
    )

    assert workflow.id.startswith("WF-")
    assert workflow.status == "pending"
    assert workflow.step_count == 3

    conn = connect()
    try:
        wf_row = conn.execute("SELECT * FROM workflows WHERE id=?", (workflow.id,)).fetchone()
        step_rows = conn.execute(
            "SELECT * FROM workflow_steps WHERE workflow_id=? ORDER BY step_order",
            (workflow.id,),
        ).fetchall()
    finally:
        conn.close()

    assert wf_row["source_action_id"] == "A-0001"
    assert wf_row["actor"] == "agent:growth"
    assert json.loads(wf_row["params_json"])["count"] == 3
    assert [row["step_order"] for row in step_rows] == [1, 2, 3]
    assert [row["status"] for row in step_rows] == ["pending", "pending", "pending"]
    assert step_rows[0]["action_type"] == "draft_content"
    assert json.loads(step_rows[0]["params_json"])["title"] == "Blog draft 1"


def test_running_content_plan_action_creates_workflow_and_records_snapshot(isolated_env):
    from soloos.actions import ActionsService
    from soloos.agents import AgentsService
    from soloos.command_deck import CommandDeck
    from soloos.db import connect

    AgentsService().seed_defaults()
    response = CommandDeck().handle_text(
        platform="telegram",
        chat_id="1971680823",
        text="이번 주 블로그 3편 초안 만들어줘",
    )
    assert response.action_id is not None

    result = ActionsService().run_one()

    assert result is not None
    assert result.status == "success"
    assert "workflow" in result.output.lower()

    conn = connect()
    try:
        action = conn.execute("SELECT * FROM actions WHERE id=?", (response.action_id,)).fetchone()
        workflows = conn.execute("SELECT * FROM workflows").fetchall()
        steps = conn.execute("SELECT * FROM workflow_steps ORDER BY step_order").fetchall()
    finally:
        conn.close()

    assert len(workflows) == 1
    assert workflows[0]["source_action_id"] == response.action_id
    assert action["snapshot_ref"] == f"workflow://{workflows[0]['id']}"
    assert len(steps) == 3


def test_run_next_step_completes_steps_in_order_and_finishes_workflow(isolated_env):
    from soloos.db import connect
    from soloos.workflow import WorkflowService

    svc = WorkflowService()
    workflow = svc.create_content_plan(
        source_action_id="A-0001",
        actor="agent:growth",
        params={"type": "blog", "count": 2},
    )

    first = svc.run_next_step(workflow.id)
    second = svc.run_next_step(workflow.id)
    empty = svc.run_next_step(workflow.id)

    assert first is not None
    assert first.step_id == "WS-0001"
    assert first.status == "success"
    assert first.output_ref.startswith("file://")
    assert first.output_ref.endswith(f"/workspace/content/{workflow.id}/WS-0001.md")
    first_output_path = first.output_ref.removeprefix("file://")
    assert "Blog draft 1" in first.output
    assert second is not None
    assert second.step_id == "WS-0002"
    assert empty is None

    conn = connect()
    try:
        wf_row = conn.execute("SELECT status FROM workflows WHERE id=?", (workflow.id,)).fetchone()
        step_rows = conn.execute(
            "SELECT status, completed_at, output_ref, output_text FROM workflow_steps WHERE workflow_id=? ORDER BY step_order",
            (workflow.id,),
        ).fetchall()
    finally:
        conn.close()

    assert wf_row["status"] == "success"
    assert [row["status"] for row in step_rows] == ["success", "success"]
    assert all(row["completed_at"] is not None for row in step_rows)
    assert step_rows[0]["output_ref"] == first.output_ref
    assert step_rows[0]["output_text"] == first.output

    output_file = isolated_env / "workspace" / "content" / workflow.id / "WS-0001.md"
    assert first_output_path == str(output_file)
    assert output_file.exists()
    file_text = output_file.read_text(encoding="utf-8")
    assert "# Blog draft 1" in file_text
    assert f"workflow_id: {workflow.id}" in file_text
    assert "type: blog" in file_text


def test_run_next_step_writes_audit_event_for_success(isolated_env):
    from soloos import audit
    from soloos.workflow import WorkflowService

    svc = WorkflowService()
    workflow = svc.create_content_plan(
        source_action_id="A-0001",
        actor="agent:growth",
        params={"type": "blog", "count": 1},
    )

    result = svc.run_next_step(workflow.id)

    assert result is not None
    rows = audit.search(action_type="workflow_step_run")
    assert len(rows) == 1
    assert rows[0]["id"] == f"STEP-{result.step_id}"
    assert rows[0]["actor"] == "agent:growth"
    assert rows[0]["target"] == f"workflow:{workflow.id}:step:{result.step_id}"
    assert rows[0]["status"] == "success"


def test_run_next_step_marks_step_and_workflow_failed_and_audits_failure(isolated_env, monkeypatch):
    from soloos import audit
    from soloos.db import connect
    import soloos.workflow as workflow_mod
    from soloos.workflow import WorkflowService

    def fail_writer(step, **_kwargs):
        raise RuntimeError(f"cannot write {step.id}")

    monkeypatch.setattr(workflow_mod, "write_draft_content_output", fail_writer)
    svc = WorkflowService()
    workflow = svc.create_content_plan(
        source_action_id="A-0001",
        actor="agent:growth",
        params={"type": "blog", "count": 1},
    )

    result = svc.run_next_step(workflow.id)

    assert result is not None
    assert result.status == "failed"
    assert result.output_ref == f"workflow-output://{workflow.id}/WS-0001/failed"
    assert "cannot write WS-0001" in result.output

    conn = connect()
    try:
        wf_row = conn.execute("SELECT status FROM workflows WHERE id=?", (workflow.id,)).fetchone()
        step_row = conn.execute(
            "SELECT status, output_ref, output_text FROM workflow_steps WHERE id='WS-0001'"
        ).fetchone()
    finally:
        conn.close()

    assert wf_row["status"] == "failed"
    assert step_row["status"] == "failed"
    assert step_row["output_ref"] == result.output_ref
    assert step_row["output_text"] == result.output

    rows = audit.search(action_type="workflow_step_run")
    assert len(rows) == 1
    assert rows[0]["id"] == "STEP-WS-0001"
    assert rows[0]["status"] == "failed"


def test_retry_step_resets_failed_step_for_rerun_and_audits(isolated_env, monkeypatch):
    from soloos import audit
    from soloos.db import connect
    import soloos.workflow as workflow_mod
    from soloos.workflow import WorkflowService

    original_writer = workflow_mod.write_draft_content_output

    def fail_writer(step, **_kwargs):
        raise RuntimeError(f"cannot write {step.id}")

    svc = WorkflowService()
    workflow = svc.create_content_plan(
        source_action_id="A-0001",
        actor="agent:growth",
        params={"type": "blog", "count": 1},
    )
    monkeypatch.setattr(workflow_mod, "write_draft_content_output", fail_writer)
    failed = svc.run_next_step(workflow.id)
    assert failed is not None
    assert failed.status == "failed"

    monkeypatch.setattr(workflow_mod, "write_draft_content_output", original_writer)
    retried = svc.retry_step(workflow.id, "WS-0001")

    assert retried is not None
    assert retried.status == "pending"
    assert retried.completed_at is None
    assert retried.output_ref is None
    assert retried.output_text is None

    conn = connect()
    try:
        wf_row = conn.execute("SELECT status FROM workflows WHERE id=?", (workflow.id,)).fetchone()
        step_row = conn.execute(
            "SELECT status, completed_at, output_ref, output_text FROM workflow_steps WHERE id='WS-0001'"
        ).fetchone()
    finally:
        conn.close()

    assert wf_row["status"] == "pending"
    assert step_row["status"] == "pending"
    assert step_row["completed_at"] is None
    assert step_row["output_ref"] is None
    assert step_row["output_text"] is None

    retry_rows = audit.search(action_type="workflow_step_retry")
    assert len(retry_rows) == 1
    assert retry_rows[0]["id"] == "RETRY-WS-0001"
    assert retry_rows[0]["actor"] == "system:workflows"
    assert retry_rows[0]["target"] == f"workflow:{workflow.id}:step:WS-0001"
    assert retry_rows[0]["status"] == "pending"

    rerun = svc.run_next_step(workflow.id)
    assert rerun is not None
    assert rerun.status == "success"
    assert rerun.output_ref.startswith("file://")


def test_workflows_cli_can_retry_failed_step(isolated_env):
    from soloos.db import connect
    from soloos.workflow import WorkflowService
    from soloos.cli import main

    workflow = WorkflowService().create_content_plan(
        source_action_id="A-0001",
        actor="agent:growth",
        params={"type": "blog", "count": 1},
    )
    conn = connect()
    try:
        conn.execute(
            """UPDATE workflow_steps
            SET status='failed', completed_at=123, output_ref='workflow-output://failed', output_text='boom'
            WHERE id='WS-0001'"""
        )
        conn.execute("UPDATE workflows SET status='failed' WHERE id=?", (workflow.id,))
    finally:
        conn.close()

    retry_result = CliRunner().invoke(main, ["workflows", "retry-step", workflow.id, "WS-0001"])
    run_result = CliRunner().invoke(main, ["workflows", "run-step", workflow.id])

    assert retry_result.exit_code == 0, retry_result.output
    assert "WS-0001" in retry_result.output
    assert "pending" in retry_result.output
    assert run_result.exit_code == 0, run_result.output
    assert "WS-0001" in run_result.output
    assert "success" in run_result.output


def test_workflows_cli_lists_and_runs_next_step(isolated_env):
    from soloos.workflow import WorkflowService
    from soloos.cli import main

    workflow = WorkflowService().create_content_plan(
        source_action_id="A-0001",
        actor="agent:growth",
        params={"type": "blog", "count": 2},
    )

    list_result = CliRunner().invoke(main, ["workflows", "list"])
    run_result = CliRunner().invoke(main, ["workflows", "run-step", workflow.id])
    steps_result = CliRunner().invoke(main, ["workflows", "steps", workflow.id])

    assert list_result.exit_code == 0, list_result.output
    assert workflow.id in list_result.output
    assert "content_plan" in list_result.output
    assert "pending" in list_result.output
    assert "2" in list_result.output
    assert run_result.exit_code == 0, run_result.output
    assert "WS-0001" in run_result.output
    assert "success" in run_result.output
    assert "file://" in run_result.output
    assert ".md" in run_result.output
    assert steps_result.exit_code == 0, steps_result.output
    assert "success" in steps_result.output
    assert "file://" in steps_result.output
    assert "pending" in steps_result.output
