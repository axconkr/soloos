from __future__ import annotations

import json

import pytest
from click.testing import CliRunner


@pytest.fixture()
def isolated_env(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    db_path = data_dir / "soloos.sqlite"
    snapshot_path = tmp_path / "web" / "soloos-snapshot.json"
    monkeypatch.setenv("SOLOOS_DATA_DIR", str(data_dir))
    monkeypatch.setenv("SOLOOS_DB_PATH", str(db_path))

    import soloos.config as cfg_mod

    cfg_mod.reset_config()
    from soloos.db import migrate

    migrate()
    yield data_dir, snapshot_path
    cfg_mod.reset_config()


def test_submit_ceo_request_routes_to_command_deck_and_exports_snapshot(isolated_env):
    from soloos.db import connect
    from soloos.mission_control import submit_ceo_request

    _data_dir, snapshot_path = isolated_env

    result = submit_ceo_request(
        text="이번 주 블로그 2편 초안 만들어줘",
        platform="web",
        chat_id="ceo",
        snapshot_path=snapshot_path,
    )

    assert result.intent == "content_plan"
    assert result.routed_to == "growth"
    assert result.action_id is not None
    assert result.snapshot_path == snapshot_path
    assert snapshot_path.exists()

    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    assert snapshot["counts"]["agents"] == 7
    assert snapshot["counts"]["actions"] == 1
    assert snapshot["actions"][0]["id"] == result.action_id
    assert snapshot["actions"][0]["actor"] == "agent:growth"
    assert snapshot["actions"][0]["status"] == "pending"
    assert [agent["id"] for agent in snapshot["agents"]] == [
        "agent:ceo_office",
        "agent:cfo",
        "agent:cto",
        "agent:design",
        "agent:general_counsel",
        "agent:growth",
        "agent:ops",
    ]

    conn = connect()
    try:
        session = conn.execute("SELECT * FROM sessions WHERE session_id = 'web:ceo:'").fetchone()
    finally:
        conn.close()
    assert session["active_agent"] == "growth"


def test_decide_approval_updates_record_and_exports_snapshot(isolated_env):
    from soloos.approvals import ApprovalsService
    from soloos.mission_control import decide_approval

    _data_dir, snapshot_path = isolated_env
    _verdict, approval_id = ApprovalsService().request(
        agent_id="growth",
        action_type="publish_content",
        target="https://example.com/draft",
        params={"channel": "linkedin"},
        audience="public",
    )
    assert approval_id is not None

    result = decide_approval(
        approval_id,
        "approved",
        by="ceo:web",
        comment="발행 승인",
        snapshot_path=snapshot_path,
    )

    assert result.approval_id == approval_id
    assert result.status == "approved"
    assert result.snapshot_path == snapshot_path

    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    assert snapshot["counts"]["approvals"] == 1
    assert snapshot["approvals"][0]["id"] == approval_id
    assert snapshot["approvals"][0]["status"] == "approved"
    assert snapshot["approvals"][0]["decided_by"] == "ceo:web"


def test_mission_control_ask_cli_smoke_exports_snapshot(isolated_env):
    from soloos.cli import main

    _data_dir, snapshot_path = isolated_env
    result = CliRunner().invoke(
        main,
        [
            "mission-control",
            "ask",
            "이번 주 블로그 1개 초안 만들어줘",
            "--snapshot-path",
            str(snapshot_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "content_plan" in result.output
    assert "agent:growth" in result.output
    assert snapshot_path.exists()
