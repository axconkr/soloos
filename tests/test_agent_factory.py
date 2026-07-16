"""Agent Factory / Employee Workbench tests."""
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


def test_employee_can_create_governed_agent_instance_from_template(isolated_env):
    from soloos.agent_factory import AgentFactoryService
    from soloos.agents import AgentsService
    from soloos.audit import search
    from soloos.db import connect

    AgentsService().seed_defaults()
    svc = AgentFactoryService()
    template = svc.create_template(
        template_id="research-assistant",
        name="Research Assistant",
        department="agent:cto",
        mission_template="Research {{topic}} and produce evidence-backed options.",
        default_skills=["web_research", "summarize", "evidence_pack"],
        default_authority={"can_browse_public_web": True, "can_contact_external": False},
        default_kpi={"primary": "decision_quality"},
        risk_tier="MED",
    )

    instance = svc.create_instance(
        template_id=template.id,
        owner_agent_id="agent:cto",
        slug="market-researcher-q3",
        mission_vars={"topic": "SoloOS ICP"},
        created_by="employee:engineering",
    )

    assert instance.id == "agent_instance:market-researcher-q3"
    assert instance.agent_id == "agent:generated:market-researcher-q3"
    assert instance.lifecycle_status == "draft"
    assert instance.policy_status == "review_required"
    assert instance.owner_agent_id == "agent:cto"
    assert "SoloOS ICP" in instance.mission
    assert instance.skills == ["web_research", "summarize", "evidence_pack"]

    conn = connect()
    try:
        row = conn.execute("SELECT * FROM agent_instances WHERE id=?", (instance.id,)).fetchone()
        assert row is not None
        assert row["template_id"] == "research-assistant"
        assert json.loads(row["capability_set_json"])["skills"] == instance.skills
        assert conn.execute("SELECT * FROM agents WHERE id=?", (instance.agent_id,)).fetchone() is None
    finally:
        conn.close()

    audit_rows = search(action_type="agent_instance_created")
    assert audit_rows
    assert audit_rows[0]["actor"] == "employee:engineering"
    assert audit_rows[0]["target"] == instance.id


def test_agent_factory_activation_requires_approval_before_roster_insert(isolated_env):
    from soloos.agent_factory import AgentFactoryService
    from soloos.agents import AgentsService
    from soloos.approvals import ApprovalsService
    from soloos.db import connect

    AgentsService().seed_defaults()
    svc = AgentFactoryService()
    svc.create_template(
        template_id="customer-reply-agent",
        name="Customer Reply Agent",
        department="agent:growth",
        mission_template="Draft customer replies for {{customer_segment}}.",
        default_skills=["reply_drafting", "tone_check"],
        default_authority={"can_draft_external_reply": True, "can_send_external_reply": False},
        default_kpi={"primary": "response_quality"},
        risk_tier="MED",
    )
    instance = svc.create_instance(
        template_id="customer-reply-agent",
        owner_agent_id="agent:growth",
        slug="vip-reply-drafter",
        mission_vars={"customer_segment": "VIP leads"},
        created_by="employee:growth",
    )

    gate = svc.request_activation(instance.id, requested_by="employee:growth")

    assert gate.status == "approval_required"
    assert gate.approval_id.startswith("AP-")
    assert svc.get_instance(instance.id).lifecycle_status == "review"

    conn = connect()
    try:
        assert conn.execute("SELECT * FROM agents WHERE id=?", (instance.agent_id,)).fetchone() is None
    finally:
        conn.close()

    ApprovalsService().decide(gate.approval_id, "approved", by="ceo", comment="factory smoke")
    activated = svc.activate(instance.id, approval_id=gate.approval_id, activated_by="employee:growth")

    assert activated.lifecycle_status == "active"
    roster_agent = AgentsService().get_active(instance.agent_id)
    assert roster_agent is not None
    assert roster_agent.name == "Customer Reply Agent / vip-reply-drafter"
    assert roster_agent.authority["can_send_external_reply"] is False


def test_agent_factory_cli_create_request_activate_and_list(isolated_env):
    from soloos.agent_factory import AgentFactoryService
    from soloos.agents import AgentsService
    from soloos.approvals import ApprovalsService
    from soloos.cli import main

    AgentsService().seed_defaults()
    AgentFactoryService().create_template(
        template_id="ops-runbook-agent",
        name="Ops Runbook Agent",
        department="agent:ops",
        mission_template="Maintain runbooks for {{system}}.",
        default_skills=["runbook", "monitoring"],
        default_authority={"can_create_local_files": True, "can_change_production": False},
        default_kpi={"primary": "runbook_coverage"},
        risk_tier="LOW",
    )

    runner = CliRunner()
    create_result = runner.invoke(
        main,
        [
            "agent-factory",
            "create",
            "ops-runbook-agent",
            "--owner-agent",
            "agent:ops",
            "--slug",
            "vercel-runbook",
            "--var",
            "system=Vercel",
            "--created-by",
            "employee:ops",
        ],
    )
    list_result = runner.invoke(main, ["agent-factory", "list"])
    request_result = runner.invoke(
        main,
        ["agent-factory", "request-activation", "agent_instance:vercel-runbook", "--requested-by", "employee:ops"],
    )

    assert create_result.exit_code == 0, create_result.output
    assert "agent_instance:vercel-runbook" in create_result.output
    assert "review_required" in create_result.output
    assert list_result.exit_code == 0, list_result.output
    assert "vercel-runbook" in list_result.output
    assert request_result.exit_code == 0, request_result.output
    assert "approval_required" in request_result.output
    approval_id = request_result.output.split("approval=")[1].split()[0]

    ApprovalsService().decide(approval_id, "approved", by="ceo", comment="ok")
    activate_result = runner.invoke(
        main,
        ["agent-factory", "activate", "agent_instance:vercel-runbook", "--approval", approval_id, "--activated-by", "employee:ops"],
    )

    assert activate_result.exit_code == 0, activate_result.output
    assert "status=active" in activate_result.output
    assert "agent:generated:vercel-runbook" in activate_result.output


def test_agent_factory_cli_can_create_template_before_instance(isolated_env):
    from soloos.agents import AgentsService
    from soloos.cli import main

    AgentsService().seed_defaults()
    runner = CliRunner()

    template_result = runner.invoke(
        main,
        [
            "agent-factory",
            "create-template",
            "research-assistant",
            "--name",
            "Research Assistant",
            "--department",
            "agent:cto",
            "--mission-template",
            "Research {{topic}} and produce options.",
            "--skill",
            "web_research",
            "--authority",
            '{"can_contact_external": false}',
            "--kpi",
            '{"primary": "decision_quality"}',
            "--risk-tier",
            "MED",
        ],
    )
    create_result = runner.invoke(
        main,
        [
            "agent-factory",
            "create",
            "research-assistant",
            "--owner-agent",
            "agent:cto",
            "--slug",
            "soloos-icp-researcher",
            "--var",
            "topic=SoloOS ICP",
            "--created-by",
            "employee:engineering",
        ],
    )

    assert template_result.exit_code == 0, template_result.output
    assert "template=research-assistant" in template_result.output
    assert create_result.exit_code == 0, create_result.output
    assert "agent_instance:soloos-icp-researcher" in create_result.output
