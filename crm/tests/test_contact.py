"""Tests for crm contact commands."""
from __future__ import annotations

import json

from crm.main import app


def test_add_contact_no_company(runner, tmp_db):
    """Add a contact without a company."""
    result = runner.invoke(app, ["contact", "add", "Bob Jones"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["data"]["name"] == "Bob Jones"
    assert data["data"]["company_id"] is None


def test_add_contact_with_company(runner, seeded_db):
    """Add a contact linked to an existing company."""
    result = runner.invoke(app, [
        "contact", "add", "Bob Jones",
        "--company", "Acme Corp",
        "--email", "bob@acme.com",
        "--phone", "555-1234",
        "--role", "Engineer",
        "--tags", "dev,backend",
        "--notes", "Good dev",
    ])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["data"]["name"] == "Bob Jones"
    assert data["data"]["company_name"] == "Acme Corp"
    assert data["data"]["email"] == "bob@acme.com"
    assert data["data"]["tags"] == "dev,backend"


def test_add_contact_nonexistent_company(runner, tmp_db):
    """Add a contact with a company that doesn't exist should error."""
    result = runner.invoke(app, [
        "contact", "add", "Ghost User",
        "--company", "NoSuchCo",
    ])
    assert result.exit_code == 3
    err = json.loads(result.output)
    assert err["code"] == "NOT_FOUND"


def test_list_contacts(runner, seeded_db):
    """List all contacts."""
    result = runner.invoke(app, ["contact", "list"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data["data"]) >= 1
    names = [c["name"] for c in data["data"]]
    assert "Alice Smith" in names


def test_list_contacts_company_filter(runner, seeded_db):
    """List contacts filtered by company."""
    result = runner.invoke(app, ["contact", "list", "--company", "Acme Corp"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    for c in data["data"]:
        assert c["company_name"] == "Acme Corp"


def test_list_contacts_tag_filter(runner, seeded_db):
    """List contacts filtered by tag."""
    result = runner.invoke(app, ["contact", "list", "--tag", "vip"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data["data"]) >= 1
    for c in data["data"]:
        assert "vip" in c["tags"]


def test_show_contact(runner, seeded_db):
    """Show contact details."""
    result = runner.invoke(app, ["contact", "show", "Alice Smith"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["data"]["name"] == "Alice Smith"
    assert data["data"]["company_name"] == "Acme Corp"
    assert "interactions_count" in data["data"]


def test_show_contact_not_found(runner, tmp_db):
    """Show non-existent contact should error."""
    result = runner.invoke(app, ["contact", "show", "Nobody"])
    assert result.exit_code == 3


def test_edit_contact(runner, seeded_db):
    """Edit a contact's fields."""
    result = runner.invoke(app, [
        "contact", "edit", "Alice Smith",
        "--email", "alice.new@acme.com",
        "--role", "VP Engineering",
    ])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["data"]["email"] == "alice.new@acme.com"
    assert data["data"]["role"] == "VP Engineering"


def test_edit_contact_not_found(runner, tmp_db):
    """Edit non-existent contact should error."""
    result = runner.invoke(app, ["contact", "edit", "Ghost", "--email", "x@x.com"])
    assert result.exit_code == 3


def test_edit_contact_no_fields(runner, seeded_db):
    """Edit with no fields should return INVALID_INPUT."""
    result = runner.invoke(app, ["contact", "edit", "Alice Smith"])
    assert result.exit_code == 2


def test_rm_contact(runner, seeded_db):
    """Remove a contact and verify it's gone."""
    # First remove the deal that references this contact (FK constraint)
    runner.invoke(app, ["deal", "rm", "Acme Deal"])
    result = runner.invoke(app, ["contact", "rm", "Alice Smith"])
    assert result.exit_code == 0

    result = runner.invoke(app, ["contact", "show", "Alice Smith"])
    assert result.exit_code == 3


def test_rm_contact_not_found(runner, tmp_db):
    """Remove non-existent contact should error."""
    result = runner.invoke(app, ["contact", "rm", "Nobody"])
    assert result.exit_code == 3
