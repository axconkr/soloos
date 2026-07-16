import { randomUUID } from "node:crypto";
import { NextResponse } from "next/server";
import { authorizeWebApi, boundedString, readBoundedJson, stableError } from "../../../lib/api-guard";
import { decideMissionControl, recordApprovalEvent, SOLOOS_VERDICT } from "../../../lib/mission-control-client";

const ALLOWED_DECISIONS = new Set(Object.keys(SOLOOS_VERDICT));

export async function POST(request: Request) {
  const authError = authorizeWebApi(request);
  if (authError) return authError;

  let body: { approval_id?: unknown; title?: unknown; department?: unknown; decision?: unknown; note?: unknown };
  try {
    body = await readBoundedJson(request);
  } catch (error) {
    if (stableError(error) === "request_too_large") {
      return NextResponse.json({ error: "request_too_large" }, { status: 413 });
    }
    return NextResponse.json({ error: "invalid_json" }, { status: 400 });
  }

  const decision = typeof body.decision === "string" ? body.decision : "";
  if (!ALLOWED_DECISIONS.has(decision)) {
    return NextResponse.json({ error: "invalid_decision" }, { status: 400 });
  }

  const approvalId = boundedString(body.approval_id, 80);
  const note = boundedString(body.note, 1000);
  const baseEvent = {
    id: `WEB-APPROVAL-${randomUUID()}`,
    created_at: new Date().toISOString(),
    approval_id: approvalId || undefined,
    title: boundedString(body.title, 200) || "approval_item",
    department: boundedString(body.department, 120) || "AI Department",
    decision,
    note,
  };

  if (!approvalId) {
    return NextResponse.json({ error: "approval_id_required" }, { status: 400 });
  }

  try {
    const event = await decideMissionControl(approvalId, decision, note, baseEvent);
    await recordApprovalEvent(event);
    return NextResponse.json(event, { status: 202 });
  } catch (error) {
    const event = {
      ...baseEvent,
      status: "soloos_decision_failed",
      error: stableError(error),
    };
    await recordApprovalEvent(event);
    return NextResponse.json(event, { status: 502 });
  }
}
