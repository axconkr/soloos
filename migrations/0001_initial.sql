-- SoloOS v0.1 initial schema
-- Applied by: soloos db migrate

CREATE TABLE IF NOT EXISTS schema_migrations (
  version INTEGER PRIMARY KEY,
  applied_at INTEGER NOT NULL,
  description TEXT
);

-- ─── Users & Agents ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  display_name TEXT,
  telegram_chat_id TEXT,
  discord_id TEXT,
  email TEXT,
  timezone TEXT DEFAULT 'Asia/Seoul',
  preferences_json TEXT,
  created_at INTEGER
);

CREATE TABLE IF NOT EXISTS agents (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  mission TEXT,
  tier TEXT CHECK(tier IN ('reasoning','bulk')) NOT NULL,
  tone TEXT,
  authority_json TEXT,
  kpi_json TEXT,
  skills_json TEXT,
  status TEXT CHECK(status IN ('active','paused')) DEFAULT 'active',
  updated_at INTEGER
);

-- ─── Actions & Approvals ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS actions (
  id TEXT PRIMARY KEY,
  ts INTEGER NOT NULL,
  actor TEXT NOT NULL,
  action_type TEXT NOT NULL,
  target TEXT,
  params_json TEXT,
  policy_rule TEXT,
  status TEXT CHECK(status IN ('pending','running','success','failed','rolled_back','expired')),
  cost_krw INTEGER DEFAULT 0,
  latency_ms INTEGER,
  approval_id TEXT,
  parent_action_id TEXT,
  snapshot_ref TEXT,
  created_at INTEGER,
  completed_at INTEGER
);
CREATE INDEX IF NOT EXISTS idx_actions_ts ON actions(ts);
CREATE INDEX IF NOT EXISTS idx_actions_actor ON actions(actor);
CREATE INDEX IF NOT EXISTS idx_actions_status ON actions(status);

CREATE TABLE IF NOT EXISTS approvals (
  id TEXT PRIMARY KEY,
  created_at INTEGER NOT NULL,
  agent_id TEXT NOT NULL,
  action_type TEXT NOT NULL,
  target TEXT NOT NULL,
  preview_url TEXT,
  cost_krw INTEGER DEFAULT 0,
  risk TEXT CHECK(risk IN ('LOW','MED','HIGH')) DEFAULT 'LOW',
  policy_rule TEXT,
  status TEXT CHECK(status IN ('pending','approved','rejected','deferred','expired')) DEFAULT 'pending',
  decided_at INTEGER,
  decided_by TEXT,
  comment TEXT,
  audit_id TEXT,
  params_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_approvals_status ON approvals(status);
CREATE INDEX IF NOT EXISTS idx_approvals_created ON approvals(created_at);

-- ─── Audit Log Index ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS audit_events (
  id TEXT PRIMARY KEY,
  ts INTEGER NOT NULL,
  actor TEXT,
  action_type TEXT,
  target TEXT,
  status TEXT,
  policy_rule TEXT,
  cost_krw INTEGER,
  file_path TEXT NOT NULL,
  line_offset INTEGER NOT NULL,
  content_hash TEXT
);
CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit_events(ts);
CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit_events(actor);

-- ─── Sessions & Intents (Command Deck) ───────────────────────
CREATE TABLE IF NOT EXISTS sessions (
  session_id TEXT PRIMARY KEY,
  platform TEXT NOT NULL,
  chat_id TEXT NOT NULL,
  thread_id TEXT,
  active_agent TEXT,
  context_snapshot TEXT,
  updated_at INTEGER
);

CREATE TABLE IF NOT EXISTS intents (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts INTEGER NOT NULL,
  session_id TEXT,
  raw_text TEXT NOT NULL,
  classified_intent TEXT,
  routed_to TEXT,
  confidence REAL,
  latency_ms INTEGER
);
