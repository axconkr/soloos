-- SoloOS v0.2 workflow engine schema

CREATE TABLE IF NOT EXISTS workflows (
  id TEXT PRIMARY KEY,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL,
  source_action_id TEXT,
  actor TEXT NOT NULL,
  workflow_type TEXT NOT NULL,
  title TEXT,
  params_json TEXT,
  status TEXT CHECK(status IN ('pending','running','success','failed','cancelled')) DEFAULT 'pending'
);
CREATE INDEX IF NOT EXISTS idx_workflows_status ON workflows(status);
CREATE INDEX IF NOT EXISTS idx_workflows_source_action ON workflows(source_action_id);

CREATE TABLE IF NOT EXISTS workflow_steps (
  id TEXT PRIMARY KEY,
  workflow_id TEXT NOT NULL,
  step_order INTEGER NOT NULL,
  actor TEXT NOT NULL,
  action_type TEXT NOT NULL,
  target TEXT,
  params_json TEXT,
  status TEXT CHECK(status IN ('pending','running','success','failed','skipped')) DEFAULT 'pending',
  created_at INTEGER NOT NULL,
  completed_at INTEGER,
  FOREIGN KEY (workflow_id) REFERENCES workflows(id)
);
CREATE INDEX IF NOT EXISTS idx_workflow_steps_workflow ON workflow_steps(workflow_id, step_order);
CREATE INDEX IF NOT EXISTS idx_workflow_steps_status ON workflow_steps(status);
