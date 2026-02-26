"""Tests for task commands."""
from tc.db import get_connection
from tc.main import app
from .conftest import parse_json


def test_generate_tasks(runner, seeded_db):
    result = runner.invoke(app, ["generate-tasks", "1"])
    assert result.exit_code == 0
    data = parse_json(result)
    assert data["data"]["tasks_generated"] > 0


def test_generate_tasks_blocks_if_exists(runner, seeded_db):
    runner.invoke(app, ["generate-tasks", "1"])
    result = runner.invoke(app, ["generate-tasks", "1"])
    assert result.exit_code != 0  # Should fail — already generated


def test_regenerate_tasks(runner, seeded_db):
    runner.invoke(app, ["generate-tasks", "1"])
    result = runner.invoke(app, ["regenerate-tasks", "1"])
    assert result.exit_code == 0
    data = parse_json(result)
    assert data["data"]["generated"] > 0


def test_tasks_list(runner, seeded_db):
    runner.invoke(app, ["generate-tasks", "1"])
    result = runner.invoke(app, ["tasks", "1"])
    assert result.exit_code == 0
    data = parse_json(result)
    assert len(data["data"]) > 0


def test_tasks_filter_by_phase(runner, seeded_db):
    runner.invoke(app, ["generate-tasks", "1"])
    result = runner.invoke(app, ["tasks", "1", "--phase", "day_0"])
    assert result.exit_code == 0
    data = parse_json(result)
    assert all(t["phase"] == "day_0" for t in data["data"])


def test_complete_task(runner, seeded_db):
    runner.invoke(app, ["generate-tasks", "1"])
    # Get first task ID
    tasks_result = runner.invoke(app, ["tasks", "1"])
    first_task_id = parse_json(tasks_result)["data"][0]["id"]

    result = runner.invoke(app, ["complete-task", str(first_task_id)])
    assert result.exit_code == 0
    data = parse_json(result)
    assert data["data"]["status"] == "completed"


def test_skip_task_with_reason(runner, seeded_db):
    runner.invoke(app, ["generate-tasks", "1"])
    tasks_result = runner.invoke(app, ["tasks", "1"])
    first_task_id = parse_json(tasks_result)["data"][0]["id"]

    result = runner.invoke(app, ["skip-task", str(first_task_id), "--reason", "Not applicable"])
    assert result.exit_code == 0
    data = parse_json(result)
    assert data["data"]["status"] == "skipped"


def test_add_manual_task(runner, seeded_db):
    result = runner.invoke(app, [
        "add-task", "1", "--title", "Custom follow-up",
        "--due-date", "2026-03-15", "--phase", "option_period",
    ])
    assert result.exit_code == 0
    data = parse_json(result)
    assert data["data"]["title"] == "Custom follow-up"


def test_tasks_due(runner, seeded_db):
    runner.invoke(app, ["generate-tasks", "1"])
    result = runner.invoke(app, ["tasks-due", "--days", "365"])
    assert result.exit_code == 0
    data = parse_json(result)
    assert len(data["data"]) > 0


def test_regenerate_preserves_completed(runner, seeded_db):
    """Completed tasks should survive regeneration."""
    runner.invoke(app, ["generate-tasks", "1"])

    # Complete a task
    tasks_result = runner.invoke(app, ["tasks", "1"])
    first_id = parse_json(tasks_result)["data"][0]["id"]
    runner.invoke(app, ["complete-task", str(first_id)])

    # Regenerate
    runner.invoke(app, ["regenerate-tasks", "1"])

    # The completed task should still be there
    conn = get_connection(seeded_db)
    completed = conn.execute("SELECT COUNT(*) as cnt FROM tasks WHERE transaction_id = 1 AND status = 'completed'").fetchone()
    conn.close()
    assert completed["cnt"] == 1
