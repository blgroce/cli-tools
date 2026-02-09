#!/usr/bin/env python3
"""List documentation from the project database."""

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
    """Parse a JSON field, returning the value or an empty list if invalid."""
    if value is None:
        return []
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return []


def list_docs(category=None):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if category:
        cursor.execute(
            "SELECT * FROM documentation WHERE category = ? ORDER BY id DESC",
            (category,)
        )
    else:
        cursor.execute("SELECT * FROM documentation ORDER BY id DESC")

    docs = []
    for row in cursor.fetchall():
        doc = dict(row)
        doc["tags"] = parse_json_field(doc.get("tags"))
        docs.append(doc)

    conn.close()

    return {"docs": docs, "count": len(docs)}


def main():
    parser = argparse.ArgumentParser(description="List project documentation")
    parser.add_argument("--category", "-c", help="Filter by category")
    args = parser.parse_args()

    result = list_docs(category=args.category)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
