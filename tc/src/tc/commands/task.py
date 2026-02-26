"""Task management commands including template-based generation."""
from __future__ import annotations

import json
from datetime import date, timedelta
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from ..business_days import adjust_to_business_day
from ..config import VALID_TASK_STATUSES, VALID_PHASES, PHASE_DISPLAY_NAMES, PHASE_ORDER
from ..db import get_connection, log_event
from ..main import ExitCode
from ..models import Task, Transaction
from ..output import get_settings, emit_success, emit_error
from ..templates import TASK_TEMPLATES, TaskTemplate


# --- Task generation helpers ---

def _get_reference_date(template: TaskTemplate, tx: Transaction) -> Optional[date]:
    """Get the reference date for a template's due date calculation."""
    ref_str = None
    if template.due_date_reference == "effective":
        ref_str = tx.effective_date
    elif template.due_date_reference == "closing":
        ref_str = tx.closing_date
    elif template.due_date_reference == "option_end":
        ref_str = tx.option_period_end
    if ref_str:
        return date.fromisoformat(ref_str)
    return None


def _calculate_due_date(template: TaskTemplate, tx: Transaction) -> Optional[str]:
    """Calculate a task's due date from template offset + reference date."""
    ref = _get_reference_date(template, tx)
    if not ref:
        return None
    raw = ref + timedelta(days=template.due_date_offset)
    adjusted = adjust_to_business_day(raw)
    return adjusted.isoformat()


def _generate_tasks_for_txn(conn, txn_id: int) -> int:
    """Generate tasks from templates for a transaction. Returns count of tasks created."""
    row = conn.execute("SELECT * FROM transactions WHERE id = ?", (txn_id,)).fetchone()
    if not row:
        return 0
    tx = Transaction.from_row(row)

    count = 0
    for tmpl in TASK_TEMPLATES:
        # Evaluate condition
        condition_met = True
        if tmpl.is_conditional and tmpl.condition:
            condition_met = tmpl.condition(tx)

        if not condition_met:
            continue

        due = _calculate_due_date(tmpl, tx)
        depends_json = json.dumps(tmpl.depends_on) if tmpl.depends_on else None

        conn.execute(
            """INSERT INTO tasks (
                transaction_id, template_id, title, description,
                phase, group_id, due_date, status,
                sort_order, depends_on, is_conditional, condition_met
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?)""",
            (
                txn_id, tmpl.id, tmpl.title, tmpl.description,
                tmpl.phase, tmpl.group_id, due,
                tmpl.sort_order, depends_json,
                int(tmpl.is_conditional), int(condition_met),
            ),
        )
        count += 1

    conn.commit()
    if count:
        log_event(conn, txn_id, "task_added", f"Generated {count} tasks from templates")
    return count


# --- CLI commands ---

def tasks(
    ctx: typer.Context,
    txn_id: int = typer.Argument(..., help="Transaction ID"),
    status: Optional[str] = typer.Option(None, "--status", help="Filter by status"),
    phase: Optional[str] = typer.Option(None, "--phase", help="Filter by phase"),
    group: Optional[str] = typer.Option(None, "--group", help="Filter by group"),
    due_before: Optional[str] = typer.Option(None, "--due-before", help="Show tasks due before this date (YYYY-MM-DD)"),
) -> None:
    """List tasks for a transaction."""
    settings = get_settings(ctx)
    conn = get_connection()

    txn = conn.execute("SELECT id FROM transactions WHERE id = ?", (txn_id,)).fetchone()
    if not txn:
        conn.close()
        emit_error(f"Transaction #{txn_id} not found", settings, code="NOT_FOUND", exit_code=ExitCode.NOT_FOUND)

    query = "SELECT * FROM tasks WHERE transaction_id = ?"
    params: list = [txn_id]

    if status:
        query += " AND status = ?"
        params.append(status)
    if phase:
        query += " AND phase = ?"
        params.append(phase)
    if group:
        query += " AND group_id = ?"
        params.append(group)
    if due_before:
        query += " AND due_date <= ?"
        params.append(due_before)

    query += " ORDER BY sort_order, due_date"
    rows = conn.execute(query, params).fetchall()
    conn.close()

    task_list = [Task.from_row(r) for r in rows]

    if settings.format == "text":
        if not task_list:
            print(f"No tasks matching filters for transaction #{txn_id}")
            raise typer.Exit(ExitCode.SUCCESS)
        table = Table(title=f"Tasks — Transaction #{txn_id}")
        table.add_column("ID", style="bold")
        table.add_column("Status")
        table.add_column("Phase")
        table.add_column("Due")
        table.add_column("Title")
        for t in task_list:
            status_style = {"pending": "yellow", "in_progress": "cyan", "completed": "green", "skipped": "dim"}.get(t.status, "")
            table.add_row(str(t.id), f"[{status_style}]{t.status}[/{status_style}]", PHASE_DISPLAY_NAMES.get(t.phase, t.phase or "-"), t.due_date or "-", t.title)
        Console().print(table)
        raise typer.Exit(ExitCode.SUCCESS)

    emit_success([t.to_dict() for t in task_list], settings)


def tasks_due(
    ctx: typer.Context,
    days: int = typer.Option(7, "--days", help="Show tasks due within N days"),
    txn_id: Optional[int] = typer.Option(None, "--txn", help="Limit to one transaction"),
) -> None:
    """Show tasks due soon across all (or one) transaction(s)."""
    settings = get_settings(ctx)
    conn = get_connection()

    cutoff = (date.today() + timedelta(days=days)).isoformat()
    today = date.today().isoformat()

    query = """
        SELECT t.*, tx.address, tx.city
        FROM tasks t
        JOIN transactions tx ON tx.id = t.transaction_id
        WHERE t.status IN ('pending', 'in_progress')
          AND t.due_date IS NOT NULL
          AND t.due_date <= ?
          AND tx.status NOT IN ('closed', 'terminated')
    """
    params: list = [cutoff]

    if txn_id:
        query += " AND t.transaction_id = ?"
        params.append(txn_id)

    query += " ORDER BY t.due_date, t.sort_order"
    rows = conn.execute(query, params).fetchall()
    conn.close()

    if settings.format == "text":
        if not rows:
            print(f"No tasks due in the next {days} days.")
            raise typer.Exit(ExitCode.SUCCESS)
        console = Console()
        table = Table(title=f"Tasks Due — Next {days} Days")
        table.add_column("Task ID", style="bold")
        table.add_column("Txn")
        table.add_column("Due")
        table.add_column("Status")
        table.add_column("Title")
        for r in rows:
            overdue = r["due_date"] < today
            due_str = r["due_date"]
            if overdue:
                due_str = f"[red]{due_str} (OVERDUE)[/red]"
            txn_label = f"#{r['transaction_id']} {r['address'] or ''}"
            table.add_row(str(r["id"]), txn_label[:30], due_str, r["status"], r["title"])
        console.print(table)
        raise typer.Exit(ExitCode.SUCCESS)

    results = []
    for r in rows:
        results.append({
            "task_id": r["id"], "transaction_id": r["transaction_id"],
            "address": r["address"], "city": r["city"],
            "due_date": r["due_date"], "status": r["status"],
            "title": r["title"], "overdue": r["due_date"] < today,
        })
    emit_success(results, settings)


def complete_task(
    ctx: typer.Context,
    task_id: int = typer.Argument(..., help="Task ID"),
) -> None:
    """Mark a task as completed."""
    settings = get_settings(ctx)
    conn = get_connection()

    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if not row:
        conn.close()
        emit_error(f"Task #{task_id} not found", settings, code="NOT_FOUND", exit_code=ExitCode.NOT_FOUND)

    if row["status"] == "completed":
        conn.close()
        emit_error(f"Task #{task_id} is already completed", settings, code="ALREADY_DONE")

    conn.execute(
        "UPDATE tasks SET status = 'completed', completed_at = datetime('now') WHERE id = ?",
        (task_id,),
    )
    conn.commit()

    log_event(conn, row["transaction_id"], "task_completed", f"Completed: {row['title']}")
    conn.close()

    emit_success({"id": task_id, "status": "completed"}, settings, text=f"Task #{task_id} completed: {row['title']}")


def skip_task(
    ctx: typer.Context,
    task_id: int = typer.Argument(..., help="Task ID"),
    reason: str = typer.Option(None, "--reason", help="Reason for skipping"),
) -> None:
    """Skip a task with optional reason."""
    settings = get_settings(ctx)
    conn = get_connection()

    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if not row:
        conn.close()
        emit_error(f"Task #{task_id} not found", settings, code="NOT_FOUND", exit_code=ExitCode.NOT_FOUND)

    conn.execute(
        "UPDATE tasks SET status = 'skipped', skip_reason = ? WHERE id = ?",
        (reason, task_id),
    )
    conn.commit()

    desc = f"Skipped: {row['title']}"
    if reason:
        desc += f" — {reason}"
    log_event(conn, row["transaction_id"], "task_skipped", desc)
    conn.close()

    emit_success({"id": task_id, "status": "skipped"}, settings, text=f"Task #{task_id} skipped: {row['title']}")


def add_task(
    ctx: typer.Context,
    txn_id: int = typer.Argument(..., help="Transaction ID"),
    title: str = typer.Option(..., "--title"),
    description: str = typer.Option(None, "--description"),
    due_date: str = typer.Option(None, "--due-date", help="YYYY-MM-DD"),
    phase: str = typer.Option(None, "--phase"),
    group: str = typer.Option(None, "--group"),
) -> None:
    """Add a manual task to a transaction."""
    settings = get_settings(ctx)
    conn = get_connection()

    txn = conn.execute("SELECT id FROM transactions WHERE id = ?", (txn_id,)).fetchone()
    if not txn:
        conn.close()
        emit_error(f"Transaction #{txn_id} not found", settings, code="NOT_FOUND", exit_code=ExitCode.NOT_FOUND)

    if due_date:
        try:
            date.fromisoformat(due_date)
        except ValueError:
            conn.close()
            emit_error(f"Invalid due date: {due_date}. Use YYYY-MM-DD.", settings, code="INVALID_INPUT", exit_code=ExitCode.INVALID_ARGS)

    cursor = conn.execute(
        "INSERT INTO tasks (transaction_id, title, description, due_date, phase, group_id) VALUES (?, ?, ?, ?, ?, ?)",
        (txn_id, title, description, due_date, phase, group),
    )
    task_id = cursor.lastrowid
    conn.commit()

    log_event(conn, txn_id, "task_added", f"Manual task: {title}")
    conn.close()

    emit_success({"id": task_id, "transaction_id": txn_id, "title": title}, settings, text=f"Task #{task_id} added to transaction #{txn_id}: {title}")


def generate_tasks(
    ctx: typer.Context,
    txn_id: int = typer.Argument(..., help="Transaction ID"),
) -> None:
    """Generate tasks from templates based on transaction properties."""
    settings = get_settings(ctx)
    conn = get_connection()

    txn = conn.execute("SELECT id FROM transactions WHERE id = ?", (txn_id,)).fetchone()
    if not txn:
        conn.close()
        emit_error(f"Transaction #{txn_id} not found", settings, code="NOT_FOUND", exit_code=ExitCode.NOT_FOUND)

    # Check if template tasks already exist
    existing = conn.execute(
        "SELECT COUNT(*) as cnt FROM tasks WHERE transaction_id = ? AND template_id IS NOT NULL",
        (txn_id,),
    ).fetchone()
    if existing["cnt"] > 0:
        conn.close()
        emit_error(
            f"Transaction #{txn_id} already has {existing['cnt']} template tasks. Use regenerate-tasks to re-evaluate.",
            settings, code="ALREADY_EXISTS",
        )

    count = _generate_tasks_for_txn(conn, txn_id)
    conn.close()

    emit_success({"transaction_id": txn_id, "tasks_generated": count}, settings, text=f"Generated {count} tasks for transaction #{txn_id}")


def regenerate_tasks(
    ctx: typer.Context,
    txn_id: int = typer.Argument(..., help="Transaction ID"),
) -> None:
    """Re-evaluate task conditions. Removes pending template tasks and regenerates."""
    settings = get_settings(ctx)
    conn = get_connection()

    txn = conn.execute("SELECT id FROM transactions WHERE id = ?", (txn_id,)).fetchone()
    if not txn:
        conn.close()
        emit_error(f"Transaction #{txn_id} not found", settings, code="NOT_FOUND", exit_code=ExitCode.NOT_FOUND)

    # Delete only pending template-generated tasks
    deleted = conn.execute(
        "DELETE FROM tasks WHERE transaction_id = ? AND template_id IS NOT NULL AND status = 'pending'",
        (txn_id,),
    ).rowcount
    conn.commit()

    count = _generate_tasks_for_txn(conn, txn_id)
    conn.close()

    emit_success(
        {"transaction_id": txn_id, "removed": deleted, "generated": count},
        settings,
        text=f"Regenerated tasks for #{txn_id}: removed {deleted} pending, generated {count} new",
    )
