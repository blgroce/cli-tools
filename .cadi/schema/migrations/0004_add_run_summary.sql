-- Migration 0004: Add summary column to runs table
-- This provides overall context about what the run is building

ALTER TABLE runs ADD COLUMN summary TEXT;
