"""Report commands: summary, dashboard, timeline."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ..config import PHASE_DISPLAY_NAMES
from ..db import get_connection
from ..main import ExitCode
from ..models import Transaction, Person, Task, Document, Note, TimelineEvent
from ..output import get_settings, emit_success, emit_error


def _days_until(target: str) -> Optional[int]:
    """Days from today until a date string."""
    try:
        d = date.fromisoformat(target)
        return (d - date.today()).days
    except (ValueError, TypeError):
        return None


def summary(
    ctx: typer.Context,
    txn_id: int = typer.Argument(..., help="Transaction ID"),
) -> None:
    """Full transaction summary — the agent's go-to command."""
    settings = get_settings(ctx)
    conn = get_connection()
    today = date.today().isoformat()

    # Transaction
    row = conn.execute("SELECT * FROM transactions WHERE id = ?", (txn_id,)).fetchone()
    if not row:
        conn.close()
        emit_error(f"Transaction #{txn_id} not found", settings, code="NOT_FOUND", exit_code=ExitCode.NOT_FOUND)
    tx = Transaction.from_row(row)

    # People
    people_rows = conn.execute("SELECT * FROM people WHERE transaction_id = ? ORDER BY role", (txn_id,)).fetchall()
    people_list = [Person.from_row(r) for r in people_rows]

    # Overdue tasks
    overdue_rows = conn.execute(
        "SELECT * FROM tasks WHERE transaction_id = ? AND status IN ('pending', 'in_progress') AND due_date < ? ORDER BY due_date",
        (txn_id, today),
    ).fetchall()
    overdue = [Task.from_row(r) for r in overdue_rows]

    # Upcoming tasks (next 5 pending/in_progress, not overdue)
    upcoming_rows = conn.execute(
        "SELECT * FROM tasks WHERE transaction_id = ? AND status IN ('pending', 'in_progress') AND (due_date >= ? OR due_date IS NULL) ORDER BY due_date NULLS LAST, sort_order LIMIT 5",
        (txn_id, today),
    ).fetchall()
    upcoming = [Task.from_row(r) for r in upcoming_rows]

    # Recently completed (last 5)
    completed_rows = conn.execute(
        "SELECT * FROM tasks WHERE transaction_id = ? AND status = 'completed' ORDER BY completed_at DESC LIMIT 5",
        (txn_id,),
    ).fetchall()
    completed = [Task.from_row(r) for r in completed_rows]

    # Task counts
    task_counts = {}
    for r in conn.execute("SELECT status, COUNT(*) as cnt FROM tasks WHERE transaction_id = ? GROUP BY status", (txn_id,)).fetchall():
        task_counts[r["status"]] = r["cnt"]

    # Documents by status
    doc_counts = {}
    for r in conn.execute("SELECT status, COUNT(*) as cnt FROM documents WHERE transaction_id = ? GROUP BY status", (txn_id,)).fetchall():
        doc_counts[r["status"]] = r["cnt"]

    # Recent notes (last 5)
    note_rows = conn.execute(
        "SELECT * FROM notes WHERE transaction_id = ? ORDER BY is_pinned DESC, created_at DESC LIMIT 5",
        (txn_id,),
    ).fetchall()
    recent_notes = [Note.from_row(r) for r in note_rows]

    conn.close()

    # --- Build output ---
    data = {
        "transaction": tx.to_dict(),
        "people": [p.to_dict() for p in people_list],
        "overdue_tasks": [t.to_dict() for t in overdue],
        "upcoming_tasks": [t.to_dict() for t in upcoming],
        "recently_completed": [t.to_dict() for t in completed],
        "task_counts": task_counts,
        "document_counts": doc_counts,
        "recent_notes": [n.to_dict() for n in recent_notes],
        "key_dates": {},
    }

    # Key dates with days remaining
    for label, val in [("effective", tx.effective_date), ("option_end", tx.option_period_end), ("closing", tx.closing_date)]:
        if val:
            days = _days_until(val)
            data["key_dates"][label] = {"date": val, "days_remaining": days}

    if settings.format == "text":
        console = Console()
        console.print()

        # Header
        console.print(Panel(
            f"[bold]{tx.address or 'No address'}[/bold], {tx.city or ''}\n"
            f"Status: [bold]{tx.status}[/bold]  |  Type: {tx.type or '-'}  |  "
            f"Price: ${tx.sales_price:,.0f}" if tx.sales_price else f"Status: [bold]{tx.status}[/bold]  |  Type: {tx.type or '-'}",
            title=f"Transaction #{tx.id}",
        ))

        # Key dates
        dates_parts = []
        if tx.effective_date:
            d = _days_until(tx.effective_date)
            dates_parts.append(f"Effective: {tx.effective_date}")
        if tx.option_period_end:
            d = _days_until(tx.option_period_end)
            marker = f" [red]({d}d)[/red]" if d is not None and d <= 3 else f" ({d}d)" if d is not None else ""
            dates_parts.append(f"Option End: {tx.option_period_end}{marker}")
        if tx.closing_date:
            d = _days_until(tx.closing_date)
            marker = f" ({d}d)" if d is not None else ""
            dates_parts.append(f"Closing: {tx.closing_date}{marker}")
        if dates_parts:
            console.print("  " + "  |  ".join(dates_parts))

        # Financials
        fin_parts = []
        if tx.earnest_money:
            fin_parts.append(f"EM: ${tx.earnest_money:,.0f}")
        if tx.option_fee:
            fin_parts.append(f"Option Fee: ${tx.option_fee:,.0f}")
        if tx.is_financed and tx.financing_amount:
            fin_parts.append(f"Financing: ${tx.financing_amount:,.0f}")
        elif not tx.is_financed:
            fin_parts.append("CASH")
        if fin_parts:
            console.print("  " + "  |  ".join(fin_parts))

        # Flags
        flags = []
        if tx.has_hoa: flags.append("HOA")
        if tx.has_mud: flags.append("MUD")
        if tx.is_pre_1978: flags.append("Pre-1978")
        if tx.is_new_construction: flags.append("New Construction")
        if flags:
            console.print(f"  Flags: {', '.join(flags)}")

        # People
        if people_list:
            console.print(f"\n[bold]People ({len(people_list)})[/bold]")
            for p in people_list:
                parts = [f"  {p.role}: [bold]{p.name}[/bold]"]
                if p.email: parts.append(p.email)
                if p.phone: parts.append(p.phone)
                if p.company: parts.append(f"({p.company})")
                console.print("  ".join(parts))

        # Overdue
        if overdue:
            console.print(f"\n[bold red]Overdue Tasks ({len(overdue)})[/bold red]")
            for t in overdue:
                console.print(f"  [red]#{t.id}[/red] {t.title} — due {t.due_date}")

        # Upcoming
        if upcoming:
            console.print(f"\n[bold]Upcoming Tasks[/bold]")
            for t in upcoming:
                console.print(f"  #{t.id} {t.title} — due {t.due_date or 'no date'}")

        # Task summary
        total = sum(task_counts.values())
        if total:
            parts = [f"{task_counts.get(s, 0)} {s}" for s in ["pending", "in_progress", "completed", "skipped"] if task_counts.get(s)]
            console.print(f"\n[bold]Tasks:[/bold] {total} total ({', '.join(parts)})")

        # Documents
        if doc_counts:
            parts = [f"{v} {k}" for k, v in sorted(doc_counts.items())]
            console.print(f"[bold]Documents:[/bold] {', '.join(parts)}")

        # Recent notes
        if recent_notes:
            console.print(f"\n[bold]Recent Notes[/bold]")
            for n in recent_notes:
                pin = "[yellow]*[/yellow] " if n.is_pinned else ""
                console.print(f"  {pin}[dim]{n.created_at}[/dim] {n.content[:80]}")

        if tx.notes:
            console.print(f"\n[dim]Transaction notes: {tx.notes}[/dim]")

        console.print()
        raise typer.Exit(ExitCode.SUCCESS)

    emit_success(data, settings)


def dashboard(
    ctx: typer.Context,
    all: bool = typer.Option(False, "--all", help="Include closed/terminated transactions"),
) -> None:
    """Cross-transaction overview of active deals and upcoming deadlines."""
    settings = get_settings(ctx)
    conn = get_connection()
    today = date.today().isoformat()
    week = (date.today() + timedelta(days=7)).isoformat()

    # Active transactions
    status_filter = "" if all else "WHERE status NOT IN ('closed', 'terminated')"
    txn_rows = conn.execute(f"SELECT * FROM transactions {status_filter} ORDER BY closing_date NULLS LAST, updated_at DESC").fetchall()
    txns = [Transaction.from_row(r) for r in txn_rows]

    # Overdue tasks across active transactions
    overdue_rows = conn.execute(
        """SELECT t.*, tx.address FROM tasks t
        JOIN transactions tx ON tx.id = t.transaction_id
        WHERE t.status IN ('pending', 'in_progress')
          AND t.due_date < ?
          AND tx.status NOT IN ('closed', 'terminated')
        ORDER BY t.due_date""",
        (today,),
    ).fetchall()

    # Tasks due next 7 days
    upcoming_rows = conn.execute(
        """SELECT t.*, tx.address FROM tasks t
        JOIN transactions tx ON tx.id = t.transaction_id
        WHERE t.status IN ('pending', 'in_progress')
          AND t.due_date >= ? AND t.due_date <= ?
          AND tx.status NOT IN ('closed', 'terminated')
        ORDER BY t.due_date, t.sort_order""",
        (today, week),
    ).fetchall()

    conn.close()

    if settings.format == "text":
        console = Console()
        console.print()

        # Transactions
        if not txns:
            console.print("[dim]No active transactions.[/dim]\n")
            raise typer.Exit(ExitCode.SUCCESS)

        table = Table(title="Active Transactions")
        table.add_column("ID", style="bold")
        table.add_column("Address")
        table.add_column("Status")
        table.add_column("Type")
        table.add_column("Closing")
        table.add_column("Days")
        for t in txns:
            days = _days_until(t.closing_date) if t.closing_date else None
            days_str = str(days) if days is not None else "-"
            if days is not None and days <= 7:
                days_str = f"[red]{days}[/red]"
            table.add_row(str(t.id), t.address or "-", t.status, t.type or "-", t.closing_date or "-", days_str)
        console.print(table)

        # Overdue
        if overdue_rows:
            console.print(f"\n[bold red]Overdue ({len(overdue_rows)})[/bold red]")
            for r in overdue_rows:
                console.print(f"  [red]#{r['id']}[/red] [{r['address'] or '?'}] {r['title']} — due {r['due_date']}")

        # Upcoming
        if upcoming_rows:
            console.print(f"\n[bold]Due This Week ({len(upcoming_rows)})[/bold]")
            for r in upcoming_rows:
                console.print(f"  #{r['id']} [{r['address'] or '?'}] {r['title']} — due {r['due_date']}")

        if not overdue_rows and not upcoming_rows:
            console.print("\n[green]No urgent tasks.[/green]")

        console.print()
        raise typer.Exit(ExitCode.SUCCESS)

    data = {
        "transactions": [t.to_dict() for t in txns],
        "overdue": [{"task_id": r["id"], "address": r["address"], "title": r["title"], "due_date": r["due_date"]} for r in overdue_rows],
        "due_this_week": [{"task_id": r["id"], "address": r["address"], "title": r["title"], "due_date": r["due_date"]} for r in upcoming_rows],
    }
    emit_success(data, settings)


def timeline(
    ctx: typer.Context,
    txn_id: int = typer.Argument(..., help="Transaction ID"),
    limit: int = typer.Option(30, "--limit", help="Max events to show"),
) -> None:
    """Chronological event log for a transaction."""
    settings = get_settings(ctx)
    conn = get_connection()

    txn = conn.execute("SELECT id FROM transactions WHERE id = ?", (txn_id,)).fetchone()
    if not txn:
        conn.close()
        emit_error(f"Transaction #{txn_id} not found", settings, code="NOT_FOUND", exit_code=ExitCode.NOT_FOUND)

    rows = conn.execute(
        "SELECT * FROM timeline_events WHERE transaction_id = ? ORDER BY created_at DESC LIMIT ?",
        (txn_id, limit),
    ).fetchall()
    conn.close()

    events = [TimelineEvent.from_row(r) for r in rows]

    if settings.format == "text":
        if not events:
            print(f"No timeline events for transaction #{txn_id}")
            raise typer.Exit(ExitCode.SUCCESS)
        console = Console()
        console.print(f"\n[bold]Timeline — Transaction #{txn_id}[/bold]\n")
        for e in events:
            console.print(f"  [dim]{e.created_at}[/dim]  [{e.event_type}]  {e.description}")
        console.print()
        raise typer.Exit(ExitCode.SUCCESS)

    emit_success([e.to_dict() for e in events], settings)
