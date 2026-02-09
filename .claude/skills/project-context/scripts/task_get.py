#!/usr/bin/env python3
"""Get a specific task by ID."""

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


def get_task(task_id):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()

    if row is None:
        conn.close()
        return {"error": f"Task {task_id} not found"}

    task = dict(row)

    # Also fetch activity count for this task
    cursor.execute(
        "SELECT COUNT(*) as count FROM activity WHERE task_id = ?",
        (task_id,)
    )
    task["activity_count"] = cursor.fetchone()["count"]

    conn.close()
    return {"task": task}


def main():
    parser = argparse.ArgumentParser(description="Get a specific task")
    parser.add_argument("task_id", type=int, help="Task ID to retrieve")
    args = parser.parse_args()

    result = get_task(args.task_id)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
