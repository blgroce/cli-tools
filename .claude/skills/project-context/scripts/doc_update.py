#!/usr/bin/env python3
"""Update a documentation record in the project database."""

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


def update_doc(doc_id, path=None, title=None, summary=None, category=None, tags=None):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Check if doc exists
    cursor.execute("SELECT * FROM documentation WHERE id = ?", (doc_id,))
    if cursor.fetchone() is None:
        conn.close()
        return {"error": f"Documentation {doc_id} not found"}

    # Build dynamic update query
    updates = []
    values = []

    if path is not None:
        updates.append("path = ?")
        values.append(path)
    if title is not None:
        updates.append("title = ?")
        values.append(title)
    if summary is not None:
        updates.append("summary = ?")
        values.append(summary)
    if category is not None:
        updates.append("category = ?")
        values.append(category)
    if tags is not None:
        updates.append("tags = ?")
        # Parse tags if provided as string
        try:
            if isinstance(tags, str):
                tags_json = tags if tags.startswith("[") else json.dumps([tags])
            else:
                tags_json = json.dumps(tags)
        except json.JSONDecodeError:
            tags_json = json.dumps([tags])
        values.append(tags_json)

    if not updates:
        conn.close()
        return {"error": "No fields to update"}

    values.append(doc_id)
    query = f"UPDATE documentation SET {', '.join(updates)} WHERE id = ?"
    cursor.execute(query, values)
    conn.commit()

    # Fetch updated record
    cursor.execute("SELECT * FROM documentation WHERE id = ?", (doc_id,))
    row = cursor.fetchone()
    conn.close()

    doc = dict(row)
    doc["tags"] = parse_json_field(doc.get("tags"))

    return {"success": True, "doc": doc, "message": f"Documentation {doc_id} updated"}


def main():
    parser = argparse.ArgumentParser(description="Update a documentation record")
    parser.add_argument("doc_id", type=int, help="Documentation ID")
    parser.add_argument("--path", "-p", help="New path to the markdown file")
    parser.add_argument("--title", "-t", help="New document title")
    parser.add_argument("--summary", "-s", help="New summary")
    parser.add_argument("--category", "-c", help="New category")
    parser.add_argument("--tags", help="New tags as JSON array")
    args = parser.parse_args()

    result = update_doc(
        doc_id=args.doc_id,
        path=args.path,
        title=args.title,
        summary=args.summary,
        category=args.category,
        tags=args.tags
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
