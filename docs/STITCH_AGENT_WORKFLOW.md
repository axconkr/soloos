# Stitch Agent Workflow for SoloOS Mission Control

This repo is prepared to use Google Stitch + `google-labs-code/stitch-skills` as a design-to-code loop for `apps/web`.

## What was installed

- Codex marketplace: `google-labs-code/stitch-skills` on `main`
- Claude Code project plugins:
  - `stitch-design`
  - `stitch-build`
  - `stitch-utilities`
- SoloOS design system for Stitch and coding agents:
  - `.stitch/DESIGN.md`

## Prerequisite

The installed skills require the Stitch MCP server to be configured in the agent environment. Without Stitch MCP auth, agents can still read `.stitch/DESIGN.md`, but they cannot create or sync real Stitch projects.

Set up Stitch MCP from Google Stitch docs, then restart the agent tool that will use it.

## Recommended SoloOS loop

### 1. Existing code to Stitch

Use this when the current Mission Control UI should be redesigned in Stitch:

```text
Use stitch::code-to-design to upload apps/web into a Stitch project named "AX Consulting Mission Control". Use .stitch/DESIGN.md as the design system. Preserve the CEO-readable dashboard structure and approval/evidence hierarchy.
```

### 2. Prompt or screenshot to design

Use this when creating new screens such as Approvals, Audit, Agents, or Artifacts:

```text
Use stitch::generate-design to create a dark CEO cockpit screen for [screen name]. Follow .stitch/DESIGN.md. The screen must show status, decision needed, next action, and evidence.
```

### 3. Apply design system

```text
Use stitch::manage-design-system to upload .stitch/DESIGN.md and apply it to every screen in the Stitch project.
```

### 4. Stitch design to React

```text
Use stitch::react-components to sync the latest Stitch project into apps/web. Keep Next.js 15, TypeScript, and the existing snapshot bridge at apps/web/public/soloos-snapshot.json.
```

### 5. Verify before reporting done

Run at minimum:

```bash
cd apps/web
npm run verify
npm audit --audit-level=moderate
```

Then open the dashboard in a browser and confirm:

- page renders
- browser console has no errors
- CEO answer card is visible
- live snapshot data is visible
- approval/risk states are not hidden

## Guardrails

- Do not let Stitch output overwrite SoloOS business logic without review.
- Treat generated React as a draft until typecheck/build/browser verification passes.
- Keep generated design assets free of credentials and customer private data.
- Phillip keeps decision gates for publishing, customer outreach, spending, and strategy.
