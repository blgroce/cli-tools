#!/usr/bin/env python3
"""Search documentation by summary, title, category, or tags."""

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


def search_docs(query=None, category=None, tag=None):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    conditions = []
    values = []

    if query:
        # Search in title and summary using LIKE
        conditions.append("(title LIKE ? OR summary LIKE ?)")
        values.extend([f"%{query}%", f"%{query}%"])

    if category:
        conditions.append("category = ?")
        values.append(category)

    if tag:
        # Search in JSON tags array
        conditions.append("tags LIKE ?")
        values.append(f"%{tag}%")

    if conditions:
        where_clause = " AND ".join(conditions)
        sql = f"SELECT * FROM documentation WHERE {where_clause} ORDER BY id DESC"
        cursor.execute(sql, values)
    else:
        cursor.execute("SELECT * FROM documentation ORDER BY id DESC")

    docs = []
    for row in cursor.fetchall():
        doc = dict(row)
        doc["tags"] = parse_json_field(doc.get("tags"))
        docs.append(doc)

    conn.close()

    return {"docs": docs, "count": len(docs), "query": query, "category": category, "tag": tag}


def main():
    parser = argparse.ArgumentParser(description="Search project documentation")
    parser.add_argument("--query", "-q", help="Search term for title and summary")
    parser.add_argument("--category", "-c", help="Filter by category")
    parser.add_argument("--tag", "-t", help="Filter by tag")
    args = parser.parse_args()

    if not args.query and not args.category and not args.tag:
        print(json.dumps({"error": "At least one search parameter required (--query, --category, or --tag)"}))
        sys.exit(1)

    result = search_docs(query=args.query, category=args.category, tag=args.tag)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
