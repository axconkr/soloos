# SoloOS Mission Control Web Deployment

The web cockpit in `apps/web` has two runtime modes.

## 1. Local dogfood mode

Use this when running on the same machine as the SoloOS Python package and SQLite data directory.

```bash
cd apps/web
npm run dev
```

API routes call the local CLI directly:

- `POST /api/company-command` → `uv run soloos mission-control ask ...`
- `POST /api/approval-decision` → `uv run soloos mission-control decide ...`

This mode writes best-effort local audit mirrors:

- `data/web-commands.jsonl`
- `data/web-approvals.jsonl`

## 2. Hosted web / serverless mode

Serverless hosts such as Vercel should not run `uv` or write SQLite/JSONL files inside the web function. Configure the web app to call a persistent SoloOS Mission Control service instead.

Required environment variable:

```bash
SOLOOS_MISSION_CONTROL_URL=https://<persistent-soloos-service>
```

Optional outbound bearer token for the persistent SoloOS service:

```bash
SOLOOS_MISSION_CONTROL_TOKEN=<shared-secret>
```

If `SOLOOS_MISSION_CONTROL_TOKEN` is set, `SOLOOS_MISSION_CONTROL_URL` must use `https://`.

Required inbound guard for hosted deployments:

```bash
SOLOOS_REQUIRE_WEB_AUTH=1
SOLOOS_WEB_BASIC_USER=ceo
SOLOOS_WEB_BASIC_PASSWORD=<strong-dashboard-password>
```

The Basic auth gate protects the dashboard, `soloos-snapshot.json`, and mutation routes while preserving same-origin browser `fetch()` calls after the CEO signs in.

For direct API clients, a bearer-style token is also supported:

```bash
SOLOOS_WEB_API_TOKEN=<ceo-web-api-secret>
```

Direct API requests can include either:

```http
Authorization: Bearer <ceo-web-api-secret>
```

or:

```http
x-soloos-web-token: <ceo-web-api-secret>
```

For non-Vercel serverless platforms, explicitly disable local CLI execution:

```bash
SOLOOS_MISSION_CONTROL_MODE=remote
```

Expected service endpoints:

- `POST /mission-control/ask`
  - body: `{ "command": string, "source": string, "snapshot_path": string }`
  - response should include: `intent`, `routed_to`, `action_id`, optional `snapshot_path`

- `POST /mission-control/decide`
  - body: `{ "approval_id": string, "verdict": "approved" | "rejected" | "deferred", "by": string, "comment": string, "snapshot_path": string }`
  - response should include: `approval_id`, `soloos_status` or `status`, optional `snapshot_path`

If `SOLOOS_MISSION_CONTROL_URL` is missing in serverless, the API routes fail closed with `soloos_route_failed` / `soloos_decision_failed` rather than pretending a write succeeded.

## Branding blocker

No clear Phillip/AX Consulting logo asset currently exists in this repo. Do not substitute an OpenManus logo, generated placeholder, or temporary text logo for production branding.

- Header status: `TODO: brand asset required`
- Required CEO input before public production deploy: official Phillip/AX Consulting logo files, preferred favicon source, and usage rules.
- Public production deployment remains blocked until the CEO approves both brand assets and deployment.

## Verification

```bash
cd apps/web
npm run verify

cd ../..
uv run pytest -q
```

For local smoke testing:

```bash
cd apps/web
npm run start -- --port 3100
curl -sS -X POST http://127.0.0.1:3100/api/company-command \
  -H 'Content-Type: application/json' \
  --data '{"command":"이번 주 블로그 1개 초안 만들어줘","source":"curl_smoke"}'
```
