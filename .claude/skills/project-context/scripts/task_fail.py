#!/usr/bin/env python3
"""Mark a task as permanently failed with a reason.

This script sets a task's status to 'failed', records the failure reason,
and automatically logs an error message to agent_messages.
"""

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


def fail_task(task_id, reason):
    """Mark a task as failed with the given reason."""
    if not reason:
        return {"error": "Failure reason is required"}

    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Check if task exists and get run_id
    cursor.execute("SELECT id, run_id, status FROM tasks WHERE id = ?", (task_id,))
    task = cursor.fetchone()
    if task is None:
        conn.close()
        return {"error": f"Task {task_id} not found"}

    if task['status'] == 'complete':
        conn.close()
        return {"error": f"Task {task_id} is already complete and cannot be failed"}

    if task['status'] == 'failed':
        conn.close()
        return {"error": f"Task {task_id} is already marked as failed"}

    run_id = task['run_id']

    # Update task status to failed
    cursor.execute("""
        UPDATE tasks
        SET status = 'failed', failure_reason = ?, passes = 0
        WHERE id = ?
    """, (reason, task_id))

    # Auto-log an error message to agent_messages
    cursor.execute("""
        INSERT INTO agent_messages (task_id, run_id, type, message)
        VALUES (?, ?, 'error', ?)
    """, (task_id, run_id, f"Task failed: {reason}"))

    conn.commit()

    # Fetch updated task
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    updated_task = dict(cursor.fetchone())
    conn.close()

    return {
        "success": True,
        "message": f"Task {task_id} marked as failed",
        "reason": reason,
        "task": updated_task
    }


def main():
    parser = argparse.ArgumentParser(
        description="Mark a task as permanently failed",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Use this when a task encounters an unrecoverable blocker:
  - Missing credentials/access you cannot obtain
  - Impossible requirements or contradictions
  - External service unavailable
  - Architectural mismatch

Examples:
  %(prog)s 5 --reason "Cannot access external API - authentication required"
  %(prog)s 12 --reason "Feature requires Python 3.12, project uses 3.9"
"""
    )
    parser.add_argument("task_id", type=int, help="Task ID to fail")
    parser.add_argument("--reason", "-r", required=True,
                        help="Explanation of why the task cannot be completed")
    args = parser.parse_args()

    result = fail_task(args.task_id, args.reason)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
