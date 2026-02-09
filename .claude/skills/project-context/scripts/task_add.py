#!/usr/bin/env python3
"""Add a new task to the project database."""

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


def add_task(category, description, steps=None, run_id=None):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO tasks (category, description, steps, passes, run_id)
        VALUES (?, ?, ?, 0, ?)
        """,
        (category, description, steps, run_id)
    )

    task_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {
        "success": True,
        "task_id": task_id,
        "message": f"Task {task_id} created successfully"
    }


def main():
    parser = argparse.ArgumentParser(description="Add a new task")
    parser.add_argument("--category", "-c", required=True, help="Task category")
    parser.add_argument("--description", "-d", required=True, help="Task description")
    parser.add_argument("--steps", "-s", help="Steps to complete the task")
    parser.add_argument("--run-id", "-r", type=int, help="Run ID to assign task to")
    args = parser.parse_args()

    result = add_task(
        category=args.category,
        description=args.description,
        steps=args.steps,
        run_id=args.run_id
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
