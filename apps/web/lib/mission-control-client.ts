import { execFile } from "node:child_process";
import { existsSync } from "node:fs";
import { appendFile, mkdir } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { promisify } from "node:util";

const runFile = promisify(execFile);

function resolveRepoRoot() {
  const cwd = process.cwd();
  if (existsSync(resolve(cwd, "pyproject.toml")) && existsSync(resolve(cwd, "src/soloos"))) return cwd;
  return resolve(cwd, "../..");
}

export const REPO_ROOT = resolveRepoRoot();
export const WEB_ROOT = existsSync(resolve(process.cwd(), "app")) ? process.cwd() : resolve(REPO_ROOT, "apps/web");
export const SNAPSHOT_PATH = resolve(WEB_ROOT, "public/soloos-snapshot.json");
export const COMMAND_LOG = resolve(REPO_ROOT, "data/web-commands.jsonl");
export const APPROVAL_LOG = resolve(REPO_ROOT, "data/web-approvals.jsonl");

const SOLOOS_API_URL = process.env.SOLOOS_MISSION_CONTROL_URL?.replace(/\/$/, "");
const SOLOOS_API_TOKEN = process.env.SOLOOS_MISSION_CONTROL_TOKEN;
export const IS_SERVERLESS = process.env.VERCEL === "1"
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

async function ensureLocalMigrations() {
  if (IS_SERVERLESS || SOLOOS_API_URL) return;
  await runFile("uv", ["run", "soloos", "db", "migrate"], { cwd: REPO_ROOT, timeout: 30_000, maxBuffer: 1024 * 1024 });
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
    const remote = await postRemote("/mission-control/ask", { command, source, snapshot_path: "soloos-snapshot.json" });
    return {
      ...baseEvent,
      ...remote,
      snapshot_path: remote.snapshot_path ? "remote_snapshot" : "soloos-snapshot.json",
      status: "routed_to_soloos_remote",
    };
  }

  if (IS_SERVERLESS) {
    throw new MissionControlUnavailableError("local uv execution is disabled in serverless; configure SOLOOS_MISSION_CONTROL_URL");
  }
  await ensureLocalMigrations();

  const { stdout, stderr } = await runFile(
    "uv",
    ["run", "soloos", "mission-control", "ask", command, "--snapshot-path", SNAPSHOT_PATH],
    { cwd: REPO_ROOT, timeout: 30_000, maxBuffer: 1024 * 1024 },
  );
  return {
    ...baseEvent,
    ...parseCliFields(stdout),
    snapshot_path: "soloos-snapshot.json",
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
      snapshot_path: "soloos-snapshot.json",
    });
    return {
      ...baseEvent,
      ...remote,
      approval_id: remote.approval_id ?? approvalId,
      snapshot_path: remote.snapshot_path ? "remote_snapshot" : "soloos-snapshot.json",
      status: "recorded_in_soloos_remote",
    };
  }

  if (IS_SERVERLESS) {
    throw new MissionControlUnavailableError("local uv execution is disabled in serverless; configure SOLOOS_MISSION_CONTROL_URL");
  }
  await ensureLocalMigrations();

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
    snapshot_path: "soloos-snapshot.json",
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

export type AgentFactoryDraftInput = {
  roleName: string;
  department: string;
  slug: string;
  mission: string;
  skills: string[];
  authority: string;
  kpi: string;
  riskTier: "LOW" | "MED" | "HIGH";
  createdBy: string;
};

function templateIdFor(input: AgentFactoryDraftInput, slug: string) {
  return `web-${input.department.replace(/^agent:/, "").replace(/[^a-zA-Z0-9_-]/g, "-")}-${slug}`.toLowerCase();
}

function isDuplicateAgentInstanceError(error: unknown) {
  const text = error instanceof Error ? `${error.message} ${(error as Error & { stderr?: string; stdout?: string }).stderr ?? ""} ${(error as Error & { stderr?: string; stdout?: string }).stdout ?? ""}` : String(error);
  return text.includes("UNIQUE constraint failed: agent_instances.id")
    || text.includes("UNIQUE constraint failed: agent_instances.slug")
    || text.includes("agent_instances.id")
    || text.includes("agent_instances.slug");
}

async function createLocalAgentInstance(input: AgentFactoryDraftInput, templateId: string, slug: string) {
  return runFile(
    "uv",
    [
      "run", "soloos", "agent-factory", "create", templateId,
      "--owner-agent", input.department,
      "--slug", slug,
      "--var", `objective=${input.roleName}`,
      "--created-by", input.createdBy,
    ],
    { cwd: REPO_ROOT, timeout: 30_000, maxBuffer: 1024 * 1024 },
  );
}

export async function createAgentFactoryDraft(input: AgentFactoryDraftInput, baseEvent: MissionControlEvent) {
  if (SOLOOS_API_URL) {
    const remote = await postRemote("/agent-factory/create", input as unknown as MissionControlEvent);
    return { ...baseEvent, ...remote, status: "agent_factory_created_remote" };
  }
  if (IS_SERVERLESS) {
    throw new MissionControlUnavailableError("local uv execution is disabled in serverless; configure SOLOOS_MISSION_CONTROL_URL");
  }
  await ensureLocalMigrations();

  let effectiveSlug = input.slug;
  let templateId = templateIdFor(input, effectiveSlug);
  const authority = JSON.stringify({ guardrail: input.authority, external_contact: false, production: false });
  const kpi = JSON.stringify({ primary: input.kpi || "agent_quality", review_required: true });
  const missionTemplate = `${input.mission} {{objective}}`;

  async function upsertTemplate(id: string) {
    await runFile(
      "uv",
      [
        "run", "soloos", "agent-factory", "create-template", id,
        "--name", input.roleName,
        "--department", input.department,
        "--mission-template", missionTemplate,
        "--authority", authority,
        "--kpi", kpi,
        "--risk-tier", input.riskTier,
        ...input.skills.flatMap((skill) => ["--skill", skill]),
      ],
      { cwd: REPO_ROOT, timeout: 30_000, maxBuffer: 1024 * 1024 },
    );
  }

  await upsertTemplate(templateId);
  let stdout = "";
  let stderr = "";
  try {
    const result = await createLocalAgentInstance(input, templateId, effectiveSlug);
    stdout = result.stdout;
    stderr = result.stderr;
  } catch (error) {
    if (!isDuplicateAgentInstanceError(error)) throw error;
    // Web forms are often re-submitted with the same draft slug. Keep the user's
    // base slug readable but make the concrete AgentInstance unique instead of
    // surfacing a 502 from SQLite.
    effectiveSlug = `${input.slug}-${Date.now().toString(36).slice(-6)}`;
    templateId = templateIdFor(input, effectiveSlug);
    await upsertTemplate(templateId);
    const retry = await createLocalAgentInstance(input, templateId, effectiveSlug);
    stdout = retry.stdout;
    stderr = retry.stderr;
  }
  await runFile("uv", ["run", "soloos", "mission-control", "export-snapshot", "--output", SNAPSHOT_PATH], { cwd: REPO_ROOT, timeout: 30_000, maxBuffer: 1024 * 1024 });
  return {
    ...baseEvent,
    template_id: templateId,
    slug: effectiveSlug,
    instance_id: stdout.match(/instance=([^\s]+)/)?.[1],
    agent_id: stdout.match(/agent=([^\s]+)/)?.[1],
    policy_status: stdout.match(/policy=([^\s]+)/)?.[1],
    lifecycle_status: stdout.match(/status=([^\s]+)/)?.[1],
    snapshot_path: "soloos-snapshot.json",
    local_warning: stderr.trim() ? "soloos_cli_wrote_stderr" : undefined,
    status: effectiveSlug === input.slug ? "agent_factory_draft_created" : "agent_factory_draft_created_with_unique_slug",
  };
}

export async function requestAgentFactoryApproval(instanceId: string, requestedBy: string, baseEvent: MissionControlEvent) {
  if (SOLOOS_API_URL) {
    const remote = await postRemote("/agent-factory/request-activation", { instance_id: instanceId, requested_by: requestedBy });
    return { ...baseEvent, ...remote, status: "agent_factory_approval_requested_remote" };
  }
  if (IS_SERVERLESS) {
    throw new MissionControlUnavailableError("local uv execution is disabled in serverless; configure SOLOOS_MISSION_CONTROL_URL");
  }
  await ensureLocalMigrations();

  const { stdout, stderr } = await runFile(
    "uv",
    ["run", "soloos", "agent-factory", "request-activation", instanceId, "--requested-by", requestedBy],
    { cwd: REPO_ROOT, timeout: 30_000, maxBuffer: 1024 * 1024 },
  );
  await runFile("uv", ["run", "soloos", "mission-control", "export-snapshot", "--output", SNAPSHOT_PATH], { cwd: REPO_ROOT, timeout: 30_000, maxBuffer: 1024 * 1024 });
  return {
    ...baseEvent,
    instance_id: stdout.match(/instance=([^\s]+)/)?.[1] ?? instanceId,
    approval_id: stdout.match(/approval=([^\s]+)/)?.[1],
    policy_status: stdout.match(/policy=([^\s]+)/)?.[1],
    risk: stdout.match(/risk=([^\s]+)/)?.[1],
    snapshot_path: "soloos-snapshot.json",
    local_warning: stderr.trim() ? "soloos_cli_wrote_stderr" : undefined,
    status: "agent_factory_approval_requested",
  };
}
