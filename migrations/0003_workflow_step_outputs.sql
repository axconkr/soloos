-- SoloOS v0.3 workflow step executor output columns

ALTER TABLE workflow_steps ADD COLUMN output_ref TEXT;
ALTER TABLE workflow_steps ADD COLUMN output_text TEXT;
