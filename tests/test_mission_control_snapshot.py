from __future__ import annotations

import json
import sqlite3


def test_export_mission_control_snapshot_reads_soloos_runtime_tables(tmp_path):
    from soloos.mission_control_snapshot import export_snapshot

    db_path = tmp_path / "soloos.sqlite"
    out_path = tmp_path / "snapshot.json"
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE agents (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, mission TEXT, tier TEXT NOT NULL,
            tone TEXT, authority_json TEXT, kpi_json TEXT, skills_json TEXT,
            status TEXT, updated_at INTEGER
        );
        CREATE TABLE agent_templates (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, department_agent_id TEXT NOT NULL,
            mission_template TEXT NOT NULL, default_authority_json TEXT NOT NULL,
            default_kpi_json TEXT NOT NULL, default_skills_json TEXT NOT NULL,
            risk_tier TEXT, status TEXT, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL
        );
        CREATE TABLE agent_instances (
            id TEXT PRIMARY KEY, agent_id TEXT NOT NULL, template_id TEXT NOT NULL,
            owner_agent_id TEXT NOT NULL, slug TEXT NOT NULL, name TEXT NOT NULL,
            mission TEXT NOT NULL, mission_vars_json TEXT NOT NULL,
            capability_set_json TEXT NOT NULL, authority_json TEXT NOT NULL,
            kpi_json TEXT NOT NULL, risk_tier TEXT, lifecycle_status TEXT,
            policy_status TEXT, approval_id TEXT, created_by TEXT NOT NULL,
            created_at INTEGER NOT NULL, activated_at INTEGER, updated_at INTEGER NOT NULL
        );
        CREATE TABLE actions (
            id TEXT PRIMARY KEY, ts INTEGER NOT NULL, actor TEXT NOT NULL,
            action_type TEXT NOT NULL, target TEXT, params_json TEXT, policy_rule TEXT,
            status TEXT, cost_krw INTEGER, latency_ms INTEGER, approval_id TEXT,
            parent_action_id TEXT, snapshot_ref TEXT, created_at INTEGER, completed_at INTEGER
        );
        CREATE TABLE workflows (
            id TEXT PRIMARY KEY, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL,
            source_action_id TEXT, actor TEXT NOT NULL, workflow_type TEXT NOT NULL,
            title TEXT, params_json TEXT, status TEXT
        );
        CREATE TABLE workflow_steps (
            id TEXT PRIMARY KEY, workflow_id TEXT NOT NULL, step_order INTEGER NOT NULL,
            actor TEXT NOT NULL, action_type TEXT NOT NULL, target TEXT, params_json TEXT,
            status TEXT, created_at INTEGER NOT NULL, completed_at INTEGER,
            output_ref TEXT, output_text TEXT
        );
        CREATE TABLE approvals (
            id TEXT PRIMARY KEY, created_at INTEGER NOT NULL, agent_id TEXT NOT NULL,
            action_type TEXT NOT NULL, target TEXT NOT NULL, preview_url TEXT,
            cost_krw INTEGER DEFAULT 0, risk TEXT DEFAULT 'LOW', policy_rule TEXT,
            status TEXT DEFAULT 'pending', decided_at INTEGER, decided_by TEXT,
            comment TEXT, audit_id TEXT, params_json TEXT
        );
        CREATE TABLE audit_events (
            id TEXT PRIMARY KEY, ts INTEGER NOT NULL, actor TEXT, action_type TEXT,
            target TEXT, status TEXT, policy_rule TEXT, cost_krw INTEGER,
            file_path TEXT NOT NULL, line_offset INTEGER NOT NULL, content_hash TEXT
        );
        """
    )
    conn.execute(
        "INSERT INTO agents VALUES (?,?,?,?,?,?,?,?,?,?)",
        (
            "agent:growth",
            "Growth / Marketing",
            "Create demand",
            "reasoning",
            "sharp",
            '{"can_publish": false}',
            '{"primary": "qualified_leads"}',
            '["content"]',
            "active",
            100,
        ),
    )
    conn.execute(
        "INSERT INTO agent_templates VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (
            "customer-reply-agent",
            "Customer Reply Agent",
            "agent:growth",
            "Draft customer replies for {{customer_segment}}.",
            '{"can_send_external_reply": false}',
            '{"primary": "response_quality"}',
            '["reply_drafting"]',
            "MED",
            "active",
            100,
            101,
        ),
    )
    conn.execute(
        "INSERT INTO agent_instances VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            "agent_instance:vip-reply-drafter",
            "agent:generated:vip-reply-drafter",
            "customer-reply-agent",
            "agent:growth",
            "vip-reply-drafter",
            "Customer Reply Agent / vip-reply-drafter",
            "Draft customer replies for VIP leads.",
            '{"customer_segment": "VIP leads"}',
            '{"skills": ["reply_drafting"], "source_template": "customer-reply-agent"}',
            '{"can_send_external_reply": false}',
            '{"primary": "response_quality"}',
            "MED",
            "review",
            "approval_required",
            "AP-0001",
            "employee:growth",
            101,
            None,
            102,
        ),
    )
    conn.execute(
        "INSERT INTO actions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            "A-0001",
            101,
            "agent:growth",
            "content_plan",
            None,
            '{"count": 1}',
            None,
            "success",
            0,
            55,
            None,
            None,
            "workflow://WF-0001",
            101,
            102,
        ),
    )
    conn.execute(
        "INSERT INTO workflows VALUES (?,?,?,?,?,?,?,?,?)",
        (
            "WF-0001",
            103,
            104,
            "A-0001",
            "agent:growth",
            "content_plan",
            "Content workflow",
            '{"count": 1}',
            "success",
        ),
    )
    conn.execute(
        "INSERT INTO workflow_steps VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            "WS-0001",
            "WF-0001",
            1,
            "agent:growth",
            "draft_content",
            "workflow:WF-0001:step:1",
            '{"title": "Blog draft 1"}',
            "success",
            103,
            105,
            "file:///tmp/WS-0001.md",
            "OpenRouter draft written",
        ),
    )
    conn.execute(
        "INSERT INTO approvals VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            "AP-0001",
            105,
            "growth",
            "publish_content",
            "https://example.com/draft",
            "file:///tmp/preview.html",
            0,
            "MED",
            "public_publish_requires_approval",
            "pending",
            None,
            None,
            None,
            None,
            '{"channel": "linkedin"}',
        ),
    )
    conn.execute(
        "INSERT INTO audit_events VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (
            "STEP-WS-0001",
            106,
            "user:telegram:1971680823",
            "workflow_step_run",
            "session:telegram:1971680823:",
            "success",
            None,
            0,
            "audit.jsonl",
            1,
            "hash",
        ),
    )
    conn.commit()
    conn.close()

    snapshot = export_snapshot(db_path=db_path, out_path=out_path)
    serialized = json.dumps(snapshot, ensure_ascii=False)

    assert "/tmp" not in serialized
    assert "1971680823" not in serialized
    assert "user:telegram:redacted" in serialized
    assert str(db_path) not in serialized
    assert snapshot["db_path"] == "soloos.sqlite"

    assert snapshot["counts"] == {
        "agents": 1,
        "agent_templates": 1,
        "agent_instances": 1,
        "actions": 1,
        "workflows": 1,
        "workflow_steps": 1,
        "approvals": 1,
        "audit_events": 1,
    }
    assert snapshot["agents"][0]["name"] == "Growth / Marketing"
    assert snapshot["agent_templates"][0]["id"] == "customer-reply-agent"
    assert snapshot["agent_templates"][0]["default_skills"] == ["reply_drafting"]
    assert snapshot["agent_instances"][0]["slug"] == "vip-reply-drafter"
    assert snapshot["agent_instances"][0]["policy_status"] == "approval_required"
    assert snapshot["actions"][0]["snapshot_ref"] == "workflow://WF-0001"
    assert snapshot["workflows"][0]["status"] == "success"
    assert snapshot["workflow_steps"][0]["output_ref"] == "file://WS-0001.md"
    assert snapshot["approvals"][0]["preview_url"] == "file://preview.html"
    assert snapshot["audit_events"][0]["file_path"] == "audit.jsonl"
    assert json.loads(out_path.read_text())["generated_at"]


def test_mission_control_cli_exports_snapshot(tmp_path, monkeypatch):
    from click.testing import CliRunner

    data_dir = tmp_path / "data"
    db_path = data_dir / "soloos.sqlite"
    out_path = tmp_path / "soloos-snapshot.json"
    monkeypatch.setenv("SOLOOS_DATA_DIR", str(data_dir))
    monkeypatch.setenv("SOLOOS_DB_PATH", str(db_path))

    import soloos.config as cfg_mod
    from soloos.agents import AgentsService
    from soloos.cli import main
    from soloos.db import migrate

    cfg_mod.reset_config()
    migrate()
    AgentsService().seed_defaults()

    result = CliRunner().invoke(main, ["mission-control", "export-snapshot", "--output", str(out_path)])

    assert result.exit_code == 0, result.output
    assert "snapshot=" in result.output
    assert out_path.exists()
    exported = json.loads(out_path.read_text(encoding="utf-8"))
    assert exported["counts"]["agents"] >= 1

    cfg_mod.reset_config()
