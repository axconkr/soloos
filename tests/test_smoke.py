"""Smoke and regression tests for policy + approvals + audit."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pytest


@pytest.fixture()
def isolated_env(tmp_path, monkeypatch):
    """Fresh DB + audit dir per test."""
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


def _ctx(**overrides):
    ctx = {
        "actor": "agent:growth",
        "action": {"type": "draft_content", "contains_secret": False},
        "target": {"env": "production"},
        "params": {},
        "audience": "ceo",
        "channel": None,
        "template": {"id": None},
    }
    ctx.update(overrides)
    return ctx


def test_policy_auto_draft(isolated_env):
    from soloos.policy import PolicyEngine

    p = PolicyEngine()
    v = p.evaluate(_ctx())
    assert v.verdict == "auto"
    assert v.rule_id == "internal_drafts"


def test_policy_deny_prod_delete(isolated_env):
    from soloos.policy import PolicyEngine

    v = PolicyEngine().evaluate(_ctx(actor="agent:ops", action={"type": "delete", "contains_secret": False}))
    assert v.verdict == "deny"


def test_policy_missing_target_env_defaults_to_approval_not_production_deny(isolated_env):
    from soloos.policy import PolicyEngine

    v = PolicyEngine().evaluate(
        _ctx(actor="agent:ops", action={"type": "delete", "contains_secret": False}, target={})
    )
    assert v.verdict == "approval"
    assert v.rule_id == "default"


def test_policy_guardrail_5m(isolated_env):
    from soloos.policy import PolicyEngine

    v = PolicyEngine().evaluate(
        _ctx(actor="agent:cfo", action={"type": "task_create", "contains_secret": False}, params={"amount_krw": 6_000_000})
    )
    assert v.verdict == "approval"
    assert v.rule_id.startswith("guardrail")


def test_policy_recursively_wraps_nested_context(isolated_env):
    from soloos.policy import PolicyEngine

    v = PolicyEngine().evaluate(
        _ctx(
            actor="agent:growth",
            action={"type": "spend_money", "contains_secret": False},
            params={"amount_krw": 600_000, "meta": {"source": "ads"}},
        )
    )
    assert v.verdict == "escalate"
    assert v.rule_id == "growth_overbudget"


def test_policy_invalid_rule_expression_raises(tmp_path):
    import soloos.policy as policy_mod

    rules = tmp_path / "rules.yaml"
    rules.write_text(
        """
default_verdict: approval
rules:
  - id: broken
    when: "action.type == "
    verdict: approval
""",
        encoding="utf-8",
    )
    engine = policy_mod.PolicyEngine(rules)
    with pytest.raises(policy_mod.PolicyRuleError):
        engine.evaluate(_ctx())


def test_config_reload_after_env_change(tmp_path, monkeypatch):
    from soloos.config import get_config

    monkeypatch.setenv("SOLOOS_DATA_DIR", str(tmp_path / "one"))
    one = get_config(reload=True)
    monkeypatch.setenv("SOLOOS_DATA_DIR", str(tmp_path / "two"))
    two = get_config(reload=True)
    assert one.data_dir != two.data_dir
    assert two.data_dir == (tmp_path / "two").resolve()


def test_ids_are_unique_under_threaded_contention(isolated_env):
    from soloos.ids import next_id

    with ThreadPoolExecutor(max_workers=8) as pool:
        ids = list(pool.map(lambda _: next_id("T"), range(50)))
    assert len(ids) == len(set(ids))
    assert sorted(ids) == [f"T-{i:04d}" for i in range(1, 51)]


def test_audit_persistence(isolated_env):
    from soloos import audit

    audit.emit(id="A-TEST", actor="test", action_type="probe", target="x", status="success")
    rows = audit.search(actor="test")
    assert len(rows) == 1
    assert rows[0]["id"] == "A-TEST"


def test_audit_get_event_reads_jsonl_source_with_extras(isolated_env):
    from soloos import audit

    audit.emit(
        id="A-DETAIL",
        actor="test",
        action_type="probe",
        target="x",
        status="success",
        extras={"output_ref": "file:///tmp/example.md", "nested": {"ok": True}},
    )

    record = audit.get_event("A-DETAIL")

    assert record is not None
    assert record["id"] == "A-DETAIL"
    assert record["extras"]["output_ref"] == "file:///tmp/example.md"
    assert record["extras"]["nested"]["ok"] is True


def test_audit_show_cli_prints_full_jsonl_record(isolated_env):
    from click.testing import CliRunner

    from soloos import audit
    from soloos.cli import main

    audit.emit(
        id="A-CLI",
        actor="test",
        action_type="probe",
        target="x",
        status="success",
        extras={"output_ref": "file:///tmp/example.md"},
    )

    result = CliRunner().invoke(main, ["audit", "show", "A-CLI"])

    assert result.exit_code == 0, result.output
    assert '"id": "A-CLI"' in result.output
    assert '"output_ref": "file:///tmp/example.md"' in result.output


def test_audit_reindex_rebuilds_from_jsonl(isolated_env):
    from soloos import audit
    from soloos.db import connect

    audit.emit(id="A-REINDEX", actor="test", action_type="probe", target="x", status="success")
    conn = connect()
    try:
        conn.execute("DELETE FROM audit_events")
    finally:
        conn.close()

    assert audit.search(actor="test") == []
    assert audit.reindex() == 1
    assert audit.search(actor="test")[0]["id"] == "A-REINDEX"


def test_approval_lifecycle(isolated_env):
    from soloos.approvals import ApprovalsService

    svc = ApprovalsService()
    v, ap_id = svc.request(
        agent_id="growth",
        action_type="publish",
        target="blog:test",
        params={"title": "hello"},
        channel="blog",
    )
    assert v.verdict == "approval"
    assert ap_id is not None

    pending = svc.list_pending()
    assert any(a.id == ap_id for a in pending)

    rec = svc.decide(ap_id, "approved", comment="ok")
    assert rec.status == "approved"
    assert rec.decided_by == "ceo"

    assert svc.list_pending() == []
