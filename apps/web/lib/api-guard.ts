import { NextResponse } from "next/server";

const WEB_API_TOKEN = process.env.SOLOOS_WEB_API_TOKEN;
const BASIC_USER = process.env.SOLOOS_WEB_BASIC_USER || "ceo";
const BASIC_PASSWORD = process.env.SOLOOS_WEB_BASIC_PASSWORD;
const REQUIRE_WEB_AUTH = process.env.SOLOOS_REQUIRE_WEB_AUTH === "1" || Boolean(process.env.SOLOOS_MISSION_CONTROL_URL);
const MAX_JSON_BYTES = 10_000;

function basicMatches(authorization: string) {
  if (!BASIC_PASSWORD || !authorization.startsWith("Basic ")) return false;
  try {
    const decoded = atob(authorization.slice("Basic ".length));
    const separator = decoded.indexOf(":");
    if (separator < 0) return false;
    const user = decoded.slice(0, separator);
    const password = decoded.slice(separator + 1);
    return user === BASIC_USER && password === BASIC_PASSWORD;
  } catch (_error) {
    return false;
  }
}

export function hasValidWebAuth(request: Request) {
  const authorization = request.headers.get("authorization") ?? "";
  const apiToken = request.headers.get("x-soloos-web-token") ?? "";
  if (WEB_API_TOKEN && (authorization === `Bearer ${WEB_API_TOKEN}` || apiToken === WEB_API_TOKEN)) return true;
  return basicMatches(authorization);
}

export function authorizeWebApi(request: Request) {
  if (!REQUIRE_WEB_AUTH) return null;
  if (!WEB_API_TOKEN && !BASIC_PASSWORD) {
    return NextResponse.json({ error: "web_api_auth_not_configured" }, { status: 500 });
  }
  if (hasValidWebAuth(request)) return null;
  return NextResponse.json({ error: "unauthorized" }, { status: 401 });
}

export async function readBoundedJson(request: Request) {
  const rawLength = request.headers.get("content-length");
  if (rawLength && Number(rawLength) > MAX_JSON_BYTES) {
    throw new Error("request_too_large");
  }

  const reader = request.body?.getReader();
  if (!reader) return await request.json();

  const chunks: Uint8Array[] = [];
  let total = 0;
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    if (value) {
      total += value.byteLength;
      if (total > MAX_JSON_BYTES) throw new Error("request_too_large");
      chunks.push(value);
    }
  }

  const buffer = new Uint8Array(total);
  let offset = 0;
  for (const chunk of chunks) {
    buffer.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return JSON.parse(new TextDecoder().decode(buffer));
}

export function boundedString(value: unknown, max: number) {
  if (typeof value !== "string") return "";
  return value.trim().slice(0, max);
}

export function stableError(error: unknown) {
  const message = error instanceof Error ? error.message : String(error);
  if (message.includes("request_too_large")) return "request_too_large";
  if (message.includes("https")) return "mission_control_transport_insecure";
  if (message.includes("SOLOOS_MISSION_CONTROL_URL")) return "mission_control_not_configured";
  if (message.includes("remote_mission_control_")) return message;
  return "mission_control_unavailable";
}

export function webAuthRequired() {
  return REQUIRE_WEB_AUTH;
}
