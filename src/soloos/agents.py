"""Agent roster service.

MVP scope: seed/list the core SoloOS agent roster used by the actions executor.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

from .db import connect


@dataclass(frozen=True)
class AgentRecord:
    id: str
    name: str
    mission: str | None
    tier: str
    tone: str | None
    authority: dict[str, Any]
    kpi: dict[str, Any]
    skills: list[str]
    status: str
    updated_at: int | None


DEFAULT_AGENTS: tuple[dict[str, Any], ...] = (
    {
        "id": "agent:ceo_office",
        "name": "CEO Office / Chief of Staff",
        "mission": "Translate Phillip's intent into priorities, decision gates, and daily operating briefs.",
        "tier": "reasoning",
        "tone": "blunt, CEO-readable, evidence-first",
        "authority": {
            "can_set_priorities": False,
            "can_request_clarification": True,
            "requires_approval_for_strategy": True,
        },
        "kpi": {"primary": "decision_latency", "secondary": "weekly_execution_throughput"},
        "skills": ["product_discovery", "planning", "decision_briefs", "mission_control"],
    },
    {
        "id": "agent:cto",
        "name": "Engineering / CTO",
        "mission": "Ship verified software changes for SoloOS, ax-con.com, soloforge.me, and client systems.",
        "tier": "reasoning",
        "tone": "technical, test-driven, concise",
        "authority": {
            "can_write_code": True,
            "can_create_local_files": True,
            "can_deploy_production": False,
            "requires_approval_for_public_repo_or_prod": True,
        },
        "kpi": {"primary": "verified_shipments", "secondary": "regression_rate"},
        "skills": ["superpowers", "context7", "webapp_testing", "tdd", "github_workflow"],
    },
    {
        "id": "agent:design",
        "name": "Design / Brand",
        "mission": "Turn strategy and product intent into usable interfaces, brand systems, and visual artifacts.",
        "tier": "reasoning",
        "tone": "tasteful, concrete, conversion-aware",
        "authority": {
            "can_generate_designs": True,
            "can_change_public_brand": False,
            "requires_approval_for_brand_lock": True,
        },
        "kpi": {"primary": "approved_design_assets", "secondary": "ux_defect_rate"},
        "skills": ["ui_ux_pro_max", "taste", "brand_guidelines", "web_artifacts"],
    },
    {
        "id": "agent:growth",
        "name": "Growth / Marketing",
        "mission": "Create positioning, content, campaigns, and social assets for Phillip's offers.",
        "tier": "reasoning",
        "tone": "sharp, practical, market-aware",
        "authority": {
            "can_draft_public_content": True,
            "can_publish": False,
            "requires_approval_for_external_send": True,
        },
        "kpi": {"primary": "qualified_leads", "secondary": "content_velocity"},
        "skills": ["copywriting", "seo", "lead_magnets", "campaigns", "social_media"],
    },
    {
        "id": "agent:cfo",
        "name": "Finance / CFO",
        "mission": "Track cash, costs, invoices, and financial risk without making final tax or investment judgments.",
        "tier": "reasoning",
        "tone": "conservative, exact, risk-aware",
        "authority": {
            "can_move_money": False,
            "can_file_taxes": False,
            "requires_approval_for_money": True,
        },
        "kpi": {"primary": "cash_visibility", "secondary": "cost_control"},
        "skills": ["cashflow", "invoices", "cost_review", "finance_checklists"],
    },
    {
        "id": "agent:general_counsel",
        "name": "Legal / Compliance",
        "mission": "Flag legal, contract, privacy, and compliance risks for human review.",
        "tier": "reasoning",
        "tone": "careful, non-lawyer, risk-focused",
        "authority": {
            "can_review_contracts": True,
            "can_provide_final_legal_advice": False,
            "requires_human_legal_review": True,
        },
        "kpi": {"primary": "risk_flags_caught", "secondary": "review_turnaround"},
        "skills": ["contract_review", "nda_checklist", "privacy_checklist", "compliance_triage"],
    },
    {
        "id": "agent:ops",
        "name": "Ops / Automation",
        "mission": "Keep workflows, automations, Google Workspace, notifications, and delivery operations moving.",
        "tier": "bulk",
        "tone": "systematic, operational, terse",
        "authority": {
            "can_run_local_automation": True,
            "can_change_production": False,
            "requires_approval_for_prod": True,
        },
        "kpi": {"primary": "cycle_time", "secondary": "automation_reliability"},
        "skills": ["workflow", "automation", "google_workspace", "telegram", "cron", "reporting"],
    },
)


class AgentsService:
    """Seed and inspect the local agent roster."""

    def seed_defaults(self) -> int:
        now = int(time.time())
        inserted = 0
        default_ids = tuple(agent["id"] for agent in DEFAULT_AGENTS)
        legacy_ids = ("agent:cmo", "agent:sales", "agent:finance")
        conn = connect()
        try:
            placeholders = ",".join("?" for _ in legacy_ids)
            conn.execute(
                f"DELETE FROM agents WHERE id IN ({placeholders}) AND id NOT IN ({','.join('?' for _ in default_ids)})",
                (*legacy_ids, *default_ids),
            )
            for agent in DEFAULT_AGENTS:
                existed = (
                    conn.execute("SELECT 1 FROM agents WHERE id=?", (agent["id"],)).fetchone()
                    is not None
                )
                conn.execute(
                    """INSERT INTO agents
                    (id, name, mission, tier, tone, authority_json, kpi_json,
                     skills_json, status, updated_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(id) DO UPDATE SET
                        name=excluded.name,
                        mission=excluded.mission,
                        tier=excluded.tier,
                        tone=excluded.tone,
                        authority_json=excluded.authority_json,
                        kpi_json=excluded.kpi_json,
                        skills_json=excluded.skills_json,
                        status=excluded.status,
                        updated_at=excluded.updated_at""",
                    (
                        agent["id"],
                        agent["name"],
                        agent["mission"],
                        agent["tier"],
                        agent["tone"],
                        json.dumps(agent["authority"], ensure_ascii=False, sort_keys=True),
                        json.dumps(agent["kpi"], ensure_ascii=False, sort_keys=True),
                        json.dumps(agent["skills"], ensure_ascii=False),
                        "active",
                        now,
                    ),
                )
                if not existed:
                    inserted += 1
        finally:
            conn.close()
        return inserted

    def list_agents(self) -> list[AgentRecord]:
        conn = connect()
        try:
            rows = conn.execute("SELECT * FROM agents ORDER BY id").fetchall()
        finally:
            conn.close()
        return [_row_to_agent(row) for row in rows]

    def get_active(self, agent_id: str) -> AgentRecord | None:
        conn = connect()
        try:
            row = conn.execute(
                "SELECT * FROM agents WHERE id=? AND status='active'",
                (agent_id,),
            ).fetchone()
        finally:
            conn.close()
        return _row_to_agent(row) if row else None


def _row_to_agent(row: Any) -> AgentRecord:
    return AgentRecord(
        id=row["id"],
        name=row["name"],
        mission=row["mission"],
        tier=row["tier"],
        tone=row["tone"],
        authority=json.loads(row["authority_json"] or "{}"),
        kpi=json.loads(row["kpi_json"] or "{}"),
        skills=json.loads(row["skills_json"] or "[]"),
        status=row["status"],
        updated_at=row["updated_at"],
    )
