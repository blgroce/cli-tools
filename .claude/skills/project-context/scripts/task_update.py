#!/usr/bin/env python3
"""Update an existing task."""

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


def update_task(task_id, description=None, steps=None, passes=None, category=None,
                status=None, failure_reason=None):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Check if task exists
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    if cursor.fetchone() is None:
        conn.close()
        return {"error": f"Task {task_id} not found"}

    # Validate status if provided
    if status is not None and status not in VALID_STATUSES:
        conn.close()
        return {"error": f"Invalid status '{status}'. Must be one of: {', '.join(VALID_STATUSES)}"}

    # Failure reason only valid with failed status
    if failure_reason is not None and status != 'failed':
        conn.close()
        return {"error": "failure_reason can only be set when status is 'failed'"}

    # Build update query dynamically
    updates = []
    values = []

    if description is not None:
        updates.append("description = ?")
        values.append(description)
    if steps is not None:
        updates.append("steps = ?")
        values.append(steps)
    if passes is not None:
        updates.append("passes = ?")
        values.append(passes)
        # Sync status based on passes for backwards compatibility
        if status is None:
            if passes >= 1:
                updates.append("status = ?")
                values.append('complete')
            # Don't auto-set to pending if passes=0 - could be failed
    if category is not None:
        updates.append("category = ?")
        values.append(category)
    if status is not None:
        updates.append("status = ?")
        values.append(status)
        # Sync passes field for backwards compatibility
        if status == 'complete':
            updates.append("passes = ?")
            values.append(1)
        elif status in ['pending', 'in_progress', 'failed']:
            updates.append("passes = ?")
            values.append(0)
    if failure_reason is not None:
        updates.append("failure_reason = ?")
        values.append(failure_reason)

    if not updates:
        conn.close()
        return {"error": "No fields to update"}

    values.append(task_id)
    query = f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?"

    cursor.execute(query, values)
    conn.commit()

    # Fetch updated task
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    task = dict(cursor.fetchone())
    conn.close()

    return {
        "success": True,
        "message": f"Task {task_id} updated",
        "task": task
    }


def main():
    parser = argparse.ArgumentParser(description="Update a task")
    parser.add_argument("task_id", type=int, help="Task ID to update")
    parser.add_argument("--description", "-d", help="New description")
    parser.add_argument("--steps", "-s", help="New steps")
    parser.add_argument("--passes", "-p", type=int, help="Update passes count (deprecated, use --status)")
    parser.add_argument("--category", "-c", help="New category")
    parser.add_argument("--status", choices=VALID_STATUSES,
                        help="Set task status: pending, in_progress, complete, failed")
    parser.add_argument("--failure-reason",
                        help="Reason for failure (only valid with --status failed)")
    args = parser.parse_args()

    result = update_task(
        task_id=args.task_id,
        description=args.description,
        steps=args.steps,
        passes=args.passes,
        category=args.category,
        status=args.status,
        failure_reason=args.failure_reason
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
