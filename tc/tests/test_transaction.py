"""Tests for transaction CRUD commands."""
from tc.main import app
from .conftest import parse_json


def test_create_transaction(runner, tmp_db):
    result = runner.invoke(app, [
        "create", "--address", "123 Main St", "--city", "Austin",
        "--type", "buyer", "--effective-date", "2026-03-01",
        "--closing-date", "2026-04-15", "--option-days", "10",
        "--sales-price", "350000", "--earnest-money", "5000",
        "--financed", "--financing-amount", "280000",
    ])
    assert result.exit_code == 0
    data = parse_json(result)
    assert data["success"] is True
    assert data["data"]["id"] == 1
    assert data["data"]["address"] == "123 Main St"
    assert data["data"]["tasks_generated"] > 0


def test_create_cash_offer_fewer_tasks(runner, tmp_db):
    """Cash offers should generate fewer tasks (no financing tasks)."""
    # Financed
    r1 = runner.invoke(app, [
        "create", "--address", "A", "--city", "X",
        "--effective-date", "2026-03-01", "--closing-date", "2026-04-15",
        "--option-days", "10", "--financed",
    ])
    financed_count = parse_json(r1)["data"]["tasks_generated"]

    # Cash
    r2 = runner.invoke(app, [
        "create", "--address", "B", "--city", "X",
        "--effective-date", "2026-03-01", "--closing-date", "2026-04-15",
        "--option-days", "10", "--cash",
    ])
    cash_count = parse_json(r2)["data"]["tasks_generated"]

    assert cash_count < financed_count


def test_create_no_tasks(runner, tmp_db):
    result = runner.invoke(app, [
        "create", "--address", "No Tasks Pl", "--no-tasks",
    ])
    assert result.exit_code == 0
    data = parse_json(result)
    assert data["data"]["tasks_generated"] == 0


def test_get_transaction(runner, seeded_db):
    result = runner.invoke(app, ["get", "1"])
    assert result.exit_code == 0
    data = parse_json(result)
    assert data["data"]["address"] == "123 Main St"
    assert data["data"]["is_financed"] is True
    assert data["data"]["has_hoa"] is True


def test_get_not_found(runner, tmp_db):
    result = runner.invoke(app, ["get", "999"])
    assert result.exit_code != 0


def test_list_transactions(runner, seeded_db):
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    data = parse_json(result)
    assert len(data["data"]) == 1
    assert data["data"][0]["address"] == "123 Main St"


def test_update_transaction(runner, seeded_db):
    result = runner.invoke(app, ["update", "1", "--status", "pending", "--closing-date", "2026-04-20"])
    assert result.exit_code == 0
    data = parse_json(result)
    assert "status" in data["data"]["updated"]
    assert "closing_date" in data["data"]["updated"]


def test_update_recalculates_option_end(runner, seeded_db):
    result = runner.invoke(app, ["update", "1", "--effective-date", "2026-03-05"])
    assert result.exit_code == 0
    # Verify option_period_end was recalculated
    get_result = runner.invoke(app, ["get", "1"])
    txn = parse_json(get_result)["data"]
    assert txn["option_period_end"] == "2026-03-15"  # 2026-03-05 + 10 days


def test_search_by_address(runner, seeded_db):
    result = runner.invoke(app, ["search", "Main"])
    assert result.exit_code == 0
    data = parse_json(result)
    assert len(data["data"]) == 1


def test_search_by_person(runner, seeded_db):
    result = runner.invoke(app, ["search", "Smith"])
    assert result.exit_code == 0
    data = parse_json(result)
    assert len(data["data"]) == 1
    # Verify disambiguation data is included
    hit = data["data"][0]
    assert "matched_on" in hit
    assert any("Smith" in m for m in hit["matched_on"])
    assert "people" in hit
    assert any(p["name"] == "John Smith" for p in hit["people"])


def test_search_shared_person(runner, tmp_db):
    """Same person on multiple transactions should return all with match context."""
    # Create two transactions
    runner.invoke(app, [
        "create", "--address", "100 Alpha St", "--city", "Austin",
        "--effective-date", "2026-03-01", "--closing-date", "2026-04-15",
        "--option-days", "10", "--no-tasks",
    ])
    runner.invoke(app, [
        "create", "--address", "200 Beta Ave", "--city", "Pflugerville",
        "--effective-date", "2026-03-05", "--closing-date", "2026-05-01",
        "--option-days", "7", "--no-tasks",
    ])
    # Add same title contact to both
    runner.invoke(app, ["add-person", "1", "--role", "title_contact", "--name", "Ben Garcia", "--company", "Capital Title"])
    runner.invoke(app, ["add-person", "2", "--role", "title_contact", "--name", "Ben Garcia", "--company", "Capital Title"])
    # Add a buyer only on transaction 1
    runner.invoke(app, ["add-person", "1", "--role", "buyer", "--name", "Alice Nguyen"])

    result = runner.invoke(app, ["search", "Ben Garcia"])
    assert result.exit_code == 0
    data = parse_json(result)
    assert len(data["data"]) == 2
    # Both should show Ben as the match reason
    for hit in data["data"]:
        assert any("Ben Garcia" in m for m in hit["matched_on"])
        assert any(p["name"] == "Ben Garcia" for p in hit["people"])
    # Transaction 1 should also list Alice in people
    txn1 = next(h for h in data["data"] if h["address"] == "100 Alpha St")
    assert any(p["name"] == "Alice Nguyen" for p in txn1["people"])


def test_search_no_results(runner, seeded_db):
    result = runner.invoke(app, ["search", "zzzznotfound"])
    assert result.exit_code == 0
    data = parse_json(result)
    assert len(data["data"]) == 0
