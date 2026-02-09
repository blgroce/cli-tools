-- Migration: 0003_add_failure_handling
-- Description: Add task status tracking and agent message table for failure handling
-- Date: 2025-01-25

-- Add status column to tasks (default 'pending')
-- Values: 'pending', 'in_progress', 'complete', 'failed'
ALTER TABLE tasks ADD COLUMN status TEXT DEFAULT 'pending';

-- Add failure_reason column to tasks
ALTER TABLE tasks ADD COLUMN failure_reason TEXT;

-- Create agent_messages table for Claude-to-orchestrator communication
CREATE TABLE IF NOT EXISTS agent_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER REFERENCES tasks(id),
    run_id INTEGER REFERENCES runs(id),
    type TEXT NOT NULL,              -- 'error', 'warning', 'info', 'abort'
    message TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Migrate existing data based on passes column
-- passes=1 → status='complete', passes=0 → status='pending'
UPDATE tasks SET status = 'complete' WHERE passes = 1;
UPDATE tasks SET status = 'pending' WHERE passes = 0;

-- Update schema version
INSERT INTO schema_version (version) VALUES (3);
