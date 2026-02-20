"""SQLite database with sqlite-vec and FTS5 for memory storage."""

import sqlite3
import struct
from pathlib import Path
from typing import Optional

import sqlite_vec

from .config import DB_PATH, EMBEDDING_DIMS


def _serialize_embedding(embedding: list[float]) -> bytes:
    """Convert float list to bytes for sqlite-vec."""
    return struct.pack(f"{len(embedding)}f", *embedding)


def _deserialize_embedding(blob: bytes) -> list[float]:
    """Convert bytes back to float list."""
    n = len(blob) // 4
    return list(struct.unpack(f"{n}f", blob))


class MemoryDB:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.enable_load_extension(True)
        sqlite_vec.load(self.conn)
        self.conn.enable_load_extension(False)
        self._init_schema()

    def _init_schema(self):
        self.conn.executescript(f"""
            CREATE TABLE IF NOT EXISTS files (
                file_id INTEGER PRIMARY KEY,
                file_path TEXT UNIQUE NOT NULL,
                content_hash TEXT NOT NULL,
                last_indexed TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS chunks (
                chunk_id INTEGER PRIMARY KEY,
                file_id INTEGER NOT NULL REFERENCES files(file_id) ON DELETE CASCADE,
                chunk_index INTEGER NOT NULL,
                start_line INTEGER NOT NULL,
                end_line INTEGER NOT NULL,
                content TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                UNIQUE(file_id, chunk_index)
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                content,
                content='chunks',
                content_rowid='chunk_id'
            );

            -- FTS sync triggers
            CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
                INSERT INTO chunks_fts(rowid, content) VALUES (new.chunk_id, new.content);
            END;
            CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
                INSERT INTO chunks_fts(chunks_fts, rowid, content) VALUES ('delete', old.chunk_id, old.content);
            END;
            CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN
                INSERT INTO chunks_fts(chunks_fts, rowid, content) VALUES ('delete', old.chunk_id, old.content);
                INSERT INTO chunks_fts(rowid, content) VALUES (new.chunk_id, new.content);
            END;

            CREATE VIRTUAL TABLE IF NOT EXISTS vec_chunks USING vec0(
                chunk_id INTEGER PRIMARY KEY,
                embedding float[{EMBEDDING_DIMS}] distance_metric=cosine
            );

            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT
            );
        """)
        self.conn.commit()

    def get_file(self, file_path: str) -> Optional[dict]:
        row = self.conn.execute(
            "SELECT * FROM files WHERE file_path = ?", (file_path,)
        ).fetchone()
        return dict(row) if row else None

    def upsert_file(self, file_path: str, content_hash: str, timestamp: str) -> int:
        """Insert or update file record. Returns file_id."""
        existing = self.get_file(file_path)
        if existing:
            self.conn.execute(
                "UPDATE files SET content_hash=?, last_indexed=? WHERE file_id=?",
                (content_hash, timestamp, existing["file_id"]),
            )
            return existing["file_id"]
        else:
            cur = self.conn.execute(
                "INSERT INTO files (file_path, content_hash, last_indexed) VALUES (?,?,?)",
                (file_path, content_hash, timestamp),
            )
            return cur.lastrowid

    def clear_chunks(self, file_id: int):
        """Remove all chunks (and vec/fts entries via triggers/cascade) for a file."""
        # Get chunk IDs first for vec cleanup
        chunk_ids = [
            r["chunk_id"]
            for r in self.conn.execute(
                "SELECT chunk_id FROM chunks WHERE file_id=?", (file_id,)
            ).fetchall()
        ]
        if chunk_ids:
            placeholders = ",".join("?" * len(chunk_ids))
            self.conn.execute(
                f"DELETE FROM vec_chunks WHERE chunk_id IN ({placeholders})", chunk_ids
            )
        self.conn.execute("DELETE FROM chunks WHERE file_id=?", (file_id,))

    def insert_chunk(
        self,
        file_id: int,
        chunk_index: int,
        start_line: int,
        end_line: int,
        content: str,
        content_hash: str,
        embedding: list[float],
    ) -> int:
        """Insert a chunk with its embedding. Returns chunk_id."""
        cur = self.conn.execute(
            """INSERT INTO chunks (file_id, chunk_index, start_line, end_line, content, content_hash)
               VALUES (?,?,?,?,?,?)""",
            (file_id, chunk_index, start_line, end_line, content, content_hash),
        )
        chunk_id = cur.lastrowid
        self.conn.execute(
            "INSERT INTO vec_chunks (chunk_id, embedding) VALUES (?,?)",
            (chunk_id, _serialize_embedding(embedding)),
        )
        return chunk_id

    def vector_search(self, query_embedding: list[float], limit: int) -> list[dict]:
        """Search by vector similarity. Returns chunk_id + distance."""
        rows = self.conn.execute(
            """SELECT chunk_id, distance
               FROM vec_chunks
               WHERE embedding MATCH ?
               ORDER BY distance
               LIMIT ?""",
            (_serialize_embedding(query_embedding), limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def bm25_search(self, query: str, limit: int) -> list[dict]:
        """Search by BM25 keyword match. Returns chunk_id + rank."""
        rows = self.conn.execute(
            """SELECT rowid as chunk_id, rank
               FROM chunks_fts
               WHERE chunks_fts MATCH ?
               ORDER BY rank
               LIMIT ?""",
            (query, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_chunk(self, chunk_id: int) -> Optional[dict]:
        row = self.conn.execute(
            """SELECT c.*, f.file_path
               FROM chunks c JOIN files f ON c.file_id = f.file_id
               WHERE c.chunk_id = ?""",
            (chunk_id,),
        ).fetchone()
        return dict(row) if row else None

    def get_chunks_by_ids(self, chunk_ids: list[int]) -> dict[int, dict]:
        if not chunk_ids:
            return {}
        placeholders = ",".join("?" * len(chunk_ids))
        rows = self.conn.execute(
            f"""SELECT c.*, f.file_path
                FROM chunks c JOIN files f ON c.file_id = f.file_id
                WHERE c.chunk_id IN ({placeholders})""",
            chunk_ids,
        ).fetchall()
        return {r["chunk_id"]: dict(r) for r in rows}

    def stats(self) -> dict:
        file_count = self.conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        chunk_count = self.conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        last_indexed = self.conn.execute(
            "SELECT MAX(last_indexed) FROM files"
        ).fetchone()[0]
        db_size = self.db_path.stat().st_size if self.db_path.exists() else 0
        return {
            "file_count": file_count,
            "chunk_count": chunk_count,
            "last_indexed": last_indexed,
            "db_size_bytes": db_size,
            "db_path": str(self.db_path),
        }

    def remove_stale_files(self, current_paths: set[str]) -> int:
        """Remove files from DB that no longer exist on disk. Returns count removed."""
        db_paths = {
            r["file_path"]
            for r in self.conn.execute("SELECT file_path FROM files").fetchall()
        }
        stale = db_paths - current_paths
        removed = 0
        for path in stale:
            f = self.get_file(path)
            if f:
                self.clear_chunks(f["file_id"])
                self.conn.execute("DELETE FROM files WHERE file_id=?", (f["file_id"],))
                removed += 1
        return removed

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()
