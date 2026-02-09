#!/usr/bin/env python3
"""List runs from the project database."""

import argparse
import json
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(".cadi/cadi-project.sqlite")


def get_connection():
    if not DB_PATH.exists():
        print(json.dumps({"error": f"Database not found at {DB_PATH}"}))
        sys.exit(1)
    return sqlite3.connect(DB_PATH)


def list_runs(status=None, mode=None, limit=10):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query = """
        SELECT r.*,
               (SELECT COUNT(*) FROM tasks WHERE run_id = r.id) as total_tasks,
               (SELECT COUNT(*) FROM tasks WHERE run_id = r.id AND passes = 0) as pending_tasks
        FROM runs r WHERE 1=1
    """
    params = []

    if status:
        query += " AND r.status = ?"
        params.append(status)

    if mode:
        query += " AND r.mode = ?"
        params.append(mode)

    query += " ORDER BY r.id DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    runs = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return {"runs": runs, "count": len(runs)}


def get_next_run():
    """Get the next run ready for execution (planning status with tasks)."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT r.*,
               (SELECT COUNT(*) FROM tasks WHERE run_id = r.id) as total_tasks,
               (SELECT COUNT(*) FROM tasks WHERE run_id = r.id AND passes = 0) as pending_tasks
        FROM runs r
        WHERE r.status = 'planning'
          AND (SELECT COUNT(*) FROM tasks WHERE run_id = r.id) > 0
        ORDER BY r.id ASC
        LIMIT 1
    """)

    row = cursor.fetchone()
    conn.close()

    if row:
        return {"run": dict(row), "command": f".cadi/loop.sh {row['id']}"}
    else:
        return {"run": None, "message": "No runs ready for execution (need 'planning' status with tasks)"}


def main():
    parser = argparse.ArgumentParser(description="List runs")
    parser.add_argument("--status", "-s", help="Filter by status (planning, running, complete, max_iterations, no_tasks)")
    parser.add_argument("--mode", "-m", help="Filter by mode (bug, prototype, feature)")
    parser.add_argument("--limit", "-l", type=int, default=10, help="Max results (default: 10)")
    parser.add_argument("--next", "-n", action="store_true", help="Get next run ready for execution")
    args = parser.parse_args()

    if args.next:
        result = get_next_run()
    else:
        result = list_runs(status=args.status, mode=args.mode, limit=args.limit)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
