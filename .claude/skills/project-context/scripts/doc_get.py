#!/usr/bin/env python3
"""Get a specific documentation record from the project database."""

import argparse
import json
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(".cadi/cadi-project.sqlite")
DOC_DIR = Path(".cadi/documentation")


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


def get_doc(doc_id, include_content=False):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM documentation WHERE id = ?", (doc_id,))
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return {"error": f"Documentation {doc_id} not found"}

    doc = dict(row)
    doc["tags"] = parse_json_field(doc.get("tags"))

    # Optionally include the file content
    if include_content:
        doc_path = DOC_DIR / doc["path"]
        if doc_path.exists():
            doc["content"] = doc_path.read_text()
        else:
            doc["content"] = None
            doc["content_error"] = f"File not found: {doc_path}"

    return doc


def main():
    parser = argparse.ArgumentParser(description="Get a documentation record")
    parser.add_argument("doc_id", type=int, help="Documentation ID")
    parser.add_argument("--content", "-C", action="store_true", help="Include file content in response")
    args = parser.parse_args()

    result = get_doc(args.doc_id, include_content=args.content)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
