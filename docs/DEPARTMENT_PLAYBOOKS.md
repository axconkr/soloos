# Department Playbooks — Phillip Personal AI Company

These playbooks define how SoloOS should route Phillip's requests before deeper workflow automation exists.

## Universal routing rule

```text
If a request affects public reputation, money, customers, legal risk, production systems, or strategy, prepare options and ask Phillip before execution.
Otherwise, execute the smallest reversible step, verify, and report evidence.
```

## Intake classifier

### Route to CEO Office when Phillip asks for:

- prioritization
- “what should we do next?”
- business direction
- weekly or daily brief
- decision comparison
- cross-department coordination

Default output:

```text
Status:
Decision needed:
Options:
Recommendation:
Evidence:
Next action:
```

### Route to Engineering / CTO when Phillip asks for:

- code changes
- tests
- bugs
- deployments
- GitHub work
- web app verification
- infrastructure changes

Default operating loop:

```text
Inspect repo → write failing test for behavior change → implement → run targeted tests → run broader checks → report exact output
```

Hard gates:

- production deployment
- DNS/domain changes
- auth/security changes
- irreversible migrations
- public repo creation

### Route to Design / Brand when Phillip asks for:

- landing page design
- UI/UX review
- dashboard layout
- brand guideline
- visual direction
- presentation visuals

Default output:

```text
Design goal:
Audience:
Proposed direction:
Concrete changes/assets:
Approval needed:
```

Hard gates:

- public brand change
- logo/identity lock
- permanent style guide replacement

### Route to Growth / Marketing when Phillip asks for:

- blog posts
- SEO
- social posts
- campaigns
- sales copy
- newsletters
- lead magnets
- launch plans

Default output:

```text
Target audience:
Offer:
Angle:
Draft assets:
Distribution plan:
Approval needed before publishing:
```

Hard gates:

- posting publicly
- sending external emails/DMs
- claims about client results without evidence
- paid ads/spend

### Route to Finance / CFO when Phillip asks for:

- invoice drafts
- cash flow
- cost review
- subscriptions
- financial summaries
- payment reminders

Default output:

```text
Finance summary:
Known numbers:
Missing data:
Risk flags:
Recommended next check:
```

Hard gates:

- moving money
- filing tax documents
- legal accounting conclusions
- investment decisions

### Route to Legal / Compliance when Phillip asks for:

- contract review
- NDA review
- privacy policy
- terms
- compliance
- IP/licensing questions

Default output:

```text
Not legal advice:
Issue summary:
Risk flags:
Questions for lawyer/client:
Suggested safe wording:
Human review required:
```

Hard gates:

- final legal advice
- contract approval
- signing authority
- privacy/security promises to customers

### Route to Ops / Automation when Phillip asks for:

- Google Docs/Sheets deliverables
- notifications
- calendar/admin work
- recurring reports
- workspace organization
- scheduled checks
- integration glue

Default operating loop:

```text
Confirm target system → create/update artifact → verify link/file/API response → notify Phillip
```

Hard gates:

- changing production automations
- new external costs
- bulk emailing/messaging
- credential changes

## Department handoff rules

- Engineering → Design: when a UI works but needs CEO-readable visual polish.
- Design → Engineering: when a design must become React/Next code.
- Growth → Legal: when public content includes strong claims, pricing, guarantees, regulated topics, or customer references.
- Growth → Design: when content needs landing page, thumbnail, deck, or visual identity.
- Finance → Ops: when invoices, reminders, or reports need recurring automation.
- CEO Office → any department: when a decision is made and execution starts.

## Evidence requirements by department

- CEO Office: decision memo path, brief path, or Mission Control card.
- Engineering: test output, diff, commit, URL, screenshot, or CLI output.
- Design: artifact file, screenshot, design token diff, or prototype URL.
- Growth: Google Doc URL, markdown draft path, content calendar, or campaign brief.
- Finance: spreadsheet URL/path, source file reference, or calculation script output.
- Legal: checklist/memo path and explicit “not legal advice” marker.
- Ops: API response, cron job ID, Google Drive URL, message delivery evidence, or log path.

## Daily personal application for Phillip

A good default day in this stack:

1. CEO Office summarizes status and pending decisions.
2. Engineering advances one verified SoloOS/product change.
3. Growth drafts one publishable asset but does not publish without approval.
4. Ops turns finished assets into Google Docs/Sheets or scheduled reminders.
5. Finance/Legal only enter when a request touches money, contracts, compliance, or risk.

## Weekly personal application for Phillip

Every week, generate:

- CEO brief: wins, blockers, decisions, next week focus.
- Engineering report: shipped, verified, failing, next build.
- Growth report: content shipped/drafted, leads, campaign ideas.
- Ops report: automations, pending admin, workspace hygiene.
- Risk report: finance/legal/compliance flags only if relevant.
