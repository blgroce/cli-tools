#!/usr/bin/env python3
"""Log messages from Claude to the orchestrator.

Allows Claude to send structured messages back to the loop,
including errors, warnings, info updates, and abort requests.
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(".cadi/cadi-project.sqlite")

VALID_TYPES = ['error', 'warning', 'info', 'abort']


def get_connection():
    if not DB_PATH.exists():
        print(json.dumps({"error": f"Database not found at {DB_PATH}"}))
        sys.exit(1)
    return sqlite3.connect(DB_PATH)


def log_message(message_type, message, task_id=None, run_id=None):
    """Log a message to the agent_messages table."""
    if message_type not in VALID_TYPES:
        return {"error": f"Invalid type '{message_type}'. Must be one of: {', '.join(VALID_TYPES)}"}

    if not message:
        return {"error": "Message cannot be empty"}

    conn = get_connection()
    cursor = conn.cursor()

    # Validate task_id if provided
    if task_id is not None:
        cursor.execute("SELECT id FROM tasks WHERE id = ?", (task_id,))
        if cursor.fetchone() is None:
            conn.close()
            return {"error": f"Task {task_id} not found"}

    # Validate run_id if provided
    if run_id is not None:
        cursor.execute("SELECT id FROM runs WHERE id = ?", (run_id,))
        if cursor.fetchone() is None:
            conn.close()
            return {"error": f"Run {run_id} not found"}

    # Insert the message
    cursor.execute("""
        INSERT INTO agent_messages (task_id, run_id, type, message)
        VALUES (?, ?, ?, ?)
    """, (task_id, run_id, message_type, message))

    message_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {
        "success": True,
        "message_id": message_id,
        "type": message_type,
        "logged": message
    }


def main():
    parser = argparse.ArgumentParser(
        description="Log a message from Claude to the orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Message types:
  error    - Task-blocking error (task cannot be completed)
  warning  - Non-blocking issue (task can continue)
  info     - Status update
  abort    - Request immediate loop termination

Examples:
  %(prog)s --type error --message "Cannot access GitHub API" --task-id 5 --run-id 12
  %(prog)s --type abort --message "Database corrupted" --run-id 12
  %(prog)s --type info --message "Starting task implementation" --task-id 5
"""
    )
    parser.add_argument("--type", "-t", required=True, choices=VALID_TYPES,
                        help="Message type")
    parser.add_argument("--message", "-m", required=True,
                        help="Message content")
    parser.add_argument("--task-id", type=int,
                        help="Associated task ID (optional)")
    parser.add_argument("--run-id", type=int,
                        help="Associated run ID (optional)")
    args = parser.parse_args()

    result = log_message(
        message_type=args.type,
        message=args.message,
        task_id=args.task_id,
        run_id=args.run_id
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
