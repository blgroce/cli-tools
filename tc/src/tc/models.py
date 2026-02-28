"""Dataclasses for TC entities."""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict, fields
from typing import Optional
import sqlite3

_BOOL_FIELDS_TXN = frozenset({
    "is_financed", "has_hoa", "has_mud", "is_pre_1978",
    "is_seller_disclosure_exempt", "is_cash_offer",
    "is_new_construction", "has_existing_survey",
})


@dataclass
class Transaction:
    id: int
    address: Optional[str] = None
    city: Optional[str] = None
    county: Optional[str] = None
    zip: Optional[str] = None
    status: str = "draft"
    type: Optional[str] = None
    effective_date: Optional[str] = None
    closing_date: Optional[str] = None
    option_period_days: Optional[int] = None
    option_period_end: Optional[str] = None
    sales_price: Optional[float] = None
    earnest_money: Optional[float] = None
    option_fee: Optional[float] = None
    is_financed: bool = True
    financing_amount: Optional[float] = None
    has_hoa: bool = False
    has_mud: bool = False
    is_pre_1978: bool = False
    is_seller_disclosure_exempt: bool = False
    is_cash_offer: bool = False
    is_new_construction: bool = False
    has_existing_survey: Optional[bool] = None
    notes: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> Transaction:
        valid = {f.name for f in fields(cls)}
        data = {k: row[k] for k in row.keys() if k in valid}
        for bf in _BOOL_FIELDS_TXN:
            if bf in data and data[bf] is not None:
                data[bf] = bool(data[bf])
        return cls(**data)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Person:
    id: int
    transaction_id: int
    role: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> Person:
        valid = {f.name for f in fields(cls)}
        return cls(**{k: row[k] for k in row.keys() if k in valid})

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Task:
    id: int
    transaction_id: int
    title: str
    template_id: Optional[str] = None
    description: Optional[str] = None
    phase: Optional[str] = None
    group_id: Optional[str] = None
    due_date: Optional[str] = None
    status: str = "pending"
    completed_at: Optional[str] = None
    sort_order: int = 0
    depends_on: Optional[str] = None
    is_conditional: bool = False
    condition_met: bool = True
    skip_reason: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> Task:
        valid = {f.name for f in fields(cls)}
        data = {k: row[k] for k in row.keys() if k in valid}
        for bf in ("is_conditional", "condition_met"):
            if bf in data and data[bf] is not None:
                data[bf] = bool(data[bf])
        return cls(**data)

    def to_dict(self) -> dict:
        d = asdict(self)
        if d.get("depends_on"):
            try:
                d["depends_on"] = json.loads(d["depends_on"])
            except (json.JSONDecodeError, TypeError):
                pass
        return d


@dataclass
class Document:
    id: int
    transaction_id: int
    name: str
    doc_type: str = "other"
    status: str = "needed"
    file_path: Optional[str] = None
    doc_search_id: Optional[int] = None
    notes: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> Document:
        valid = {f.name for f in fields(cls)}
        return cls(**{k: row[k] for k in row.keys() if k in valid})

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Note:
    id: int
    transaction_id: int
    content: str
    is_pinned: bool = False
    created_at: Optional[str] = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> Note:
        valid = {f.name for f in fields(cls)}
        data = {k: row[k] for k in row.keys() if k in valid}
        if "is_pinned" in data:
            data["is_pinned"] = bool(data["is_pinned"])
        return cls(**data)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TimelineEvent:
    id: int
    transaction_id: int
    event_type: str
    description: str
    created_at: Optional[str] = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> TimelineEvent:
        valid = {f.name for f in fields(cls)}
        return cls(**{k: row[k] for k in row.keys() if k in valid})

    def to_dict(self) -> dict:
        return asdict(self)
