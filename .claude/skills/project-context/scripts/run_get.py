#!/usr/bin/env python3
"""Get a single run from the project database."""

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


def get_run(run_id):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT r.*,
               (SELECT COUNT(*) FROM tasks WHERE run_id = r.id) as total_tasks,
               (SELECT COUNT(*) FROM tasks WHERE run_id = r.id AND passes = 0) as pending_tasks
        FROM runs r
        WHERE r.id = ?
        """,
        (run_id,)
    )

    row = cursor.fetchone()
    conn.close()

    if row:
        return {"run": dict(row)}
    else:
        return {"error": f"Run {run_id} not found"}


def main():
    parser = argparse.ArgumentParser(description="Get a single run")
    parser.add_argument("run_id", type=int, help="Run ID to retrieve")
    args = parser.parse_args()

    result = get_run(args.run_id)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
