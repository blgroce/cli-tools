"""Real Estate memory-search-re CLI — index, search, store, status."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from enum import IntEnum
from pathlib import Path
from typing import Optional

import typer

from . import __version__
from .config import (
    DB_PATH,
    MEMORY_DIR,
    NOTES_FILE,
    DEFAULT_MAX_RESULTS,
    DEFAULT_MIN_SCORE,
)

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Semantic memory search for Real Estate assistant.",
)


class ExitCode(IntEnum):
    SUCCESS = 0
    GENERAL_ERROR = 1
    INVALID_ARGS = 2
    NOT_FOUND = 3
    EXTERNAL_FAILURE = 4


def _version_callback(value: bool) -> None:
    if value:
        print(f"memory-search-re {__version__}")
        raise typer.Exit(0)


@app.callback()
def main(
    ctx: typer.Context,
    fmt: str = typer.Option("json", "--format", help="Output format: json or text"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress non-error output"),
    version: bool = typer.Option(
        False, "--version", help="Show version and exit",
        is_eager=True, callback=_version_callback,
    ),
) -> None:
    ctx.obj = {"format": fmt, "quiet": quiet}


class _Done(Exception):
    """Signal successful completion — avoids typer.Exit being caught by except blocks."""
    pass


def _emit(data: dict, ctx: typer.Context, text: Optional[str] = None):
    obj = ctx.obj or {}
    if obj.get("quiet"):
        return
    if obj.get("format") == "text":
        print(text or "")
    else:
        print(json.dumps({"success": True, "data": data}))


def _emit_error(message: str, code: str = "ERROR", exit_code: int = 1):
    print(json.dumps({"error": True, "code": code, "message": message}), file=sys.stderr)
    raise typer.Exit(exit_code)


@app.command()
def index(
    ctx: typer.Context,
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show per-file progress"),
) -> None:
    """Index markdown files from the vault into the memory database."""
    from .db import MemoryDB
    from .indexer import index_files

    try:
        db = MemoryDB()
        stats = index_files(db, verbose=verbose)
        db.close()

        text_lines = [
            f"Files scanned: {stats['files_scanned']}",
            f"Files indexed: {stats['files_indexed']}",
            f"Files skipped (unchanged): {stats['files_skipped']}",
            f"Files removed (stale): {stats['files_removed']}",
            f"Chunks created: {stats['chunks_created']}",
        ]
        _emit(stats, ctx, text="\n".join(text_lines))
    except Exception as e:
        _emit_error(str(e), code="INDEX_ERROR", exit_code=ExitCode.EXTERNAL_FAILURE)


@app.command()
def search(
    ctx: typer.Context,
    query: str = typer.Argument(..., help="Search query"),
    limit: int = typer.Option(DEFAULT_MAX_RESULTS, "--limit", "-n", help="Max results"),
    min_score: float = typer.Option(DEFAULT_MIN_SCORE, "--min-score", help="Min score threshold"),
) -> None:
    """Search memory using hybrid vector + keyword matching."""
    from .db import MemoryDB
    from .search import hybrid_search

    try:
        db = MemoryDB()
        results = hybrid_search(db, query, limit=limit, min_score=min_score)
        db.close()

        if not results:
            text = "No results found."
        else:
            text_lines = []
            for i, r in enumerate(results, 1):
                path = r["file_path"]
                # Make path relative to vault if possible
                try:
                    from .config import VAULT_ROOT
                    rel = str(Path(path).relative_to(VAULT_ROOT))
                except ValueError:
                    rel = path
                text_lines.append(
                    f"--- Result {i} (score: {r['score']}) ---\n"
                    f"File: {rel}:{r['start_line']}-{r['end_line']}\n"
                    f"{r['snippet']}\n"
                )
            text = "\n".join(text_lines)

        _emit({"results": results, "count": len(results)}, ctx, text=text)
    except Exception as e:
        _emit_error(str(e), code="SEARCH_ERROR", exit_code=ExitCode.EXTERNAL_FAILURE)


@app.command()
def store(
    ctx: typer.Context,
    text: str = typer.Argument(..., help="Text to store in memory"),
    file: str = typer.Option("daily", "--file", "-f", help="Target: 'daily' or 'notes'"),
) -> None:
    """Store text to a memory file and re-index it."""
    from .db import MemoryDB
    from .indexer import index_files

    now = datetime.now()

    if file == "daily":
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        target = MEMORY_DIR / f"{now.strftime('%Y-%m-%d')}.md"
        if not target.exists():
            target.write_text(f"# Memory — {now.strftime('%Y-%m-%d')}\n\n", encoding="utf-8")
    elif file == "notes":
        target = NOTES_FILE
    else:
        _emit_error(f"Unknown file target: {file}. Use 'daily' or 'notes'.", code="INVALID_ARGS", exit_code=ExitCode.INVALID_ARGS)
        return  # unreachable but keeps type checker happy

    # Append
    timestamp = now.strftime("%H:%M")
    entry = f"\n- [{timestamp}] {text}\n"
    with open(target, "a", encoding="utf-8") as f:
        f.write(entry)

    # Re-index just this file (full index will catch it, but let's be immediate)
    try:
        db = MemoryDB()
        # We run full index but hash-based dedup means only changed files get re-embedded
        stats = index_files(db, verbose=False)
        db.close()
    except Exception:
        pass  # Non-critical — next periodic index will catch it

    rel_path = str(target)
    try:
        from .config import VAULT_ROOT
        rel_path = str(target.relative_to(VAULT_ROOT))
    except ValueError:
        pass

    _emit(
        {"stored": True, "file": rel_path, "text": text},
        ctx,
        text=f"Stored to {rel_path}",
    )


@app.command()
def status(ctx: typer.Context) -> None:
    """Show memory database statistics."""
    from .db import MemoryDB

    try:
        db = MemoryDB()
        s = db.stats()
        db.close()

        db_size_mb = round(s["db_size_bytes"] / (1024 * 1024), 2)
        text = (
            f"Files indexed: {s['file_count']}\n"
            f"Total chunks: {s['chunk_count']}\n"
            f"Last indexed: {s['last_indexed'] or 'never'}\n"
            f"Database size: {db_size_mb} MB\n"
            f"Database path: {s['db_path']}"
        )
        _emit(s, ctx, text=text)
    except Exception as e:
        _emit_error(str(e), code="STATUS_ERROR")


if __name__ == "__main__":
    app()
