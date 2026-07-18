from __future__ import annotations

import json

import pytest


@pytest.fixture()
def isolated_env(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    db_path = data_dir / "soloos.sqlite"
    snapshot_path = tmp_path / "web" / "soloos-snapshot.json"
    monkeypatch.setenv("SOLOOS_DATA_DIR", str(data_dir))
    monkeypatch.setenv("SOLOOS_DB_PATH", str(db_path))
    monkeypatch.setenv("TELEGRAM_CEO_CHAT_ID", "1971680823")
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)

    import soloos.config as cfg_mod

    cfg_mod.reset_config()
    from soloos.db import migrate

    migrate()
    yield data_dir, snapshot_path
    cfg_mod.reset_config()


def test_approval_request_writes_telegram_card_with_decision_context(isolated_env):
    from soloos.approvals import ApprovalsService

    data_dir, _snapshot_path = isolated_env
    _verdict, approval_id = ApprovalsService().request(
        agent_id="growth",
        action_type="agent_factory_activate",
        target="agent_instance:customer-triage",
        params={
            "env": "production",
            "requesting_department": "Growth / Marketing",
            "mission": "신규 고객 문의를 분류하고 담당 부서에 전달합니다.",
            "artifact_summary": "고객 문의 1차 분류 AI 직원 활성화",
            "authority_limits": {"external_send": False, "production_change": False},
            "kpi": {"primary": "routing_accuracy"},
            "success_criteria": "분류 정확도 90% 이상",
            "evidence_ref": "audit:A-0007",
        },
        preview_url="file://preview.html",
        cost_krw=1200,
        audience="ceo",
    )

    assert approval_id is not None
    outbox = data_dir / "telegram-approval-outbox.jsonl"
    assert outbox.exists()
    card = json.loads(outbox.read_text(encoding="utf-8").splitlines()[-1])
    assert card["approval_id"] == approval_id
    assert card["delivery_status"] == "outbox"
    assert card["chat_ref"] == "ceo_telegram"
    assert "1971680823" not in json.dumps(card, ensure_ascii=False)
    text = card["text"]
    for expected in [
        approval_id,
        "agent_factory_activate",
        "agent_instance:customer-triage",
        "Growth / Marketing",
        "production",
        "1,200원",
        "신규 고객 문의를 분류",
        "고객 문의 1차 분류 AI 직원 활성화",
        "external_send=False",
        "routing_accuracy",
        "audit:A-0007",
    ]:
        assert expected in text
    keyboard = card["reply_markup"]["inline_keyboard"]
    assert keyboard[0][0] == {"text": "승인", "callback_data": f"soloos:approval:{approval_id}:approve"}
    assert keyboard[0][1] == {"text": "반려", "callback_data": f"soloos:approval:{approval_id}:reject"}
    assert keyboard[0][2] == {"text": "수정요청", "callback_data": f"soloos:approval:{approval_id}:revise"}

    record = ApprovalsService().get(approval_id)
    assert record is not None
    assert record.params["telegram"]["decision_surface"] == "primary"
    assert record.params["telegram"]["delivery_status"] == "outbox"
    assert record.params["telegram"]["chat_ref"] == "ceo_telegram"


def test_telegram_callback_updates_approval_and_refreshes_snapshot(isolated_env):
    from soloos.approvals import ApprovalsService
    from soloos.telegram_approvals import handle_telegram_approval_callback

    _data_dir, snapshot_path = isolated_env
    _verdict, approval_id = ApprovalsService().request(
        agent_id="growth",
        action_type="publish_content",
        target="https://example.com/draft",
        params={"env": "production", "mission": "LinkedIn 글 발행"},
        audience="public",
    )
    assert approval_id is not None

    result = handle_telegram_approval_callback(
        f"soloos:approval:{approval_id}:approve",
        by="ceo:telegram",
        snapshot_path=snapshot_path,
    )

    assert result.approval_id == approval_id
    assert result.status == "approved"
    assert result.verdict == "approved"
    assert "승인" in result.confirmation_text
    assert snapshot_path.exists()
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    assert snapshot["approvals"][0]["id"] == approval_id
    assert snapshot["approvals"][0]["status"] == "approved"
    assert snapshot["approvals"][0]["decided_by"] == "ceo:telegram"

    decided = ApprovalsService().get(approval_id)
    assert decided is not None
    assert decided.comment == "Telegram inline decision: approve"


def test_telegram_callback_revise_maps_to_deferred(isolated_env):
    from soloos.approvals import ApprovalsService
    from soloos.telegram_approvals import parse_telegram_callback

    _data_dir, _snapshot_path = isolated_env
    _verdict, approval_id = ApprovalsService().request(
        agent_id="cto",
        action_type="deploy_preview",
        target="preview://soloos",
        params={"env": "preview"},
        audience="ceo",
    )
    assert approval_id is not None

    parsed = parse_telegram_callback(f"soloos:approval:{approval_id}:revise")
    assert parsed.approval_id == approval_id
    assert parsed.verdict == "deferred"
    assert parsed.action == "revise"
