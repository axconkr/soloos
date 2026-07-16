# AI Company Stack v0.1 — Phillip Personal Deployment

Status: applied to SoloOS dogfood roster and documented for Phillip first.
Owner: Phillip Hong / AX Consulting.
Scope: convert the viral “Claude as a company” pattern into a practical SoloOS operating stack, not a blind install of 42 skills.

## Executive decision

We will not install every public Claude skill/plugin immediately.

Instead, SoloOS will use a seven-department operating stack:

1. CEO Office / Chief of Staff
2. Engineering / CTO
3. Design / Brand
4. Growth / Marketing
5. Finance / CFO
6. Legal / Compliance
7. Ops / Automation

The rule is simple:

```text
Skill/plugin candidates are allowed into Phillip's operating stack only if they improve a real workflow, have clear authority boundaries, and leave evidence.
```

## Why this fits Phillip

Phillip is not trying to make a toy chatbot. The near-term goal is to run AX Consulting and SoloOS development with a small AI-native operating team.

That means the stack must support:

- real work across `ax-con.com`, `soloforge.me`, SoloOS, content, and operations;
- CEO-readable briefs, not developer logs first;
- approval gates for public publishing, money, customer contact, legal judgment, production deploys, and brand locks;
- durable evidence: files, tests, audit events, Google Docs/Sheets, URLs, screenshots, or database rows;
- selective import of external skills after compatibility review.

## Department map

### 1. CEO Office / Chief of Staff

Mission: translate Phillip's intent into priorities, decisions, and daily operating briefs.

Inputs:

- Telegram/Discord messages from Phillip
- Mission Control state
- project docs and current sprint
- pending approvals

Outputs:

- daily/weekly brief
- decision memo
- prioritized task queue
- escalation list

Authority:

- may draft priorities and decision options;
- may ask clarification when decisions matter;
- may not set strategy without Phillip approval.

Candidate skills/tools:

- product discovery
- architecture planning
- writing plans
- Mission Control summary
- session search / memory

### 2. Engineering / CTO

Mission: ship verified software changes.

Primary assets:

- SoloOS repo
- ax-con.com repo
- soloforge.me repo
- GitHub issues/PRs
- tests and CI

Outputs:

- code changes
- tests
- PRs/commits
- deployment verification
- bug reports

Authority:

- may write local code and tests;
- may create local artifacts;
- may not deploy production, modify DNS, publish public repos, or make irreversible migrations without approval.

Candidate external stack:

- `obra/superpowers` — methodology and agentic development workflow; MIT.
- `upstash/context7` — current documentation for code generation; MIT.
- `anthropics/skills` — skill templates and official examples; license needs per-skill review.
- webapp testing skills — use only after validation.

### 3. Design / Brand

Mission: create usable, tasteful interfaces and brand assets.

Outputs:

- landing page direction
- dashboard UI review
- brand guidelines
- component critique
- visual artifacts

Authority:

- may draft designs and design reviews;
- may not lock public brand direction without Phillip approval.

Candidate external stack:

- `nextlevelbuilder/ui-ux-pro-max-skill` — design intelligence; MIT.
- `Leonxlnx/taste-skill` — anti-generic design taste guidance; MIT.
- Anthropic web artifacts / brand guideline skills — candidate import after license/content review.

### 4. Growth / Marketing

Mission: turn Phillip's offers and build logs into market-facing assets.

Outputs:

- positioning
- campaign plans
- SEO briefs
- blog posts
- social posts
- lead magnets
- email drafts

Authority:

- may draft public content;
- may not publish, DM leads, or send emails externally without approval.

Candidate external stack:

- marketing skill bundles — repo slug from the viral post is truncated, so verify before import.
- `charlie947/social-media-skills` — social media skill bundle; MIT.

### 5. Finance / CFO

Mission: improve cash visibility, cost control, invoices, and finance hygiene.

Outputs:

- cash-flow summaries
- invoice drafts
- cost review
- finance checklist
- risk flags

Authority:

- may classify and summarize;
- may not move money, file taxes, provide investment advice, or make final accounting judgments.

Candidate external stack:

- Claude finance plugin pages exist, but are Claude-hosted plugin assets rather than directly portable SoloOS skills.
- Use as inspiration/checklists only until API/installation terms are confirmed.

### 6. Legal / Compliance

Mission: flag contract, NDA, privacy, and compliance risks for human review.

Outputs:

- NDA review checklist
- contract risk flags
- privacy/compliance notes
- human-lawyer escalation memo

Authority:

- may review and flag;
- may not provide final legal advice;
- may not approve contract terms.

Candidate external stack:

- Claude legal plugin page exists, but direct SoloOS portability is not yet proven.
- Use only as advisory workflow/checklist until reviewed.

### 7. Ops / Automation

Mission: keep workflows, notifications, Google Workspace, cron jobs, and delivery moving.

Outputs:

- automation runs
- Google Docs/Sheets deliverables
- Telegram/Discord notifications
- workspace organization
- operational reports

Authority:

- may run local automation;
- may not change production systems or security config without approval.

Candidate stack:

- Hermes gateway
- Google Workspace OAuth
- cron jobs
- email notification pipeline
- logs and session search

## External candidate audit snapshot

Verified by live GitHub/URL checks during this application pass:

- `https://github.com/obra/superpowers` — exists; MIT; agentic skills framework.
- `https://github.com/upstash/context7` — exists; MIT; current docs platform/MCP ecosystem.
- `https://github.com/anthropics/skills` — exists; public Agent Skills repository; license must be checked per imported skill.
- `https://github.com/thedotmack/claude-mem` — exists; Apache-2.0; memory layer; claims Hermes support.
- `https://github.com/nextlevelbuilder/ui-ux-pro-max-skill` — exists; MIT; UI/UX skill.
- `https://github.com/Leonxlnx/taste-skill` — exists; MIT; design taste skill.
- `https://github.com/charlie947/social-media-skills` — exists; MIT; social media skills.
- `https://claude.com/plugins/finance` — reachable; Claude-hosted plugin page, not automatically portable.
- `https://claude.com/plugins/small-business` — reachable; Claude-hosted plugin page, not automatically portable.
- `https://claude.com/plugins/legal` — reachable; Claude-hosted plugin page, not automatically portable.

Unresolved/truncated from the original post:

- Jakubantalik transitions link needs exact repo slug.
- coreyhaines31 marketing link needs exact repo slug.
- several Anthropic skill names need exact path under `anthropics/skills/skills/`.

## Admission criteria for importing any skill

A skill can enter Phillip's personal AI company stack only if all are true:

1. It maps to one department and one primary workflow.
2. It has no hidden required paid service unless Phillip approves.
3. Its license allows local use/adaptation.
4. It does not override SoloOS decision gates.
5. It produces or improves a verifiable artifact.
6. It can be summarized in CEO language.
7. It can be disabled without breaking the whole system.

## First operating version

The first version is intentionally conservative:

- apply the seven-agent roster in SoloOS;
- document the department playbooks;
- import external skills only after a compatibility review;
- keep Finance and Legal as checklist/advisory flows only;
- keep publishing, money, legal final judgment, customer outreach, deployment, and brand lock behind Phillip approval.

## Next implementation backlog

1. Add per-department workflow templates to SoloOS.
2. Build an import scanner that classifies candidate skill repos into: direct skill, MCP, plugin, documentation-only, incompatible.
3. Add Mission Control cards for each department: status, pending approvals, latest evidence, KPI.
4. Add Google Drive output routes for Growth/Ops deliverables.
5. Add optional skill installation scripts only after Phillip approves the chosen set.
