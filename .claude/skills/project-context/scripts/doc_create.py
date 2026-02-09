#!/usr/bin/env python3
"""Create a new documentation file from template and register in database."""

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from datetime import date

DB_PATH = Path(".cadi/cadi-project.sqlite")
DOC_DIR = Path(".cadi/documentation")

VALID_CATEGORIES = ["auth", "api", "ui", "data", "infra", "flow"]

TEMPLATE = """# {title}

> {summary}

## Location

| Type | Path |
|------|------|
| {location_type} | `{location_path}` |

## How It Works

{how_it_works}

## Usage

```{code_lang}
{usage_example}
```

## Related Docs

{related_docs}

---
*Created: {date} | Task: #{task_id}*
"""


def get_connection():
    if not DB_PATH.exists():
        print(json.dumps({"error": f"Database not found at {DB_PATH}"}))
        sys.exit(1)
    return sqlite3.connect(DB_PATH)


def find_related_docs(category, exclude_name):
    """Find existing docs in the same category to auto-link."""
    related = []
    if not DOC_DIR.exists():
        return related

    for doc_file in DOC_DIR.glob(f"{category}-*.md"):
        doc_name = doc_file.stem  # e.g., "infra-loop-script"
        if doc_name != f"{category}-{exclude_name}":
            # Extract title from first line of file
            try:
                first_line = doc_file.read_text().split('\n')[0]
                doc_title = first_line.replace('# ', '').strip()
                related.append(f"- [{doc_title}](./{doc_name}.md)")
            except:
                related.append(f"- [{doc_name}](./{doc_name}.md)")

    return related


def create_doc(category, name, title, summary, location_type, location_path,
               how_it_works, usage_example, task_id, code_lang="typescript",
               related_docs=None, tags=None):

    if category not in VALID_CATEGORIES:
        return {"error": f"Invalid category. Valid: {VALID_CATEGORIES}"}

    # Create filename
    filename = f"{category}-{name}.md"
    filepath = DOC_DIR / filename

    # Ensure directory exists
    DOC_DIR.mkdir(parents=True, exist_ok=True)

    # Auto-find related docs if not provided
    if related_docs is None:
        found_related = find_related_docs(category, name)
        related_docs = "\n".join(found_related) if found_related else "- None yet"

    # Generate content
    content = TEMPLATE.format(
        title=title,
        summary=summary,
        location_type=location_type,
        location_path=location_path,
        how_it_works=how_it_works,
        usage_example=usage_example,
        code_lang=code_lang,
        related_docs=related_docs,
        date=date.today().isoformat(),
        task_id=task_id
    )

    # Write file
    filepath.write_text(content)

    # Register in database
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO documentation (path, title, summary, category, tags)
        VALUES (?, ?, ?, ?, ?)
        """,
        (str(filepath), title, summary, category, json.dumps(tags or []))
    )

    doc_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {
        "success": True,
        "doc_id": doc_id,
        "path": str(filepath),
        "message": f"Created {filename} and registered as doc #{doc_id}"
    }


def main():
    parser = argparse.ArgumentParser(description="Create documentation from template")
    parser.add_argument("--category", "-c", required=True, choices=VALID_CATEGORIES)
    parser.add_argument("--name", "-n", required=True, help="Short name (kebab-case)")
    parser.add_argument("--title", "-t", required=True, help="Document title")
    parser.add_argument("--summary", "-s", required=True, help="One-line summary")
    parser.add_argument("--location-type", required=True, help="e.g., Component, API, Service")
    parser.add_argument("--location-path", required=True, help="File path")
    parser.add_argument("--how", required=True, help="Bullet points (use \\n for newlines)")
    parser.add_argument("--usage", required=True, help="Code example")
    parser.add_argument("--task-id", required=True, type=int, help="Task ID that created this")
    parser.add_argument("--lang", default="typescript", help="Code language (default: typescript)")
    parser.add_argument("--related", default=None, help="Related docs links (auto-detected if omitted)")
    parser.add_argument("--tags", help="JSON array of tags")
    args = parser.parse_args()

    tags = json.loads(args.tags) if args.tags else None

    result = create_doc(
        category=args.category,
        name=args.name,
        title=args.title,
        summary=args.summary,
        location_type=args.location_type,
        location_path=args.location_path,
        how_it_works=args.how.replace("\\n", "\n"),
        usage_example=args.usage,
        task_id=args.task_id,
        code_lang=args.lang,
        related_docs=args.related.replace("\\n", "\n") if args.related else None,
        tags=tags
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
