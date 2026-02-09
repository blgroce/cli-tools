#!/usr/bin/env python3
"""Create a new run in the project database."""

import argparse
import json
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(".cadi/cadi-project.sqlite")
VALID_MODES = ["bug", "prototype", "feature"]


def get_connection():
    if not DB_PATH.exists():
        print(json.dumps({"error": f"Database not found at {DB_PATH}"}))
        sys.exit(1)
    return sqlite3.connect(DB_PATH)


def create_run(mode, max_iterations=10, summary=None):
    if mode not in VALID_MODES:
        return {"error": f"Invalid mode '{mode}'. Valid: {VALID_MODES}"}

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO runs (mode, max_iterations, summary, status)
        VALUES (?, ?, ?, 'planning')
        """,
        (mode, max_iterations, summary)
    )

    run_id = cursor.lastrowid
    conn.commit()
    conn.close()

    result = {
        "success": True,
        "run_id": run_id,
        "mode": mode,
        "max_iterations": max_iterations,
        "message": f"Run {run_id} created in planning status"
    }
    if summary:
        result["summary"] = summary
    return result


def main():
    parser = argparse.ArgumentParser(description="Create a new run")
    parser.add_argument("--mode", "-m", required=True, choices=VALID_MODES, help="Run mode")
    parser.add_argument("--max-iterations", "-i", type=int, default=10, help="Max iterations (default: 10)")
    parser.add_argument("--summary", "-s", help="Overall context about what this run is building")
    args = parser.parse_args()

    result = create_run(mode=args.mode, max_iterations=args.max_iterations, summary=args.summary)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
