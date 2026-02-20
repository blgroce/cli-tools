"""Tests for crm company commands."""
from __future__ import annotations

import json

from crm.main import app


def test_add_company(runner, tmp_db):
    """Add a company and verify JSON output."""
    result = runner.invoke(app, ["company", "add", "TestCo"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["success"] is True
    assert data["data"]["name"] == "TestCo"
    assert data["data"]["status"] == "prospect"


def test_add_company_with_options(runner, tmp_db):
    """Add a company with all options."""
    result = runner.invoke(app, [
        "company", "add", "FullCo",
        "--status", "active",
        "--industry", "Finance",
        "--website", "https://fullco.com",
        "--notes", "A great company",
    ])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["data"]["industry"] == "Finance"
    assert data["data"]["status"] == "active"
    assert data["data"]["website"] == "https://fullco.com"
    assert data["data"]["notes"] == "A great company"


def test_add_duplicate_company(runner, tmp_db):
    """Adding a duplicate company should return an error."""
    runner.invoke(app, ["company", "add", "DupeCo"])
    result = runner.invoke(app, ["company", "add", "DupeCo"])
    assert result.exit_code == 1
    err = json.loads(result.output)
    assert err["error"] is True
    assert err["code"] == "DUPLICATE"


def test_list_companies(runner, seeded_db):
    """List all companies."""
    result = runner.invoke(app, ["company", "list"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["success"] is True
    assert len(data["data"]) >= 1
    names = [c["name"] for c in data["data"]]
    assert "Acme Corp" in names


def test_list_companies_with_status_filter(runner, seeded_db):
    """List companies filtered by status."""
    result = runner.invoke(app, ["company", "list", "--status", "active"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    for c in data["data"]:
        assert c["status"] == "active"


def test_list_companies_empty_filter(runner, seeded_db):
    """Filter with non-matching status returns empty list."""
    result = runner.invoke(app, ["company", "list", "--status", "past"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["data"] == []


def test_show_company(runner, seeded_db):
    """Show company details including counts."""
    result = runner.invoke(app, ["company", "show", "Acme Corp"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["data"]["name"] == "Acme Corp"
    assert "contacts_count" in data["data"]
    assert "deals_count" in data["data"]
    assert data["data"]["contacts_count"] >= 1
    assert data["data"]["deals_count"] >= 1


def test_show_company_not_found(runner, tmp_db):
    """Show non-existent company should error."""
    result = runner.invoke(app, ["company", "show", "Nope"])
    assert result.exit_code == 3
    err = json.loads(result.output)
    assert err["code"] == "NOT_FOUND"


def test_edit_company(runner, seeded_db):
    """Edit a company field."""
    result = runner.invoke(app, ["company", "edit", "Acme Corp", "--industry", "AI"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["data"]["industry"] == "AI"


def test_edit_company_rename(runner, seeded_db):
    """Rename a company."""
    result = runner.invoke(app, ["company", "edit", "Acme Corp", "--name", "Acme Inc"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["data"]["name"] == "Acme Inc"


def test_edit_company_not_found(runner, tmp_db):
    """Edit non-existent company should error."""
    result = runner.invoke(app, ["company", "edit", "Ghost", "--industry", "Nothing"])
    assert result.exit_code == 3


def test_edit_company_no_fields(runner, seeded_db):
    """Edit with no fields should return INVALID_INPUT."""
    result = runner.invoke(app, ["company", "edit", "Acme Corp"])
    assert result.exit_code == 2


def test_rm_company_no_relations(runner, tmp_db):
    """Remove a company with no relations."""
    runner.invoke(app, ["company", "add", "ToDelete"])
    result = runner.invoke(app, ["company", "rm", "ToDelete"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["data"]["name"] == "ToDelete"

    # Verify it's gone
    result = runner.invoke(app, ["company", "show", "ToDelete"])
    assert result.exit_code == 3


def test_rm_company_with_relations_blocked(runner, seeded_db):
    """Remove a company with contacts/deals without --force should fail."""
    result = runner.invoke(app, ["company", "rm", "Acme Corp"])
    assert result.exit_code == 1
    err = json.loads(result.output)
    assert err["code"] == "HAS_RELATIONS"


def test_rm_company_force(runner, seeded_db):
    """Remove a company with --force should cascade delete."""
    result = runner.invoke(app, ["company", "rm", "Acme Corp", "--force"])
    assert result.exit_code == 0

    # Verify the company is gone
    result = runner.invoke(app, ["company", "show", "Acme Corp"])
    assert result.exit_code == 3


def test_rm_company_not_found(runner, tmp_db):
    """Remove non-existent company should error."""
    result = runner.invoke(app, ["company", "rm", "Ghost"])
    assert result.exit_code == 3
