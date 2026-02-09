-- Migration 0002: Add priority column to tasks table
-- This adds a priority field for task ordering

ALTER TABLE tasks ADD COLUMN priority INTEGER DEFAULT 0;
