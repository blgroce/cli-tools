-- CADI Database Schema
-- Version: 1
-- Description: Complete schema for CADI project tracking database
--
-- This schema defines all tables needed for CADI to function.
-- Use this file to initialize a fresh database.
-- For upgrades, use migration files in ./migrations/

-- Schema version tracking
-- This table tracks which schema version the database is at
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Insert current schema version
INSERT INTO schema_version (version) VALUES (4);

-- Runs table
-- Tracks execution batches with mode and status
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mode TEXT NOT NULL,              -- 'bug', 'prototype', 'feature'
    max_iterations INTEGER,          -- Loop iteration limit
    summary TEXT,                    -- Overall context about what this run is building
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME,
    status TEXT DEFAULT 'running'    -- 'planning', 'running', 'complete', 'failed', 'aborted', 'max_iterations', 'no_tasks'
);

-- Tasks table
-- Individual work items assigned to runs
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER REFERENCES runs(id),
    category TEXT NOT NULL,          -- Task category (e.g., 'feature', 'bug', 'debug')
    description TEXT NOT NULL,       -- What to do
    steps TEXT,                      -- Detailed steps (optional)
    passes INTEGER DEFAULT 0,        -- 0 = pending, 1 = complete (legacy, use status)
    status TEXT DEFAULT 'pending',   -- 'pending', 'in_progress', 'complete', 'failed'
    failure_reason TEXT              -- Why the task failed (only set when status='failed')
);

-- Activity table
-- Audit trail of task execution
CREATE TABLE IF NOT EXISTS activity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    created_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    changes_made JSON,               -- List of changes
    executed_commands JSON,          -- Commands run
    reference_screenshot_path TEXT,  -- Proof file path
    issues_and_resolutions TEXT,     -- Problems solved
    FOREIGN KEY (task_id) REFERENCES tasks(id)
);

-- Documentation table
-- Index of project documentation
CREATE TABLE IF NOT EXISTS documentation (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL,              -- File path
    title TEXT NOT NULL,             -- Document title
    summary TEXT NOT NULL,           -- One-line description
    category TEXT,                   -- 'infra', 'api', 'feature', etc.
    tags JSON,                       -- Search tags
    created_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Agent messages table
-- Communication channel from Claude to the orchestrator
CREATE TABLE IF NOT EXISTS agent_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER REFERENCES tasks(id),
    run_id INTEGER REFERENCES runs(id),
    type TEXT NOT NULL,              -- 'error', 'warning', 'info', 'abort'
    message TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
