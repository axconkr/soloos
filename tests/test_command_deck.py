"""Command Deck dispatch/session tests."""
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


def test_command_deck_handles_greeting_and_records_session_intent(isolated_env):
    from soloos.command_deck import CommandDeck
    from soloos.db import connect

    response = CommandDeck().handle_text(
        platform="telegram",
        chat_id="1971680823",
        text="안녕",
    )

    assert response.intent == "greeting"
    assert response.routed_to is None
    assert response.action_id is None
    assert response.requires_clarification is False
    assert "SoloOS" in response.markdown

    conn = connect()
    try:
        session = conn.execute("SELECT * FROM sessions").fetchone()
        intent = conn.execute("SELECT * FROM intents").fetchone()
    finally:
        conn.close()

    assert session["session_id"] == "telegram:1971680823:"
    assert session["platform"] == "telegram"
    assert intent["raw_text"] == "안녕"
    assert intent["classified_intent"] == "greeting"
    assert intent["routed_to"] is None


def test_command_deck_routes_content_plan_to_growth_and_enqueues_action(isolated_env):
    from soloos.command_deck import CommandDeck
    from soloos import audit
    from soloos.db import connect

    response = CommandDeck().handle_text(
        platform="telegram",
        chat_id="1971680823",
        text="이번 주 블로그 3편 초안 만들어줘",
    )

    assert response.intent == "content_plan"
    assert response.routed_to == "growth"
    assert response.action_id is not None
    assert response.requires_clarification is False
    assert "Growth" in response.markdown
    assert response.action_id in response.markdown

    conn = connect()
    try:
        action = conn.execute("SELECT * FROM actions WHERE id = ?", (response.action_id,)).fetchone()
    finally:
        conn.close()

    assert action is not None
    assert action["actor"] == "agent:growth"
    assert action["action_type"] == "content_plan"
    assert action["target"] == "command_deck:telegram:1971680823:"
    assert action["status"] == "pending"
    assert action["policy_rule"] == "command_deck:local_classifier"

    rows = audit.search(action_type="deck_dispatch")
    assert len(rows) == 1
    assert rows[0]["actor"] == "user:telegram:1971680823"
    assert rows[0]["status"] == "routed"


def test_command_deck_routes_inbound_inquiry_reply_to_growth_sales(isolated_env):
    from soloos.command_deck import CommandDeck
    from soloos.db import connect

    response = CommandDeck().handle_text(
        platform="web",
        chat_id="ceo",
        text="신규 문의 답장 초안 작성해줘",
    )

    assert response.intent == "sales_task"
    assert response.routed_to == "growth"
    assert response.action_id is not None
    assert response.requires_clarification is False
    assert "Growth" in response.markdown

    conn = connect()
    try:
        action = conn.execute("SELECT * FROM actions WHERE id = ?", (response.action_id,)).fetchone()
    finally:
        conn.close()

    assert action is not None
    assert action["actor"] == "agent:growth"
    assert action["action_type"] == "sales_task"
    assert "reply_draft" in action["params_json"]


def test_command_deck_unknown_text_asks_clarifying_question(isolated_env):
    from soloos.command_deck import CommandDeck

    response = CommandDeck().handle_text(
        platform="telegram",
        chat_id="1971680823",
        text="저거 처리해줘",
    )

    assert response.intent == "unknown"
    assert response.routed_to is None
    assert response.action_id is None
    assert response.requires_clarification is True
    assert "어느 팀" in response.markdown


def test_command_deck_does_not_enqueue_greeting_or_unknown(isolated_env):
    from soloos.command_deck import CommandDeck
    from soloos.db import connect

    deck = CommandDeck()
    greeting = deck.handle_text(platform="telegram", chat_id="1971680823", text="안녕")
    unknown = deck.handle_text(platform="telegram", chat_id="1971680823", text="저거 처리해줘")

    assert greeting.action_id is None
    assert unknown.action_id is None

    conn = connect()
    try:
        count = conn.execute("SELECT COUNT(*) c FROM actions").fetchone()["c"]
    finally:
        conn.close()
    assert count == 0


def test_deck_dispatch_cli_outputs_response_and_records_intent(isolated_env):
    from soloos.cli import main
    from soloos.db import connect

    result = CliRunner().invoke(
        main,
        [
            "deck",
            "dispatch",
            "안녕",
            "--platform",
            "telegram",
            "--chat-id",
            "1971680823",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "SoloOS" in result.output

    conn = connect()
    try:
        count = conn.execute("SELECT COUNT(*) c FROM intents").fetchone()["c"]
    finally:
        conn.close()
    assert count == 1


def test_deck_dispatch_cli_prints_action_id_for_routed_task(isolated_env):
    from soloos.cli import main

    result = CliRunner().invoke(
        main,
        [
            "deck",
            "dispatch",
            "이번 주 블로그 3편 초안 만들어줘",
            "--platform",
            "telegram",
            "--chat-id",
            "1971680823",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "A-" in result.output
