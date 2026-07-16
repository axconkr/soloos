# SoloOS Agent Operating Constitution

This repository uses shared project-level instructions for every AI coding or operating agent that works inside SoloOS.

Read this file first, then read [`docs/AGENT_OPERATING_CONSTITUTION.md`](docs/AGENT_OPERATING_CONSTITUTION.md) for the detailed rules.

## Non-negotiables

1. **Do not copy leaked system prompts verbatim.** Public prompt archives can inspire patterns, but SoloOS must use distilled, original operating rules that fit this product.
2. **CEO-readable output first.** SoloOS exists to help Phillip run AX Consulting. Translate technical events into: status, completed work, decision needed, evidence.
3. **Evidence or it did not happen.** Any claim of completion must point to a file, command output, URL, DB row, screenshot, or audit event.
4. **Decision gates stay with Phillip.** Publishing, customer outreach, spending, irreversible changes, or strategy choices require explicit CEO approval unless Phillip already delegated that class of decision.
5. **TDD for behavior changes.** New code paths, CLI behavior, DB writes, workflow execution, and dashboard changes need a failing test first.
6. **Secrets never enter artifacts.** API keys, tokens, credentials, customer private data, and personal data must not be committed, displayed, logged, or added to generated documents.
7. **When work touches the Mission Control UI,** verify it from the CEO view: browser opens, console clean, live snapshot visible, next action clear.

## Operating loop

Use this loop for every meaningful task:

```text
Understand goal → inspect context → plan smallest safe change → execute → verify → report in CEO language
```

## Reporting format

Prefer this final structure:

```text
Done:
- What changed

Verified:
- Exact command/output or URL/screenshot

CEO view:
- What it means
- What Phillip should decide next

Caution:
- Any remaining risk, missing auth, temporary process, or blocker
```

## Project-specific reminders

- `apps/web` is the Mission Control UI.
- `apps/web/public/soloos-snapshot.json` is the live-data bridge for the current dashboard.
- `src/soloos/mission_control_snapshot.py` exports live SQLite state for the UI.
- `.stitch/DESIGN.md` is the shared design-system source for Stitch and coding agents.
- `docs/STITCH_AGENT_WORKFLOW.md` defines the Stitch → React workflow; generated UI is draft until tests/browser verification pass.
- `mc.ax-con.com` should remain CEO-readable, not developer-log-first.
- Keep detailed logs behind a disclosure such as “상세 로그 보기”.
