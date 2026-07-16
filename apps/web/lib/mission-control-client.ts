import { execFile } from "node:child_process";
import { appendFile, mkdir } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { promisify } from "node:util";

const runFile = promisify(execFile);

export const REPO_ROOT = resolve(process.cwd(), "../..");
export const SNAPSHOT_PATH = resolve(process.cwd(), "public/soloos-snapshot.json");
export const COMMAND_LOG = resolve(REPO_ROOT, "data/web-commands.jsonl");
export const APPROVAL_LOG = resolve(REPO_ROOT, "data/web-approvals.jsonl");

const SOLOOS_API_URL = process.env.SOLOOS_MISSION_CONTROL_URL?.replace(/\/$/, "");
const SOLOOS_API_TOKEN = process.env.SOLOOS_MISSION_CONTROL_TOKEN;
const IS_SERVERLESS = process.env.VERCEL === "1"
  || process.env.NETLIFY === "true"
  || Boolean(process.env.AWS_LAMBDA_FUNCTION_NAME)
  || Boolean(process.env.CF_PAGES)
  || process.env.SOLOOS_MISSION_CONTROL_MODE === "remote"
  || process.env.NEXT_RUNTIME === "edge";
const REMOTE_TIMEOUT_MS = 15_000;

export const SOLOOS_VERDICT: Record<string, "approved" | "rejected" | "deferred"> = {
  approve: "approved",
  reject: "rejected",
  revise: "deferred",
};

export type MissionControlEvent = Record<string, unknown>;

export class MissionControlUnavailableError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "MissionControlUnavailableError";
  }
}

function headers() {
  const base: Record<string, string> = { "Content-Type": "application/json" };
  if (SOLOOS_API_TOKEN) base.Authorization = `Bearer ${SOLOOS_API_TOKEN}`;
  return base;
}

function parseCliFields(stdout: string) {
  return {
    intent: stdout.match(/intent=([^\s]+)/)?.[1],
    routed_to: stdout.match(/routed_to=([^\s]+)/)?.[1],
    action_id: stdout.match(/action_id=([^\s]+)/)?.[1],
    approval_id: stdout.match(/approval=([^\s]+)/)?.[1],
    soloos_status: stdout.match(/status=([^\s]+)/)?.[1],
  };
}

async function appendJsonl(path: string, event: MissionControlEvent) {
  if (IS_SERVERLESS) return;
  await mkdir(dirname(path), { recursive: true });
  await appendFile(path, `${JSON.stringify(event)}\n`, "utf8");
}

async function postRemote(path: string, body: MissionControlEvent) {
  if (!SOLOOS_API_URL) {
    throw new MissionControlUnavailableError(
      "SOLOOS_MISSION_CONTROL_URL is required for serverless deployment",
    );
  }
  if (SOLOOS_API_TOKEN && !SOLOOS_API_URL.startsWith("https://")) {
    throw new MissionControlUnavailableError("SOLOOS_MISSION_CONTROL_URL must use https when SOLOOS_MISSION_CONTROL_TOKEN is set");
  }
  const response = await fetch(`${SOLOOS_API_URL}${path}`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(REMOTE_TIMEOUT_MS),
  });
  if (!response.ok) {
    throw new MissionControlUnavailableError(`remote_mission_control_${response.status}`);
  }
  const json = await response.json().catch(() => ({}));
  return json as MissionControlEvent;
}

export async function askMissionControl(command: string, source: string, baseEvent: MissionControlEvent) {
  if (SOLOOS_API_URL) {
    const remote = await postRemote("/mission-control/ask", { command, source, snapshot_path: SNAPSHOT_PATH });
    return {
      ...baseEvent,
      ...remote,
      snapshot_path: remote.snapshot_path ?? SNAPSHOT_PATH,
      status: "routed_to_soloos_remote",
    };
  }

  if (IS_SERVERLESS) {
    throw new MissionControlUnavailableError("local uv execution is disabled in serverless; configure SOLOOS_MISSION_CONTROL_URL");
  }

  const { stdout, stderr } = await runFile(
    "uv",
    ["run", "soloos", "mission-control", "ask", command, "--snapshot-path", SNAPSHOT_PATH],
    { cwd: REPO_ROOT, timeout: 30_000, maxBuffer: 1024 * 1024 },
  );
  return {
    ...baseEvent,
    ...parseCliFields(stdout),
    snapshot_path: SNAPSHOT_PATH,
    local_warning: stderr.trim() ? "soloos_cli_wrote_stderr" : undefined,
    status: "routed_to_soloos",
  };
}

export async function decideMissionControl(
  approvalId: string,
  decision: string,
  note: string,
  baseEvent: MissionControlEvent,
) {
  const verdict = SOLOOS_VERDICT[decision];
  if (SOLOOS_API_URL) {
    const remote = await postRemote("/mission-control/decide", {
      approval_id: approvalId,
      verdict,
      by: "ceo:web",
      comment: note || decision,
      snapshot_path: SNAPSHOT_PATH,
    });
    return {
      ...baseEvent,
      ...remote,
      approval_id: remote.approval_id ?? approvalId,
      snapshot_path: remote.snapshot_path ?? SNAPSHOT_PATH,
      status: "recorded_in_soloos_remote",
    };
  }

  if (IS_SERVERLESS) {
    throw new MissionControlUnavailableError("local uv execution is disabled in serverless; configure SOLOOS_MISSION_CONTROL_URL");
  }

  const { stdout, stderr } = await runFile(
    "uv",
    [
      "run",
      "soloos",
      "mission-control",
      "decide",
      approvalId,
      verdict,
      "--by",
      "ceo:web",
      "--comment",
      note || decision,
      "--snapshot-path",
      SNAPSHOT_PATH,
    ],
    { cwd: REPO_ROOT, timeout: 30_000, maxBuffer: 1024 * 1024 },
  );
  return {
    ...baseEvent,
    ...parseCliFields(stdout),
    approval_id: approvalId,
    snapshot_path: SNAPSHOT_PATH,
    local_warning: stderr.trim() ? "soloos_cli_wrote_stderr" : undefined,
    status: "recorded_in_soloos",
  };
}

export async function recordCommandEvent(event: MissionControlEvent) {
  await appendJsonl(COMMAND_LOG, event);
}

export async function recordApprovalEvent(event: MissionControlEvent) {
  await appendJsonl(APPROVAL_LOG, event);
}
