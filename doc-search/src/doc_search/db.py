"""SQLite database with FTS5 for document storage and search."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

from .config import DB_PATH

SCHEMA_VERSION = 1


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(conn: Optional[sqlite3.Connection] = None) -> sqlite3.Connection:
    if conn is None:
        conn = get_connection()

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS documents (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT NOT NULL,
            source_path     TEXT,
            extracted_text  TEXT NOT NULL,
            page_count      INTEGER NOT NULL DEFAULT 0,
            char_count      INTEGER NOT NULL DEFAULT 0,
            tags            TEXT DEFAULT '',
            metadata        TEXT DEFAULT '{}',
            created_at      DATETIME DEFAULT (datetime('now'))
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
            name,
            extracted_text,
            tags,
            content='documents',
            content_rowid='id'
        );

        -- FTS sync triggers
        CREATE TRIGGER IF NOT EXISTS documents_ai AFTER INSERT ON documents BEGIN
            INSERT INTO documents_fts(rowid, name, extracted_text, tags)
            VALUES (new.id, new.name, new.extracted_text, new.tags);
        END;

        CREATE TRIGGER IF NOT EXISTS documents_ad AFTER DELETE ON documents BEGIN
            INSERT INTO documents_fts(documents_fts, rowid, name, extracted_text, tags)
            VALUES ('delete', old.id, old.name, old.extracted_text, old.tags);
        END;

        CREATE TRIGGER IF NOT EXISTS documents_au AFTER UPDATE ON documents BEGIN
            INSERT INTO documents_fts(documents_fts, rowid, name, extracted_text, tags)
            VALUES ('delete', old.id, old.name, old.extracted_text, old.tags);
            INSERT INTO documents_fts(rowid, name, extracted_text, tags)
            VALUES (new.id, new.name, new.extracted_text, new.tags);
        END;
    """)

    row = conn.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
    if row is None:
        conn.execute("INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,))
        conn.commit()

    return conn


def insert_document(
    conn: sqlite3.Connection,
    name: str,
    source_path: str,
    extracted_text: str,
    page_count: int,
    char_count: int,
    tags: str = "",
    metadata: str = "{}",
) -> int:
    cur = conn.execute(
        """INSERT INTO documents (name, source_path, extracted_text, page_count, char_count, tags, metadata)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (name, source_path, extracted_text, page_count, char_count, tags, metadata),
    )
    conn.commit()
    return cur.lastrowid


def get_document(conn: sqlite3.Connection, doc_id: int) -> Optional[dict]:
    row = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
    return dict(row) if row else None


def get_latest_document(conn: sqlite3.Connection) -> Optional[dict]:
    row = conn.execute("SELECT * FROM documents ORDER BY id DESC LIMIT 1").fetchone()
    return dict(row) if row else None


def list_documents(conn: sqlite3.Connection, tag: Optional[str] = None) -> list[dict]:
    if tag:
        rows = conn.execute(
            "SELECT id, name, source_path, page_count, char_count, tags, created_at FROM documents WHERE tags LIKE ? ORDER BY id DESC",
            (f"%{tag}%",),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, name, source_path, page_count, char_count, tags, created_at FROM documents ORDER BY id DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def search_documents(conn: sqlite3.Connection, query: str, limit: int = 10) -> list[dict]:
    rows = conn.execute(
        """SELECT d.id, d.name, d.tags, d.created_at,
                  snippet(documents_fts, 1, '>>>', '<<<', '...', 40) as snippet
           FROM documents_fts
           JOIN documents d ON d.id = documents_fts.rowid
           WHERE documents_fts MATCH ?
           ORDER BY rank
           LIMIT ?""",
        (query, limit),
    ).fetchall()
    return [dict(r) for r in rows]


def delete_document(conn: sqlite3.Connection, doc_id: int) -> bool:
    cur = conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
    conn.commit()
    return cur.rowcount > 0
