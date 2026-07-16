import { randomUUID } from "node:crypto";
import { NextResponse } from "next/server";
import { authorizeWebApi, boundedString, readBoundedJson, stableError } from "../../../lib/api-guard";
import { askMissionControl, recordCommandEvent } from "../../../lib/mission-control-client";

function suggestedDepartment(command: string) {
  const lower = command.toLowerCase();
  if (lower.includes("문의") || lower.includes("답장") || lower.includes("답변") || lower.includes("회신") || lower.includes("고객") || lower.includes("리드") || lower.includes("영업")) return "agent:growth";
  if (lower.includes("콘텐츠") || lower.includes("블로그") || lower.includes("마케팅") || lower.includes("seo")) return "agent:growth";
  if (lower.includes("웹") || lower.includes("버그") || lower.includes("개발") || lower.includes("사이트")) return "agent:cto";
  if (lower.includes("디자인") || lower.includes("브랜드") || lower.includes("ui")) return "agent:design";
  if (lower.includes("비용") || lower.includes("송장") || lower.includes("현금") || lower.includes("예산")) return "agent:cfo";
  if (lower.includes("계약") || lower.includes("nda") || lower.includes("법률")) return "agent:general_counsel";
  if (lower.includes("알림") || lower.includes("자동화") || lower.includes("문서")) return "agent:ops";
  return "agent:ceo_office";
}

export async function POST(request: Request) {
  const authError = authorizeWebApi(request);
  if (authError) return authError;

  let body: { command?: unknown; source?: unknown };
  try {
    body = await readBoundedJson(request);
  } catch (error) {
    if (stableError(error) === "request_too_large") {
      return NextResponse.json({ error: "request_too_large" }, { status: 413 });
    }
    return NextResponse.json({ error: "invalid_json" }, { status: 400 });
  }

  const command = boundedString(body.command, 2000);
  if (command.length < 3) {
    return NextResponse.json({ error: "command_required" }, { status: 400 });
  }

  const source = boundedString(body.source, 80) || "mission_control_web";
  const baseEvent = {
    id: `WEB-CMD-${randomUUID()}`,
    created_at: new Date().toISOString(),
    source,
    command,
    suggested_department: suggestedDepartment(command),
  };

  try {
    const event = await askMissionControl(command, source, baseEvent);
    await recordCommandEvent(event);
    return NextResponse.json(event, { status: 202 });
  } catch (error) {
    const event = {
      ...baseEvent,
      status: "soloos_route_failed",
      error: stableError(error),
    };
    await recordCommandEvent(event);
    return NextResponse.json(event, { status: 502 });
  }
}
