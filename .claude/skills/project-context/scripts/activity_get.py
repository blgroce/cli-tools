#!/usr/bin/env python3
"""Get activity records for a task or recent activity across all tasks."""

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


def parse_json_field(value):
    """Parse JSON field, returning None if empty or invalid."""
    if value is None:
        return None
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return value


def get_activity_for_task(task_id):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Verify task exists
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    task_row = cursor.fetchone()
    if task_row is None:
        conn.close()
        return {"error": f"Task {task_id} not found"}

    task = dict(task_row)

    cursor.execute(
        """
        SELECT * FROM activity
        WHERE task_id = ?
        ORDER BY created_time DESC
        """,
        (task_id,)
    )

    activities = []
    for row in cursor.fetchall():
        activity = dict(row)
        activity["changes_made"] = parse_json_field(activity["changes_made"])
        activity["executed_commands"] = parse_json_field(activity["executed_commands"])
        activities.append(activity)

    conn.close()

    return {
        "task": task,
        "activities": activities,
        "count": len(activities)
    }


def get_recent_activity(limit=10):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT a.*, t.category, t.description as task_description
        FROM activity a
        JOIN tasks t ON a.task_id = t.id
        ORDER BY a.created_time DESC
        LIMIT ?
        """,
        (limit,)
    )

    activities = []
    for row in cursor.fetchall():
        activity = dict(row)
        activity["changes_made"] = parse_json_field(activity["changes_made"])
        activity["executed_commands"] = parse_json_field(activity["executed_commands"])
        activities.append(activity)

    conn.close()

    return {
        "activities": activities,
        "count": len(activities)
    }


def main():
    parser = argparse.ArgumentParser(description="Get activity records")
    parser.add_argument("task_id", type=int, nargs="?", help="Task ID to get activity for")
    parser.add_argument("--recent", "-r", type=int, help="Get N most recent activities across all tasks")
    args = parser.parse_args()

    if args.recent:
        result = get_recent_activity(limit=args.recent)
    elif args.task_id:
        result = get_activity_for_task(args.task_id)
    else:
        # Default to recent 10 if no args
        result = get_recent_activity(limit=10)

    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
