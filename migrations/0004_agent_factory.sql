-- Agent Factory / Employee Workbench substrate
-- Lets employees define governed agent templates and request activation into the roster.

CREATE TABLE IF NOT EXISTS agent_templates (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  department_agent_id TEXT NOT NULL,
  mission_template TEXT NOT NULL,
  default_authority_json TEXT NOT NULL DEFAULT '{}',
  default_kpi_json TEXT NOT NULL DEFAULT '{}',
  default_skills_json TEXT NOT NULL DEFAULT '[]',
  risk_tier TEXT CHECK(risk_tier IN ('LOW','MED','HIGH')) DEFAULT 'MED',
  status TEXT CHECK(status IN ('active','deprecated')) DEFAULT 'active',
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_agent_templates_department ON agent_templates(department_agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_templates_status ON agent_templates(status);

CREATE TABLE IF NOT EXISTS agent_instances (
  id TEXT PRIMARY KEY,
  agent_id TEXT NOT NULL UNIQUE,
  template_id TEXT NOT NULL,
  owner_agent_id TEXT NOT NULL,
  slug TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  mission TEXT NOT NULL,
  mission_vars_json TEXT NOT NULL DEFAULT '{}',
  capability_set_json TEXT NOT NULL DEFAULT '{}',
  authority_json TEXT NOT NULL DEFAULT '{}',
  kpi_json TEXT NOT NULL DEFAULT '{}',
  risk_tier TEXT CHECK(risk_tier IN ('LOW','MED','HIGH')) DEFAULT 'MED',
  lifecycle_status TEXT CHECK(lifecycle_status IN ('draft','review','active','paused','retired')) DEFAULT 'draft',
  policy_status TEXT CHECK(policy_status IN ('review_required','approval_required','approved','rejected','blocked')) DEFAULT 'review_required',
  approval_id TEXT,
  created_by TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  activated_at INTEGER,
  updated_at INTEGER NOT NULL,
  FOREIGN KEY(template_id) REFERENCES agent_templates(id)
);
CREATE INDEX IF NOT EXISTS idx_agent_instances_template ON agent_instances(template_id);
CREATE INDEX IF NOT EXISTS idx_agent_instances_owner ON agent_instances(owner_agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_instances_lifecycle ON agent_instances(lifecycle_status);
