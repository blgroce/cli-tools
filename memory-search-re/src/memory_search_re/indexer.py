"""File discovery, chunking, and indexing."""

import hashlib
from datetime import datetime, timezone
from pathlib import Path

from .config import (
    VAULT_ROOT,
    INDEX_PATHS,
    EXCLUDE_DIRS,
    SKILL_REFS,
    CHUNK_TARGET_CHARS,
    CHUNK_OVERLAP_CHARS,
)
from .db import MemoryDB
from .embeddings import embed_texts, get_api_key


def discover_files() -> list[Path]:
    """Find all markdown files to index."""
    files = []
    for base_path in INDEX_PATHS:
        if not base_path.exists():
            continue
        for md_file in base_path.rglob("*.md"):
            # Check if any parent directory is in the exclude list
            skip = False
            for part in md_file.relative_to(VAULT_ROOT).parts:
                if part in EXCLUDE_DIRS:
                    skip = True
                    break
            if not skip:
                files.append(md_file)

    # Also index skill references
    if SKILL_REFS.exists():
        for md_file in SKILL_REFS.rglob("references/*.md"):
            files.append(md_file)

    return sorted(files)


def file_hash(path: Path) -> str:
    """SHA-256 hash of file contents."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def chunk_text(text: str) -> list[dict]:
    """Split text into overlapping chunks.

    Returns list of {text, start_line, end_line}.
    Splits on paragraph boundaries (double newlines) and heading boundaries.
    """
    lines = text.split("\n")
    if not lines:
        return []

    # Build paragraphs with line tracking
    paragraphs = []
    current_lines = []
    current_start = 1  # 1-indexed

    for i, line in enumerate(lines, 1):
        # Split on headings or double blank lines
        is_heading = line.startswith("#") and len(current_lines) > 0
        is_blank = line.strip() == "" and current_lines and current_lines[-1].strip() == ""

        if is_heading and current_lines:
            # Flush current paragraph before heading
            paragraphs.append({
                "text": "\n".join(current_lines).strip(),
                "start": current_start,
                "end": i - 1,
            })
            current_lines = [line]
            current_start = i
        elif is_blank and current_lines:
            paragraphs.append({
                "text": "\n".join(current_lines).strip(),
                "start": current_start,
                "end": i - 1,
            })
            current_lines = []
            current_start = i + 1
        else:
            if not current_lines and line.strip() == "":
                current_start = i + 1
                continue
            current_lines.append(line)

    # Flush remaining
    if current_lines:
        text_content = "\n".join(current_lines).strip()
        if text_content:
            paragraphs.append({
                "text": text_content,
                "start": current_start,
                "end": len(lines),
            })

    # Merge paragraphs into chunks of target size
    chunks = []
    current_chunk_text = ""
    current_chunk_start = None
    current_chunk_end = None

    for para in paragraphs:
        if not para["text"]:
            continue

        if current_chunk_text and len(current_chunk_text) + len(para["text"]) + 2 > CHUNK_TARGET_CHARS:
            # Current chunk is full, save it
            chunks.append({
                "text": current_chunk_text,
                "start_line": current_chunk_start,
                "end_line": current_chunk_end,
            })

            # Start new chunk with overlap from end of previous
            overlap_text = current_chunk_text[-CHUNK_OVERLAP_CHARS:] if len(current_chunk_text) > CHUNK_OVERLAP_CHARS else ""
            if overlap_text:
                current_chunk_text = overlap_text + "\n\n" + para["text"]
            else:
                current_chunk_text = para["text"]
            current_chunk_start = para["start"]
            current_chunk_end = para["end"]
        else:
            if current_chunk_text:
                current_chunk_text += "\n\n" + para["text"]
            else:
                current_chunk_text = para["text"]

            if current_chunk_start is None:
                current_chunk_start = para["start"]
            current_chunk_end = para["end"]

    # Flush last chunk
    if current_chunk_text:
        chunks.append({
            "text": current_chunk_text,
            "start_line": current_chunk_start or 1,
            "end_line": current_chunk_end or 1,
        })

    return chunks


def index_files(db: MemoryDB, verbose: bool = False) -> dict:
    """Index all markdown files. Returns stats."""
    api_key = get_api_key()
    files = discover_files()
    current_paths = {str(f) for f in files}
    now = datetime.now(timezone.utc).isoformat()

    stats = {
        "files_scanned": len(files),
        "files_indexed": 0,
        "files_skipped": 0,
        "files_removed": 0,
        "chunks_created": 0,
    }

    # Remove files that no longer exist
    stats["files_removed"] = db.remove_stale_files(current_paths)

    # Collect files that need indexing
    to_index = []
    for path in files:
        path_str = str(path)
        current_hash = file_hash(path)
        existing = db.get_file(path_str)

        if existing and existing["content_hash"] == current_hash:
            stats["files_skipped"] += 1
            continue

        to_index.append((path, path_str, current_hash))

    if not to_index:
        if verbose:
            print(f"All {len(files)} files up to date, nothing to index.")
        db.commit()
        return stats

    # Chunk all files first, then batch embed
    all_chunks = []  # (file_idx, chunk_data)
    file_infos = []  # (path, path_str, current_hash, chunk_list)

    for path, path_str, current_hash in to_index:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            if verbose:
                print(f"  Skip {path.name}: {e}")
            continue

        chunks = chunk_text(text)
        if not chunks:
            continue

        file_idx = len(file_infos)
        file_infos.append((path, path_str, current_hash, chunks))
        for chunk in chunks:
            all_chunks.append((file_idx, chunk))

    if not all_chunks:
        db.commit()
        return stats

    # Batch embed all chunks
    if verbose:
        print(f"Embedding {len(all_chunks)} chunks from {len(file_infos)} files...")

    chunk_texts = [c[1]["text"] for c in all_chunks]
    embeddings = embed_texts(chunk_texts, api_key=api_key)

    # Store everything
    embed_idx = 0
    for file_idx, (path, path_str, current_hash, chunks) in enumerate(file_infos):
        file_id = db.upsert_file(path_str, current_hash, now)
        db.clear_chunks(file_id)

        for chunk_index, chunk in enumerate(chunks):
            chunk_hash = hashlib.sha256(chunk["text"].encode()).hexdigest()
            db.insert_chunk(
                file_id=file_id,
                chunk_index=chunk_index,
                start_line=chunk["start_line"],
                end_line=chunk["end_line"],
                content=chunk["text"],
                content_hash=chunk_hash,
                embedding=embeddings[embed_idx],
            )
            embed_idx += 1
            stats["chunks_created"] += 1

        stats["files_indexed"] += 1
        if verbose:
            print(f"  Indexed {path.name}: {len(chunks)} chunks")

    db.commit()
    return stats
