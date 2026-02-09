#!/usr/bin/env python3
"""List tasks from the project database."""

import argparse
import json
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(".cadi/cadi-project.sqlite")

VALID_STATUSES = ['pending', 'in_progress', 'complete', 'failed']


def get_connection():
    if not DB_PATH.exists():
        print(json.dumps({"error": f"Database not found at {DB_PATH}"}))
        sys.exit(1)
    return sqlite3.connect(DB_PATH)


def list_tasks(category=None, run_id=None, pending_only=False, status=None,
               exclude_failed=False, include_failed=False):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query = "SELECT * FROM tasks WHERE 1=1"
    params = []

    if category:
        query += " AND category = ?"
        params.append(category)

    if run_id:
        query += " AND run_id = ?"
        params.append(run_id)

    if status:
        query += " AND status = ?"
        params.append(status)
    elif pending_only:
        # --pending now uses status column, excludes failed by default
        query += " AND status = 'pending'"
    elif exclude_failed:
        query += " AND status != 'failed'"

    # Allow explicitly including failed tasks
    # (only relevant if not already filtering by specific status)
    if not include_failed and not status and not pending_only:
        # Default behavior: show all tasks including failed
        pass

    query += " ORDER BY id ASC"

    cursor.execute(query, params)
    tasks = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return {"tasks": tasks, "count": len(tasks)}


def main():
    parser = argparse.ArgumentParser(description="List project tasks")
    parser.add_argument("--category", "-c", help="Filter by category")
    parser.add_argument("--run-id", "-r", type=int, help="Filter by run ID")
    parser.add_argument("--pending", "-p", action="store_true",
                        help="Only show pending tasks (excludes failed)")
    parser.add_argument("--status", choices=VALID_STATUSES,
                        help="Filter by specific status")
    parser.add_argument("--exclude-failed", action="store_true",
                        help="Exclude failed tasks from results")
    parser.add_argument("--include-failed", action="store_true",
                        help="Include failed tasks (default when not using --pending)")
    args = parser.parse_args()

    result = list_tasks(
        category=args.category,
        run_id=args.run_id,
        pending_only=args.pending,
        status=args.status,
        exclude_failed=args.exclude_failed,
        include_failed=args.include_failed
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
