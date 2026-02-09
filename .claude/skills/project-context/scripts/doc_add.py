#!/usr/bin/env python3
"""Add a new documentation reference to the project database."""

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


def add_doc(path, title, summary, category=None, tags=None):
    # Validate that the document file exists
    doc_path = DOC_DIR / path if not path.startswith(".cadi/documentation/") else Path(path)
    if not doc_path.exists():
        return {"error": f"Documentation file not found: {doc_path}"}

    # Normalize path to be relative to .cadi/documentation/
    if path.startswith(".cadi/documentation/"):
        path = path.replace(".cadi/documentation/", "")

    conn = get_connection()
    cursor = conn.cursor()

    # Parse tags if provided as JSON string
    tags_json = None
    if tags:
        try:
            if isinstance(tags, str):
                tags_json = tags if tags.startswith("[") else json.dumps([tags])
            else:
                tags_json = json.dumps(tags)
        except json.JSONDecodeError:
            tags_json = json.dumps([tags])

    cursor.execute(
        """
        INSERT INTO documentation (path, title, summary, category, tags)
        VALUES (?, ?, ?, ?, ?)
        """,
        (path, title, summary, category, tags_json)
    )

    doc_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {
        "success": True,
        "doc_id": doc_id,
        "message": f"Documentation {doc_id} created successfully"
    }


def main():
    parser = argparse.ArgumentParser(description="Add a new documentation reference")
    parser.add_argument("--path", "-p", required=True, help="Path to the markdown file (relative to .cadi/documentation/)")
    parser.add_argument("--title", "-t", required=True, help="Document title")
    parser.add_argument("--summary", "-s", required=True, help="Short descriptive summary")
    parser.add_argument("--category", "-c", help="Document category (e.g., architecture, api, guides)")
    parser.add_argument("--tags", help="Tags as JSON array or comma-separated string")
    args = parser.parse_args()

    result = add_doc(
        path=args.path,
        title=args.title,
        summary=args.summary,
        category=args.category,
        tags=args.tags
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
