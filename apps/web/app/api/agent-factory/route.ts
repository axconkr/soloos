import { randomUUID } from "node:crypto";
import { NextResponse } from "next/server";
import { authorizeWebApi, boundedString, readBoundedJson, stableError } from "../../../lib/api-guard";
import { createAgentFactoryDraft, requestAgentFactoryApproval } from "../../../lib/mission-control-client";

const DEPARTMENTS = new Set(["agent:ceo_office", "agent:cto", "agent:design", "agent:growth", "agent:cfo", "agent:general_counsel", "agent:ops"]);
const RISK_TIERS = new Set(["LOW", "MED", "HIGH"]);

function slugify(value: string) {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9-]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 48) || `agent-${randomUUID().slice(0, 8)}`;
}

function skillList(value: unknown) {
  if (Array.isArray(value)) return value.map((item) => boundedString(item, 40)).filter(Boolean).slice(0, 8);
  return boundedString(value, 240).split(",").map((item) => item.trim()).filter(Boolean).slice(0, 8);
}

export async function POST(request: Request) {
  const authError = authorizeWebApi(request);
  if (authError) return authError;

  let body: Record<string, unknown>;
  try {
    body = await readBoundedJson(request);
  } catch (error) {
    if (stableError(error) === "request_too_large") {
      return NextResponse.json({ error: "request_too_large" }, { status: 413 });
    }
    return NextResponse.json({ error: "invalid_json" }, { status: 400 });
  }

  const mode = boundedString(body.mode, 40);
  const baseEvent = {
    id: `WEB-FACTORY-${randomUUID()}`,
    created_at: new Date().toISOString(),
    mode,
  };

  try {
    if (mode === "create_draft") {
      const roleName = boundedString(body.role_name, 120);
      const mission = boundedString(body.mission, 1000);
      const department = DEPARTMENTS.has(boundedString(body.department, 80)) ? boundedString(body.department, 80) : "agent:ceo_office";
      const riskTierRaw = boundedString(body.risk_tier, 10).toUpperCase();
      const riskTier = (RISK_TIERS.has(riskTierRaw) ? riskTierRaw : "MED") as "LOW" | "MED" | "HIGH";
      if (roleName.length < 2 || mission.length < 10) {
        return NextResponse.json({ error: "agent_spec_required" }, { status: 400 });
      }
      const event = await createAgentFactoryDraft(
        {
          roleName,
          department,
          slug: slugify(boundedString(body.slug, 80) || roleName),
          mission,
          skills: skillList(body.skills),
          authority: boundedString(body.authority, 600) || "CEO 승인 전 외부 발행/고객접촉/프로덕션 변경 금지",
          kpi: boundedString(body.kpi, 120) || "agent_quality",
          riskTier,
          createdBy: boundedString(body.created_by, 80) || "employee:web",
        },
        baseEvent,
      );
      return NextResponse.json(event, { status: 202 });
    }

    if (mode === "request_approval") {
      const instanceId = boundedString(body.instance_id, 120);
      if (!instanceId.startsWith("agent_instance:")) {
        return NextResponse.json({ error: "instance_id_required" }, { status: 400 });
      }
      const event = await requestAgentFactoryApproval(
        instanceId,
        boundedString(body.requested_by, 80) || "employee:web",
        baseEvent,
      );
      return NextResponse.json(event, { status: 202 });
    }

    return NextResponse.json({ error: "invalid_factory_mode" }, { status: 400 });
  } catch (error) {
    return NextResponse.json({ ...baseEvent, status: "agent_factory_failed", error: stableError(error) }, { status: 502 });
  }
}
