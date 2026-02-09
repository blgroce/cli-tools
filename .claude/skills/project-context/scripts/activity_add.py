#!/usr/bin/env python3
"""Add an activity record for a task."""

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


def add_activity(task_id, changes=None, commands=None, issues=None, screenshot=None):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Verify task exists
    cursor.execute("SELECT id FROM tasks WHERE id = ?", (task_id,))
    if cursor.fetchone() is None:
        conn.close()
        return {"error": f"Task {task_id} not found"}

    # Parse JSON arrays if provided as strings
    changes_json = None
    commands_json = None

    if changes:
        if isinstance(changes, str):
            try:
                changes_json = json.dumps(json.loads(changes))
            except json.JSONDecodeError:
                # Treat as single item if not valid JSON
                changes_json = json.dumps([changes])
        else:
            changes_json = json.dumps(changes)

    if commands:
        if isinstance(commands, str):
            try:
                commands_json = json.dumps(json.loads(commands))
            except json.JSONDecodeError:
                commands_json = json.dumps([commands])
        else:
            commands_json = json.dumps(commands)

    cursor.execute(
        """
        INSERT INTO activity (task_id, changes_made, executed_commands,
                              issues_and_resolutions, reference_screenshot_path)
        VALUES (?, ?, ?, ?, ?)
        """,
        (task_id, changes_json, commands_json, issues, screenshot)
    )

    activity_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {
        "success": True,
        "activity_id": activity_id,
        "task_id": task_id,
        "message": f"Activity {activity_id} recorded for task {task_id}"
    }


def main():
    parser = argparse.ArgumentParser(description="Add activity record for a task")
    parser.add_argument("task_id", type=int, help="Task ID this activity belongs to")
    parser.add_argument("--changes", "-c", help="Changes made (JSON array or string)")
    parser.add_argument("--commands", "-x", help="Commands executed (JSON array or string)")
    parser.add_argument("--issues", "-i", help="Issues encountered and resolutions")
    parser.add_argument("--screenshot", "-s", help="Path to reference screenshot")
    args = parser.parse_args()

    result = add_activity(
        task_id=args.task_id,
        changes=args.changes,
        commands=args.commands,
        issues=args.issues,
        screenshot=args.screenshot
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
