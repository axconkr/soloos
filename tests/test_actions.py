"""Actions executor tests."""
from __future__ import annotations

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


def _enqueue_content_action() -> str:
    from soloos.command_deck import CommandDeck

    response = CommandDeck().handle_text(
        platform="telegram",
        chat_id="1971680823",
        text="이번 주 블로그 3편 초안 만들어줘",
    )
    assert response.action_id is not None
    return response.action_id


def test_actions_next_returns_oldest_pending_action(isolated_env):
    from soloos.actions import ActionsService

    action_id = _enqueue_content_action()
    action = ActionsService().next_pending()

    assert action is not None
    assert action.id == action_id
    assert action.status == "pending"
    assert action.actor == "agent:growth"
    assert action.params["count"] == 3


def test_actions_run_one_dispatches_to_seeded_agent_handler_and_audits(isolated_env):
    from soloos import audit
    from soloos.actions import ActionsService
    from soloos.agents import AgentsService
    from soloos.db import connect

    AgentsService().seed_defaults()
    action_id = _enqueue_content_action()
    result = ActionsService().run_one()

    assert result is not None
    assert result.id == action_id
    assert result.status == "success"
    assert "Growth / Marketing workflow" in result.output
    assert "draft_content" in result.output

    conn = connect()
    try:
        row = conn.execute("SELECT * FROM actions WHERE id = ?", (action_id,)).fetchone()
    finally:
        conn.close()

    assert row["status"] == "success"
    assert row["completed_at"] is not None
    assert row["latency_ms"] is not None
    assert row["snapshot_ref"] == "workflow://WF-0001"

    rows = audit.search(action_type="action_run")
    assert len(rows) == 1
    assert rows[0]["target"] == f"action:{action_id}"
    assert rows[0]["status"] == "success"


def test_actions_run_one_returns_none_when_queue_empty(isolated_env):
    from soloos.actions import ActionsService

    assert ActionsService().run_one() is None


def test_actions_next_cli_prints_pending_action(isolated_env):
    from soloos.cli import main

    action_id = _enqueue_content_action()
    result = CliRunner().invoke(main, ["actions", "next"])

    assert result.exit_code == 0, result.output
    assert action_id in result.output
    assert "pending" in result.output


def test_actions_run_one_cli_executes_pending_action(isolated_env):
    from soloos.agents import AgentsService
    from soloos.cli import main
    from soloos.db import connect

    AgentsService().seed_defaults()
    action_id = _enqueue_content_action()
    result = CliRunner().invoke(main, ["actions", "run-one"])

    assert result.exit_code == 0, result.output
    assert action_id in result.output
    assert "success" in result.output

    conn = connect()
    try:
        status = conn.execute("SELECT status FROM actions WHERE id = ?", (action_id,)).fetchone()["status"]
    finally:
        conn.close()
    assert status == "success"
