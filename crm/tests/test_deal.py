"""Tests for crm deal commands."""
from __future__ import annotations

import json

from crm.main import app


def test_add_deal(runner, seeded_db):
    """Add a deal with required company."""
    result = runner.invoke(app, [
        "deal", "add", "New Project",
        "--company", "Acme Corp",
        "--value", "100000",
        "--stage", "proposal",
    ])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["data"]["title"] == "New Project"
    assert data["data"]["value"] == 100000.0
    assert data["data"]["stage"] == "proposal"
    assert data["data"]["company_name"] == "Acme Corp"


def test_add_deal_default_stage(runner, seeded_db):
    """Deal defaults to 'lead' stage."""
    result = runner.invoke(app, [
        "deal", "add", "Default Stage Deal",
        "--company", "Acme Corp",
    ])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["data"]["stage"] == "lead"


def test_add_deal_with_contact(runner, seeded_db):
    """Add a deal with a contact reference."""
    result = runner.invoke(app, [
        "deal", "add", "Contact Deal",
        "--company", "Acme Corp",
        "--contact", "Alice Smith",
        "--notes", "Important deal",
    ])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["data"]["contact_name"] == "Alice Smith"
    assert data["data"]["notes"] == "Important deal"


def test_add_deal_invalid_stage(runner, seeded_db):
    """Invalid stage should error."""
    result = runner.invoke(app, [
        "deal", "add", "Bad Stage",
        "--company", "Acme Corp",
        "--stage", "invalid",
    ])
    assert result.exit_code == 2


def test_add_deal_nonexistent_company(runner, tmp_db):
    """Deal with non-existent company should error."""
    result = runner.invoke(app, [
        "deal", "add", "No Company Deal",
        "--company", "GhostCo",
    ])
    assert result.exit_code == 3


def test_list_deals(runner, seeded_db):
    """List all deals."""
    result = runner.invoke(app, ["deal", "list"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data["data"]) >= 1
    titles = [d["title"] for d in data["data"]]
    assert "Acme Deal" in titles


def test_list_deals_stage_filter(runner, seeded_db):
    """List deals filtered by stage."""
    result = runner.invoke(app, ["deal", "list", "--stage", "proposal"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    for d in data["data"]:
        assert d["stage"] == "proposal"


def test_list_deals_company_filter(runner, seeded_db):
    """List deals filtered by company."""
    result = runner.invoke(app, ["deal", "list", "--company", "Acme Corp"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    for d in data["data"]:
        assert d["company_name"] == "Acme Corp"


def test_show_deal(runner, seeded_db):
    """Show deal details."""
    result = runner.invoke(app, ["deal", "show", "Acme Deal"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["data"]["title"] == "Acme Deal"
    assert data["data"]["value"] == 50000.0
    assert data["data"]["company_name"] == "Acme Corp"


def test_show_deal_not_found(runner, tmp_db):
    """Show non-existent deal should error."""
    result = runner.invoke(app, ["deal", "show", "Nothing"])
    assert result.exit_code == 3


def test_move_deal(runner, seeded_db):
    """Move a deal to a new stage."""
    result = runner.invoke(app, ["deal", "move", "Acme Deal", "--stage", "negotiation"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["data"]["stage"] == "negotiation"


def test_move_deal_invalid_stage(runner, seeded_db):
    """Move to invalid stage should error."""
    result = runner.invoke(app, ["deal", "move", "Acme Deal", "--stage", "bad"])
    assert result.exit_code == 2


def test_move_deal_not_found(runner, tmp_db):
    """Move non-existent deal should error."""
    result = runner.invoke(app, ["deal", "move", "Ghost", "--stage", "active"])
    assert result.exit_code == 3


def test_rm_deal(runner, seeded_db):
    """Remove a deal."""
    result = runner.invoke(app, ["deal", "rm", "Acme Deal"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["data"]["title"] == "Acme Deal"

    # Verify it's gone
    result = runner.invoke(app, ["deal", "show", "Acme Deal"])
    assert result.exit_code == 3


def test_rm_deal_not_found(runner, tmp_db):
    """Remove non-existent deal should error."""
    result = runner.invoke(app, ["deal", "rm", "Nothing"])
    assert result.exit_code == 3
