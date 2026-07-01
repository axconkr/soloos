"""Smoke tests for policy + approvals + audit."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest


@pytest.fixture()
def isolated_env(tmp_path, monkeypatch):
    """Fresh DB + audit dir per test."""
    data_dir = tmp_path / "data"
    db_path = data_dir / "soloos.sqlite"
    monkeypatch.setenv("SOLOOS_DATA_DIR", str(data_dir))
    monkeypatch.setenv("SOLOOS_DB_PATH", str(db_path))
    # reload config singleton
    import soloos.config as cfg_mod
    cfg_mod._config = None
    from soloos.db import migrate
    migrate()
    yield data_dir


def test_policy_auto_draft(isolated_env):
    from soloos.policy import PolicyEngine
    p = PolicyEngine()
    v = p.evaluate({
        "actor": "agent:cmo",
        "action": {"type": "draft_content", "contains_secret": False},
        "target": {"env": "production"},
        "params": {},
        "audience": "ceo",
        "channel": None,
        "template": {"id": None},
    })
    assert v.verdict == "auto"
    assert v.rule_id == "internal_drafts"


def test_policy_deny_prod_delete(isolated_env):
    from soloos.policy import PolicyEngine
    v = PolicyEngine().evaluate({
        "actor": "agent:ops",
        "action": {"type": "delete", "contains_secret": False},
        "target": {"env": "production"},
        "params": {},
        "audience": "ceo",
        "channel": None,
        "template": {"id": None},
    })
    assert v.verdict == "deny"


def test_policy_guardrail_5m(isolated_env):
    from soloos.policy import PolicyEngine
    v = PolicyEngine().evaluate({
        "actor": "agent:finance",
        "action": {"type": "task_create", "contains_secret": False},
        "target": {"env": "production"},
        "params": {"amount_krw": 6_000_000},
        "audience": "ceo",
        "channel": None,
        "template": {"id": None},
    })
    assert v.verdict == "approval"
    assert v.rule_id.startswith("guardrail")


def test_approval_lifecycle(isolated_env):
    from soloos.approvals import ApprovalsService
    svc = ApprovalsService()
    v, ap_id = svc.request(
        agent_id="cmo",
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


def test_audit_persistence(isolated_env):
    from soloos import audit
    audit.emit(id="A-TEST", actor="test", action_type="probe", target="x", status="success")
    rows = audit.search(actor="test")
    assert len(rows) == 1
    assert rows[0]["id"] == "A-TEST"
