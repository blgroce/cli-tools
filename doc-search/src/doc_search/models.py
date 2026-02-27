"""Data models for doc-search."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Document:
    id: int
    name: str
    source_path: str
    extracted_text: str
    page_count: int
    char_count: int
    tags: str
    metadata: str
    created_at: str
    quality_warning: Optional[str] = None

    @staticmethod
    def from_row(row) -> Document:
        return Document(
            id=row["id"],
            name=row["name"],
            source_path=row["source_path"],
            extracted_text=row["extracted_text"],
            page_count=row["page_count"],
            char_count=row["char_count"],
            tags=row["tags"] or "",
            metadata=row["metadata"] or "{}",
            created_at=row["created_at"],
        )
