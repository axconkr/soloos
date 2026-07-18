"""Agent Factory / Employee Workbench service.

This is the substrate below Mission Control: employees can define governed agent
instances from templates, request CEO approval, then activate approved instances
into the executable SoloOS agent roster.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from typing import Any

from . import audit
from .approvals import ApprovalsService
from .db import connect
from .ids import next_id

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,62}[a-z0-9]$")
_VAR_RE = re.compile(r"{{\s*([a-zA-Z0-9_]+)\s*}}")


@dataclass(frozen=True)
class AgentTemplateRecord:
    id: str
    name: str
    department_agent_id: str
    mission_template: str
    default_authority: dict[str, Any]
    default_kpi: dict[str, Any]
    default_skills: list[str]
    risk_tier: str
    status: str
    created_at: int
    updated_at: int


@dataclass(frozen=True)
class AgentInstanceRecord:
    id: str
    agent_id: str
    template_id: str
    owner_agent_id: str
    slug: str
    name: str
    mission: str
    mission_vars: dict[str, Any]
    capability_set: dict[str, Any]
    authority: dict[str, Any]
    kpi: dict[str, Any]
    skills: list[str]
    risk_tier: str
    lifecycle_status: str
    policy_status: str
    approval_id: str | None
    created_by: str
    created_at: int
    activated_at: int | None
    updated_at: int


@dataclass(frozen=True)
class ActivationGate:
    instance_id: str
    status: str
    approval_id: str | None
    policy_rule: str
    risk: str


class AgentFactoryService:
    """Create governed agent specs before they enter the active roster."""

    def create_template(
        self,
        *,
        template_id: str,
        name: str,
        department: str,
        mission_template: str,
        default_skills: list[str] | None = None,
        default_authority: dict[str, Any] | None = None,
        default_kpi: dict[str, Any] | None = None,
        risk_tier: str = "MED",
    ) -> AgentTemplateRecord:
        if risk_tier not in {"LOW", "MED", "HIGH"}:
            raise ValueError(f"invalid risk_tier: {risk_tier}")
        now = int(time.time())
        authority = default_authority or {}
        kpi = default_kpi or {}
        skills = default_skills or []
        conn = connect()
        try:
            conn.execute(
                """INSERT INTO agent_templates
                (id, name, department_agent_id, mission_template, default_authority_json,
                 default_kpi_json, default_skills_json, risk_tier, status, created_at, updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name,
                    department_agent_id=excluded.department_agent_id,
                    mission_template=excluded.mission_template,
                    default_authority_json=excluded.default_authority_json,
                    default_kpi_json=excluded.default_kpi_json,
                    default_skills_json=excluded.default_skills_json,
                    risk_tier=excluded.risk_tier,
                    status='active',
                    updated_at=excluded.updated_at""",
                (
                    template_id,
                    name,
                    department,
                    mission_template,
                    json.dumps(authority, ensure_ascii=False, sort_keys=True),
                    json.dumps(kpi, ensure_ascii=False, sort_keys=True),
                    json.dumps(skills, ensure_ascii=False),
                    risk_tier,
                    "active",
                    now,
                    now,
                ),
            )
            row = conn.execute("SELECT * FROM agent_templates WHERE id=?", (template_id,)).fetchone()
        finally:
            conn.close()
        return _row_to_template(row)

    def create_instance(
        self,
        *,
        template_id: str,
        owner_agent_id: str,
        slug: str,
        mission_vars: dict[str, Any] | None = None,
        created_by: str,
    ) -> AgentInstanceRecord:
        _validate_slug(slug)
        template = self.get_template(template_id)
        if template is None or template.status != "active":
            raise KeyError(f"active template not found: {template_id}")
        vars_dict = mission_vars or {}
        mission = _render_template(template.mission_template, vars_dict)
        now = int(time.time())
        instance_id = f"agent_instance:{slug}"
        agent_id = f"agent:generated:{slug}"
        name = f"{template.name} / {slug}"
        capability_set = {
            "skills": template.default_skills,
            "source_template": template.id,
            "owner_agent_id": owner_agent_id,
        }
        conn = connect()
        try:
            conn.execute(
                """INSERT INTO agent_instances
                (id, agent_id, template_id, owner_agent_id, slug, name, mission,
                 mission_vars_json, capability_set_json, authority_json, kpi_json,
                 risk_tier, lifecycle_status, policy_status, approval_id, created_by,
                 created_at, activated_at, updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    instance_id,
                    agent_id,
                    template.id,
                    owner_agent_id,
                    slug,
                    name,
                    mission,
                    json.dumps(vars_dict, ensure_ascii=False, sort_keys=True),
                    json.dumps(capability_set, ensure_ascii=False, sort_keys=True),
                    json.dumps(template.default_authority, ensure_ascii=False, sort_keys=True),
                    json.dumps(template.default_kpi, ensure_ascii=False, sort_keys=True),
                    template.risk_tier,
                    "draft",
                    "review_required",
                    None,
                    created_by,
                    now,
                    None,
                    now,
                ),
            )
            row = conn.execute("SELECT * FROM agent_instances WHERE id=?", (instance_id,)).fetchone()
        finally:
            conn.close()
        audit.emit(
            id=next_id("A"),
            actor=created_by,
            action_type="agent_instance_created",
            target=instance_id,
            status="review_required",
            policy_rule="agent_factory:create_draft",
            extras={"agent_id": agent_id, "template_id": template_id, "owner_agent_id": owner_agent_id},
        )
        return _row_to_instance(row)

    def request_activation(self, instance_id: str, *, requested_by: str) -> ActivationGate:
        instance = self.get_instance(instance_id)
        if instance is None:
            raise KeyError(instance_id)
        if instance.lifecycle_status == "active":
            return ActivationGate(instance.id, "already_active", instance.approval_id, "agent_factory:already_active", instance.risk_tier)

        verdict, approval_id = ApprovalsService().request(
            agent_id=instance.owner_agent_id.removeprefix("agent:"),
            action_type="agent_factory_activate",
            target=instance.id,
            params={
                "template_id": instance.template_id,
                "risk_tier": instance.risk_tier,
                "generated_agent_id": instance.agent_id,
                "created_by": instance.created_by,
                "requested_by": requested_by,
                "env": "production",
            },
            audience="ceo",
        )
        policy_status = "approval_required" if approval_id else ("approved" if verdict.verdict == "auto" else "blocked")
        lifecycle_status = "review" if approval_id else instance.lifecycle_status
        conn = connect()
        try:
            conn.execute(
                "UPDATE agent_instances SET lifecycle_status=?, policy_status=?, approval_id=?, updated_at=? WHERE id=?",
                (lifecycle_status, policy_status, approval_id, int(time.time()), instance.id),
            )
        finally:
            conn.close()
        audit.emit(
            id=next_id("A"),
            actor=requested_by,
            action_type="agent_activation_requested",
            target=instance.id,
            status="approval_required" if approval_id else verdict.verdict,
            policy_rule=verdict.rule_id,
            extras={"approval_id": approval_id, "generated_agent_id": instance.agent_id},
        )
        return ActivationGate(
            instance_id=instance.id,
            status="approval_required" if approval_id else verdict.verdict,
            approval_id=approval_id,
            policy_rule=verdict.rule_id,
            risk=verdict.risk,
        )

    def activate(self, instance_id: str, *, approval_id: str, activated_by: str) -> AgentInstanceRecord:
        instance = self.get_instance(instance_id)
        if instance is None:
            raise KeyError(instance_id)
        approval = ApprovalsService().get(approval_id)
        if approval is None or approval.status != "approved":
            raise RuntimeError(f"approval not approved: {approval_id}")
        if approval.target != instance.id:
            raise RuntimeError(f"approval {approval_id} does not target {instance.id}")
        now = int(time.time())
        conn = connect()
        try:
            conn.execute(
                """INSERT INTO agents
                (id, name, mission, tier, tone, authority_json, kpi_json, skills_json, status, updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name,
                    mission=excluded.mission,
                    tier=excluded.tier,
                    tone=excluded.tone,
                    authority_json=excluded.authority_json,
                    kpi_json=excluded.kpi_json,
                    skills_json=excluded.skills_json,
                    status='active',
                    updated_at=excluded.updated_at""",
                (
                    instance.agent_id,
                    instance.name,
                    instance.mission,
                    "reasoning" if instance.risk_tier in {"MED", "HIGH"} else "bulk",
                    "Korean-first, evidence-backed, role-scoped",
                    json.dumps(instance.authority, ensure_ascii=False, sort_keys=True),
                    json.dumps(instance.kpi, ensure_ascii=False, sort_keys=True),
                    json.dumps(instance.skills, ensure_ascii=False),
                    "active",
                    now,
                ),
            )
            conn.execute(
                """UPDATE agent_instances
                SET lifecycle_status='active', policy_status='approved', approval_id=?, activated_at=?, updated_at=?
                WHERE id=?""",
                (approval_id, now, now, instance.id),
            )
            row = conn.execute("SELECT * FROM agent_instances WHERE id=?", (instance.id,)).fetchone()
        finally:
            conn.close()
        audit.emit(
            id=next_id("A"),
            actor=activated_by,
            action_type="agent_instance_activated",
            target=instance.id,
            status="active",
            policy_rule=approval.policy_rule,
            extras={"approval_id": approval_id, "generated_agent_id": instance.agent_id},
        )
        return _row_to_instance(row)

    def get_template(self, template_id: str) -> AgentTemplateRecord | None:
        conn = connect()
        try:
            row = conn.execute("SELECT * FROM agent_templates WHERE id=?", (template_id,)).fetchone()
        finally:
            conn.close()
        return _row_to_template(row) if row else None

    def get_instance(self, instance_id: str) -> AgentInstanceRecord | None:
        conn = connect()
        try:
            row = conn.execute("SELECT * FROM agent_instances WHERE id=?", (instance_id,)).fetchone()
        finally:
            conn.close()
        return _row_to_instance(row) if row else None

    def list_instances(self, limit: int = 50) -> list[AgentInstanceRecord]:
        conn = connect()
        try:
            rows = conn.execute(
                "SELECT * FROM agent_instances ORDER BY updated_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        finally:
            conn.close()
        return [_row_to_instance(row) for row in rows]


def _validate_slug(slug: str) -> None:
    if not _SLUG_RE.match(slug):
        raise ValueError("slug must be 3-64 chars of lowercase letters, digits, and hyphens")


def _render_template(template: str, vars_dict: dict[str, Any]) -> str:
    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in vars_dict:
            raise ValueError(f"missing mission var: {key}")
        return str(vars_dict[key])

    return _VAR_RE.sub(replace, template)


def _row_to_template(row: Any) -> AgentTemplateRecord:
    return AgentTemplateRecord(
        id=row["id"],
        name=row["name"],
        department_agent_id=row["department_agent_id"],
        mission_template=row["mission_template"],
        default_authority=json.loads(row["default_authority_json"] or "{}"),
        default_kpi=json.loads(row["default_kpi_json"] or "{}"),
        default_skills=json.loads(row["default_skills_json"] or "[]"),
        risk_tier=row["risk_tier"],
        status=row["status"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _row_to_instance(row: Any) -> AgentInstanceRecord:
    capability_set = json.loads(row["capability_set_json"] or "{}")
    skills = capability_set.get("skills") or []
    return AgentInstanceRecord(
        id=row["id"],
        agent_id=row["agent_id"],
        template_id=row["template_id"],
        owner_agent_id=row["owner_agent_id"],
        slug=row["slug"],
        name=row["name"],
        mission=row["mission"],
        mission_vars=json.loads(row["mission_vars_json"] or "{}"),
        capability_set=capability_set,
        authority=json.loads(row["authority_json"] or "{}"),
        kpi=json.loads(row["kpi_json"] or "{}"),
        skills=skills,
        risk_tier=row["risk_tier"],
        lifecycle_status=row["lifecycle_status"],
        policy_status=row["policy_status"],
        approval_id=row["approval_id"],
        created_by=row["created_by"],
        created_at=row["created_at"],
        activated_at=row["activated_at"],
        updated_at=row["updated_at"],
    )
