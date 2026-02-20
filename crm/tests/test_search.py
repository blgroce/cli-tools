"""Tests for crm search command."""
from __future__ import annotations

import json

from crm.main import app


def test_search_finds_company(runner, seeded_db):
    """Search should find companies by name."""
    result = runner.invoke(app, ["search", "Acme"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data["data"]["companies"]) >= 1


def test_search_finds_contact(runner, seeded_db):
    """Search should find contacts by name."""
    result = runner.invoke(app, ["search", "Alice"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data["data"]["contacts"]) >= 1


def test_search_finds_interaction(runner, seeded_db):
    """Search should find interactions by summary."""
    result = runner.invoke(app, ["search", "roadmap"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data["data"]["interactions"]) >= 1


def test_search_finds_deal(runner, seeded_db):
    """Search should find deals by title."""
    result = runner.invoke(app, ["search", "Acme Deal"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data["data"]["deals"]) >= 1


def test_search_no_results(runner, seeded_db):
    """Search with no matching term should return empty lists."""
    result = runner.invoke(app, ["search", "zzzznonexistent"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["data"]["companies"] == []
    assert data["data"]["contacts"] == []
    assert data["data"]["interactions"] == []
    assert data["data"]["deals"] == []


def test_search_cross_entity(runner, seeded_db):
    """Search term matching multiple entity types."""
    result = runner.invoke(app, ["search", "Acme"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    # "Acme" matches company name and deal title
    assert len(data["data"]["companies"]) >= 1
    assert len(data["data"]["deals"]) >= 1
