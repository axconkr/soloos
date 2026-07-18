# SoloOS — Data Model (v0.1)

**Scope:** Cross-module data schemas. Each module owns its tables but this doc unifies the shape.

**Storage:**
- **Primary DB**: SQLite `data/soloos.sqlite` (WAL mode)
- **Vectors**: sqlite-vec extension on same file (`data/soloos.sqlite`, virtual table)
- **Files**: `data/audit/*.jsonl`, `data/workspace/**`, `data/snapshots/**`
- **KV**: Hermes-managed session store (short-lived)

---

## 1. Entity Overview

```
┌────────┐      ┌──────────┐      ┌──────────┐
│  User  │──1:1─│  Agent   │──1:N─│  Action  │
└────────┘      └──────────┘      └────┬─────┘
    │                                   │
    │                                   ├─► approval (optional)
    │                                   ├─► audit_event
    │                                   └─► snapshot (if destructive)
    ▼
┌──────────┐     ┌────────┐     ┌─────────┐
│ Contact  │─1:N─│  Deal  │─1:N─│ Invoice │
└──────────┘     └────────┘     └─────────┘
    │                │
    │                ▼
    │           ┌──────────┐
    └──1:N─────▶│  Note    │──► embedding (vector)
                └──────────┘
```

---

## 2. Core Tables

### 2.1 users
```sql
CREATE TABLE users (
  id TEXT PRIMARY KEY,          -- 'ceo' for solopreneur
  display_name TEXT,
  telegram_chat_id TEXT,
  discord_id TEXT,
  email TEXT,
  timezone TEXT DEFAULT 'Asia/Seoul',
  preferences_json TEXT,
  created_at INTEGER
);
```

### 2.2 agents
```sql
CREATE TABLE agents (
  id TEXT PRIMARY KEY,          -- 'agent:cmo', 'agent:sales', ...
  name TEXT NOT NULL,
  mission TEXT,
  tier TEXT CHECK(tier IN ('reasoning','bulk')) NOT NULL,
  tone TEXT,
  authority_json TEXT,          -- JSON: {auto:[], requires_approval:[]}
  kpi_json TEXT,                -- JSON: weekly targets
  skills_json TEXT,             -- JSON array of skill ids
  status TEXT CHECK(status IN ('active','paused')) DEFAULT 'active',
  updated_at INTEGER
);
```

### 2.3 actions (audit-relevant runtime record)
```sql
CREATE TABLE actions (
  id TEXT PRIMARY KEY,          -- 'A-0421'
  ts INTEGER NOT NULL,
  actor TEXT NOT NULL,          -- 'agent:cmo' | 'user:ceo' | 'system'
  action_type TEXT NOT NULL,    -- draft_content, spend_money, ...
  target TEXT,                  -- resource ref
  params_json TEXT,
  policy_rule TEXT,             -- rule id or 'auto'
  status TEXT CHECK(status IN ('pending','running','success','failed','rolled_back','expired')),
  cost_krw INTEGER DEFAULT 0,
  latency_ms INTEGER,
  approval_id TEXT,             -- FK approvals.id (nullable)
  parent_action_id TEXT,        -- for chained actions
  snapshot_ref TEXT,            -- filesystem path if destructive
  created_at INTEGER,
  completed_at INTEGER,
  FOREIGN KEY (approval_id) REFERENCES approvals(id)
);
CREATE INDEX idx_actions_ts ON actions(ts);
CREATE INDEX idx_actions_actor ON actions(actor);
CREATE INDEX idx_actions_status ON actions(status);
```

### 2.4 workflows / workflow_steps
```sql
CREATE TABLE workflows (
  id TEXT PRIMARY KEY,          -- 'WF-0001'
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL,
  source_action_id TEXT,        -- actions.id that created the workflow
  actor TEXT NOT NULL,          -- 'agent:cmo'
  workflow_type TEXT NOT NULL,  -- content_plan, sales_followup, ...
  title TEXT,
  params_json TEXT,
  status TEXT CHECK(status IN ('pending','running','success','failed','cancelled')) DEFAULT 'pending'
);
CREATE INDEX idx_workflows_status ON workflows(status);
CREATE INDEX idx_workflows_source_action ON workflows(source_action_id);

CREATE TABLE workflow_steps (
  id TEXT PRIMARY KEY,          -- 'WS-0001'
  workflow_id TEXT NOT NULL,
  step_order INTEGER NOT NULL,
  actor TEXT NOT NULL,
  action_type TEXT NOT NULL,    -- draft_content, research_lead, ...
  target TEXT,
  params_json TEXT,
  status TEXT CHECK(status IN ('pending','running','success','failed','skipped')) DEFAULT 'pending',
  created_at INTEGER NOT NULL,
  completed_at INTEGER,
  output_ref TEXT,              -- file:///.../data/workspace/content/WF-0001/WS-0001.md
  output_text TEXT,             -- short executor summary for CLI/table display
  FOREIGN KEY (workflow_id) REFERENCES workflows(id)
);
CREATE INDEX idx_workflow_steps_workflow ON workflow_steps(workflow_id, step_order);
CREATE INDEX idx_workflow_steps_status ON workflow_steps(status);
```

MVP behavior: `agent:cmo/content_plan` creates one workflow with N `draft_content` pending steps and stores `actions.snapshot_ref='workflow://WF-...'`. `soloos workflows run-step WF-...` claims the oldest pending step, marks it `running`, calls the `AgentRunner` seam (`DeterministicAgentRunner` by default until live LLM runners are enabled), writes the returned Markdown draft to `data/workspace/content/WF-.../WS-....md`, stores `output_ref='file://...'` plus a short `output_text` summary, marks the step `success`, and emits a `workflow_step_run` audit event (`id='STEP-WS-...'`, `target='workflow:WF-...:step:WS-...'`, `extras.runner=<runner>`). If step execution raises, the step is marked `failed`, `output_ref='workflow-output://WF-.../WS-.../failed'`, an audit event with `status='failed'` is emitted, and the parent workflow becomes `failed`. `soloos workflows retry-step WF-... WS-...` resets a failed step to `pending`, clears `completed_at`/outputs, sets the parent workflow back to `pending`, and emits `workflow_step_retry`. The workflow becomes `success` only when no pending/running steps remain.

### 2.5 approvals
(see `M1_COMMAND_DECK.md` §4 — canonical definition)

### 2.6 audit_events (index over JSONL)
```sql
CREATE TABLE audit_events (
  id TEXT PRIMARY KEY,
  ts INTEGER NOT NULL,
  actor TEXT, action_type TEXT, target TEXT,
  status TEXT, policy_rule TEXT, cost_krw INTEGER,
  file_path TEXT NOT NULL,
  line_offset INTEGER NOT NULL,
  content_hash TEXT
);
CREATE INDEX idx_audit_ts ON audit_events(ts);
```

**Integrity note:** `data/audit/*.jsonl` is the source of truth. `audit_events` is a rebuildable SQLite index; if an index write fails after JSONL append, run `soloos audit reindex`. Use `soloos audit show <event_id>` to read the full JSONL record, including `extras` such as workflow output refs.

### 2.7 id_counters (internal sequence allocator)
```sql
CREATE TABLE id_counters (
  prefix TEXT PRIMARY KEY,      -- e.g. 'A', 'AP', 'C', 'D'
  next_value INTEGER NOT NULL DEFAULT 1
);
```

`soloos.ids.next_id()` updates this table inside `BEGIN IMMEDIATE` to avoid duplicate IDs under concurrent processes. It is created lazily by the ID service because it is internal infrastructure, not a domain entity.

### 2.8 Command Deck reserved tables

`sessions` and `intents` are created by the initial migration for M1 Command Deck. They are used by `soloos.command_deck.CommandDeck.handle_text()` to persist chat routing state and the deterministic classifier history for the current CLI smoke path; Telegram/Discord gateway handlers will reuse the same tables.

---

## 3. Revenue Loop Tables

### 3.1 contacts
```sql
CREATE TABLE contacts (
  id TEXT PRIMARY KEY,          -- 'C-0123'
  name TEXT NOT NULL,
  company TEXT,
  email TEXT,
  phone TEXT,
  source TEXT,                  -- 'tally', 'referral', 'linkedin', ...
  first_seen INTEGER,
  last_touch INTEGER,
  tags_json TEXT,               -- ['hot', 'enterprise']
  notes TEXT
);
CREATE INDEX idx_contacts_email ON contacts(email);
```

### 3.2 deals
```sql
CREATE TABLE deals (
  id TEXT PRIMARY KEY,          -- 'D-0089'
  contact_id TEXT NOT NULL,
  title TEXT,
  stage TEXT CHECK(stage IN ('LEAD','QUALIFY','PROPOSAL','CONTRACT','INVOICE','COLLECT','WON','LOST')),
  size_krw INTEGER,
  probability REAL DEFAULT 0.3,
  expected_close INTEGER,
  actual_close INTEGER,
  owner TEXT DEFAULT 'agent:sales',
  next_action TEXT,
  next_action_due INTEGER,
  created_at INTEGER,
  updated_at INTEGER,
  FOREIGN KEY (contact_id) REFERENCES contacts(id)
);
CREATE INDEX idx_deals_stage ON deals(stage);
CREATE INDEX idx_deals_close ON deals(expected_close);
```

### 3.3 invoices
```sql
CREATE TABLE invoices (
  id TEXT PRIMARY KEY,          -- 'INV-041'
  deal_id TEXT,
  contact_id TEXT,
  amount_krw INTEGER NOT NULL,
  currency TEXT DEFAULT 'KRW',
  issued_at INTEGER,
  due_at INTEGER,
  paid_at INTEGER,
  status TEXT CHECK(status IN ('draft','issued','paid','overdue','void')),
  provider TEXT,                -- 'stripe' | 'toss' | 'manual'
  provider_ref TEXT,
  pdf_path TEXT
);
```

---

## 4. Memory Cortex Tables

### 4.1 notes (raw content)
```sql
CREATE TABLE notes (
  id TEXT PRIMARY KEY,          -- 'N-....'
  layer TEXT CHECK(layer IN ('personal','org','project')) NOT NULL,
  scope TEXT,                   -- project_id or 'global'
  source TEXT,                  -- 'telegram', 'gdoc', 'gmail', ...
  source_ref TEXT,              -- URL or ID
  title TEXT,
  content TEXT NOT NULL,
  content_hash TEXT UNIQUE,
  created_at INTEGER,
  ingested_at INTEGER
);
CREATE INDEX idx_notes_layer_scope ON notes(layer, scope);
```

### 4.2 embeddings (sqlite-vec virtual)
```sql
-- Requires sqlite-vec extension loaded
CREATE VIRTUAL TABLE embeddings USING vec0(
  note_id TEXT PRIMARY KEY,
  embedding FLOAT[1536]         -- text-embedding-3-small
);
```

**Search:**
```sql
SELECT n.id, n.title, n.content, distance
FROM embeddings e
JOIN notes n ON n.id = e.note_id
WHERE e.embedding MATCH ? AND k = 5
  AND n.layer IN ('org','project')
ORDER BY distance;
```

---

## 5. Ledger & Metrics Tables

### 5.1 metrics_daily
```sql
CREATE TABLE metrics_daily (
  date TEXT PRIMARY KEY,        -- 'YYYY-MM-DD'
  revenue_krw INTEGER DEFAULT 0,
  expense_krw INTEGER DEFAULT 0,
  new_leads INTEGER DEFAULT 0,
  deals_won INTEGER DEFAULT 0,
  deals_lost INTEGER DEFAULT 0,
  tasks_completed INTEGER DEFAULT 0,
  approvals_pending INTEGER DEFAULT 0,
  llm_cost_usd REAL DEFAULT 0,
  ads_cost_krw INTEGER DEFAULT 0,
  extras_json TEXT
);
```

### 5.2 anomalies
```sql
CREATE TABLE anomalies (
  id TEXT PRIMARY KEY,
  detected_at INTEGER NOT NULL,
  metric TEXT NOT NULL,
  value REAL, baseline REAL, sigma REAL,
  severity TEXT CHECK(severity IN ('info','warn','critical')),
  notified_at INTEGER,
  status TEXT CHECK(status IN ('open','acknowledged','resolved')) DEFAULT 'open'
);
```

---

## 6. Workflow Tables

### 6.1 workflows (persisted plans)
```sql
CREATE TABLE workflows (
  id TEXT PRIMARY KEY,
  trigger_type TEXT,            -- 'user_command' | 'cron' | 'webhook' | 'event'
  trigger_ref TEXT,
  goal TEXT,
  plan_json TEXT,               -- ordered steps
  status TEXT CHECK(status IN ('planned','running','paused','done','failed','aborted')),
  created_at INTEGER,
  updated_at INTEGER
);

CREATE TABLE workflow_steps (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  workflow_id TEXT NOT NULL,
  seq INTEGER NOT NULL,
  agent_id TEXT,
  action_type TEXT,
  params_json TEXT,
  action_id TEXT,               -- FK actions.id when executed
  status TEXT,
  started_at INTEGER,
  finished_at INTEGER,
  FOREIGN KEY (workflow_id) REFERENCES workflows(id)
);
```

---

## 7. Naming Conventions

| Prefix | Domain |
|--------|--------|
| `A-` | Action |
| `AP-` | Approval |
| `C-` | Contact |
| `D-` | Deal |
| `INV-` | Invoice |
| `N-` | Note |
| `W-` | Workflow |
| `AN-` | Anomaly |

All IDs zero-padded to 4 digits initially, auto-widen when overflowing.

---

## 8. Retention Policy

| Data | Hot | Warm | Cold |
|------|-----|------|------|
| Sessions | 7d SQLite | archive → notes | discard |
| Audit JSONL | 90d local | S3/Drive | discard after 2y |
| Actions (SQLite) | 1y | export CSV | truncate |
| Notes/Embeddings | forever | — | opt-in prune |
| Metrics daily | forever | — | — |
| Snapshots (destructive undo) | 30d | — | discard |

---

## 9. Migration Strategy

- Migrations under `soloos/migrations/NNNN_description.sql`
- Applied via `soloos db migrate` CLI (implemented Week 1 Day 5)
- Each migration idempotent; version tracked in `schema_migrations` table.
