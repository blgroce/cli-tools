"""Dataclasses for CRM entities."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional

import sqlite3


@dataclass
class Company:
    id: int
    name: str
    industry: Optional[str] = None
    status: Optional[str] = None
    website: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> Company:
        return cls(**{k: row[k] for k in row.keys()})

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Contact:
    id: int
    name: str
    company_id: Optional[int] = None
    role: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    tags: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> Contact:
        return cls(**{k: row[k] for k in row.keys()})

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Interaction:
    id: int
    contact_id: int
    company_id: Optional[int] = None
    type: Optional[str] = None
    summary: Optional[str] = None
    occurred_at: Optional[str] = None
    followup_date: Optional[str] = None
    followup_note: Optional[str] = None
    created_at: Optional[str] = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> Interaction:
        return cls(**{k: row[k] for k in row.keys()})

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Deal:
    id: int
    title: str
    company_id: int
    contact_id: Optional[int] = None
    value: Optional[float] = None
    stage: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> Deal:
        return cls(**{k: row[k] for k in row.keys()})

    def to_dict(self) -> dict:
        return asdict(self)
