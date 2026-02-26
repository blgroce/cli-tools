"""Transaction CRUD commands."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from ..config import VALID_STATUSES, VALID_TYPES
from ..db import get_connection, log_event
from ..main import ExitCode
from ..models import Transaction
from ..output import get_settings, emit_success, emit_error


def _parse_date(date_str: str, field_name: str) -> str:
    """Validate YYYY-MM-DD format and return the string."""
    try:
        date.fromisoformat(date_str)
        return date_str
    except ValueError:
        raise typer.BadParameter(f"Invalid date for {field_name}: {date_str}. Use YYYY-MM-DD format.")


def _calc_option_end(effective: str, days: int) -> str:
    """Calculate option period end date."""
    eff = date.fromisoformat(effective)
    return (eff + timedelta(days=days)).isoformat()


def create(
    ctx: typer.Context,
    address: str = typer.Option(..., help="Property address"),
    city: str = typer.Option(None, help="City"),
    type: str = typer.Option("buyer", help="Transaction type: buyer/seller/dual"),
    status: str = typer.Option("active", help="Status: draft/active/under_option/pending/closed/terminated"),
    effective_date: Optional[str] = typer.Option(None, "--effective-date", help="Contract effective date (YYYY-MM-DD)"),
    closing_date: Optional[str] = typer.Option(None, "--closing-date", help="Closing date (YYYY-MM-DD)"),
    option_days: Optional[int] = typer.Option(None, "--option-days", help="Option period in days"),
    option_end: Optional[str] = typer.Option(None, "--option-end", help="Option period end (YYYY-MM-DD), overrides calculation"),
    sales_price: Optional[float] = typer.Option(None, "--sales-price"),
    earnest_money: Optional[float] = typer.Option(None, "--earnest-money"),
    option_fee: Optional[float] = typer.Option(None, "--option-fee"),
    financed: bool = typer.Option(True, "--financed/--cash", help="Is the transaction financed?"),
    financing_amount: Optional[float] = typer.Option(None, "--financing-amount"),
    hoa: bool = typer.Option(False, "--hoa/--no-hoa", help="Property has HOA"),
    mud: bool = typer.Option(False, "--mud/--no-mud", help="Property is in a MUD"),
    pre_1978: bool = typer.Option(False, "--pre-1978/--post-1978", help="Built before 1978"),
    seller_disclosure_exempt: bool = typer.Option(False, "--seller-disclosure-exempt/--no-seller-disclosure-exempt"),
    new_construction: bool = typer.Option(False, "--new-construction/--not-new-construction"),
    existing_survey: Optional[bool] = typer.Option(None, "--existing-survey/--no-existing-survey"),
    county: str = typer.Option(None),
    zip_code: str = typer.Option(None, "--zip"),
    notes: str = typer.Option(None),
    generate: bool = typer.Option(True, "--generate-tasks/--no-tasks", help="Auto-generate tasks from templates"),
) -> None:
    """Create a new real estate transaction."""
    settings = get_settings(ctx)

    if type not in VALID_TYPES:
        emit_error(f"Invalid type: {type}. Must be one of: {', '.join(sorted(VALID_TYPES))}", settings, code="INVALID_INPUT", exit_code=ExitCode.INVALID_ARGS)
    if status not in VALID_STATUSES:
        emit_error(f"Invalid status: {status}. Must be one of: {', '.join(sorted(VALID_STATUSES))}", settings, code="INVALID_INPUT", exit_code=ExitCode.INVALID_ARGS)

    if effective_date:
        effective_date = _parse_date(effective_date, "effective-date")
    if closing_date:
        closing_date = _parse_date(closing_date, "closing-date")

    # Calculate option period end
    option_period_end = None
    if option_end:
        option_period_end = _parse_date(option_end, "option-end")
    elif effective_date and option_days:
        option_period_end = _calc_option_end(effective_date, option_days)

    conn = get_connection()
    cursor = conn.execute(
        """INSERT INTO transactions (
            address, city, county, zip, status, type,
            effective_date, closing_date, option_period_days, option_period_end,
            sales_price, earnest_money, option_fee,
            is_financed, financing_amount,
            has_hoa, has_mud, is_pre_1978, is_seller_disclosure_exempt,
            is_cash_offer, is_new_construction, has_existing_survey,
            notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            address, city, county, zip_code, status, type,
            effective_date, closing_date, option_days, option_period_end,
            sales_price, earnest_money, option_fee,
            int(financed), financing_amount,
            int(hoa), int(mud), int(pre_1978), int(seller_disclosure_exempt),
            int(not financed),  # is_cash_offer is inverse of financed
            int(new_construction),
            int(existing_survey) if existing_survey is not None else None,
            notes,
        ),
    )
    txn_id = cursor.lastrowid
    conn.commit()

    log_event(conn, txn_id, "created", f"Transaction created: {address}, {city or ''}")

    # Auto-generate tasks if requested
    task_count = 0
    if generate:
        from .task import _generate_tasks_for_txn
        task_count = _generate_tasks_for_txn(conn, txn_id)

    conn.close()

    row = {"id": txn_id, "address": address, "city": city, "status": status, "tasks_generated": task_count}
    text = f"Created transaction #{txn_id}: {address}"
    if city:
        text += f", {city}"
    if task_count:
        text += f" ({task_count} tasks generated)"
    emit_success(row, settings, text=text)


def get(
    ctx: typer.Context,
    id: int = typer.Argument(..., help="Transaction ID"),
) -> None:
    """Get transaction details."""
    settings = get_settings(ctx)
    conn = get_connection()
    row = conn.execute("SELECT * FROM transactions WHERE id = ?", (id,)).fetchone()
    conn.close()

    if not row:
        emit_error(f"Transaction #{id} not found", settings, code="NOT_FOUND", exit_code=ExitCode.NOT_FOUND)

    txn = Transaction.from_row(row)

    if settings.format == "text":
        console = Console()
        console.print(f"\n[bold]Transaction #{txn.id}[/bold]: {txn.address or 'No address'}")
        console.print(f"  Status: {txn.status}  |  Type: {txn.type or '-'}")
        console.print(f"  City: {txn.city or '-'}  |  County: {txn.county or '-'}  |  ZIP: {txn.zip or '-'}")
        console.print(f"  Effective: {txn.effective_date or '-'}  |  Closing: {txn.closing_date or '-'}")
        if txn.option_period_days:
            console.print(f"  Option Period: {txn.option_period_days} days (ends {txn.option_period_end or '-'})")
        console.print(f"  Price: ${txn.sales_price:,.0f}" if txn.sales_price else "  Price: -")
        console.print(f"  Earnest Money: ${txn.earnest_money:,.0f}" if txn.earnest_money else "  Earnest Money: -")
        if txn.is_financed:
            console.print(f"  Financed: ${txn.financing_amount:,.0f}" if txn.financing_amount else "  Financed: Yes")
        else:
            console.print("  Cash offer")
        flags = []
        if txn.has_hoa:
            flags.append("HOA")
        if txn.has_mud:
            flags.append("MUD")
        if txn.is_pre_1978:
            flags.append("Pre-1978")
        if txn.is_new_construction:
            flags.append("New Construction")
        if flags:
            console.print(f"  Flags: {', '.join(flags)}")
        if txn.notes:
            console.print(f"  Notes: {txn.notes}")
        console.print()
        raise typer.Exit(ExitCode.SUCCESS)

    emit_success(txn.to_dict(), settings)


def list_transactions(
    ctx: typer.Context,
    status: Optional[str] = typer.Option(None, "--status", help="Filter by status"),
    type: Optional[str] = typer.Option(None, "--type", help="Filter by type"),
    all: bool = typer.Option(False, "--all", help="Include closed/terminated"),
) -> None:
    """List transactions."""
    settings = get_settings(ctx)
    conn = get_connection()

    query = "SELECT * FROM transactions"
    params: list = []
    conditions: list[str] = []

    if status:
        if status not in VALID_STATUSES:
            conn.close()
            emit_error(f"Invalid status: {status}", settings, code="INVALID_INPUT", exit_code=ExitCode.INVALID_ARGS)
        conditions.append("status = ?")
        params.append(status)
    elif not all:
        conditions.append("status NOT IN ('closed', 'terminated')")

    if type:
        conditions.append("type = ?")
        params.append(type)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY updated_at DESC"

    rows = conn.execute(query, params).fetchall()
    conn.close()

    txns = [Transaction.from_row(r) for r in rows]

    if settings.format == "text":
        if not txns:
            print("No transactions found.")
            raise typer.Exit(ExitCode.SUCCESS)
        table = Table(title="Transactions")
        table.add_column("ID", style="bold")
        table.add_column("Address")
        table.add_column("City")
        table.add_column("Status")
        table.add_column("Type")
        table.add_column("Closing")
        for t in txns:
            table.add_row(
                str(t.id), t.address or "-", t.city or "-",
                t.status, t.type or "-", t.closing_date or "-",
            )
        Console().print(table)
        raise typer.Exit(ExitCode.SUCCESS)

    emit_success([t.to_dict() for t in txns], settings)


def update(
    ctx: typer.Context,
    id: int = typer.Argument(..., help="Transaction ID"),
    address: Optional[str] = typer.Option(None),
    city: Optional[str] = typer.Option(None),
    county: Optional[str] = typer.Option(None),
    zip_code: Optional[str] = typer.Option(None, "--zip"),
    status: Optional[str] = typer.Option(None, "--status"),
    type: Optional[str] = typer.Option(None, "--type"),
    effective_date: Optional[str] = typer.Option(None, "--effective-date"),
    closing_date: Optional[str] = typer.Option(None, "--closing-date"),
    option_days: Optional[int] = typer.Option(None, "--option-days"),
    option_end: Optional[str] = typer.Option(None, "--option-end"),
    sales_price: Optional[float] = typer.Option(None, "--sales-price"),
    earnest_money: Optional[float] = typer.Option(None, "--earnest-money"),
    option_fee: Optional[float] = typer.Option(None, "--option-fee"),
    financed: Optional[bool] = typer.Option(None, "--financed/--cash"),
    financing_amount: Optional[float] = typer.Option(None, "--financing-amount"),
    hoa: Optional[bool] = typer.Option(None, "--hoa/--no-hoa"),
    mud: Optional[bool] = typer.Option(None, "--mud/--no-mud"),
    pre_1978: Optional[bool] = typer.Option(None, "--pre-1978/--post-1978"),
    seller_disclosure_exempt: Optional[bool] = typer.Option(None, "--seller-disclosure-exempt/--no-seller-disclosure-exempt"),
    new_construction: Optional[bool] = typer.Option(None, "--new-construction/--not-new-construction"),
    existing_survey: Optional[bool] = typer.Option(None, "--existing-survey/--no-existing-survey"),
    notes: Optional[str] = typer.Option(None),
) -> None:
    """Update a transaction's fields."""
    settings = get_settings(ctx)
    conn = get_connection()

    row = conn.execute("SELECT * FROM transactions WHERE id = ?", (id,)).fetchone()
    if not row:
        conn.close()
        emit_error(f"Transaction #{id} not found", settings, code="NOT_FOUND", exit_code=ExitCode.NOT_FOUND)

    if status and status not in VALID_STATUSES:
        conn.close()
        emit_error(f"Invalid status: {status}", settings, code="INVALID_INPUT", exit_code=ExitCode.INVALID_ARGS)
    if type and type not in VALID_TYPES:
        conn.close()
        emit_error(f"Invalid type: {type}", settings, code="INVALID_INPUT", exit_code=ExitCode.INVALID_ARGS)

    updates: dict = {}
    changes: list[str] = []

    field_map = {
        "address": address, "city": city, "county": county, "zip": zip_code,
        "status": status, "type": type,
        "effective_date": effective_date, "closing_date": closing_date,
        "option_period_days": option_days,
        "sales_price": sales_price, "earnest_money": earnest_money, "option_fee": option_fee,
        "financing_amount": financing_amount, "notes": notes,
    }
    for col, val in field_map.items():
        if val is not None:
            if col in ("effective_date", "closing_date"):
                val = _parse_date(val, col)
            updates[col] = val
            changes.append(col)

    bool_map = {
        "is_financed": financed, "has_hoa": hoa, "has_mud": mud,
        "is_pre_1978": pre_1978, "is_seller_disclosure_exempt": seller_disclosure_exempt,
        "is_new_construction": new_construction, "has_existing_survey": existing_survey,
    }
    for col, val in bool_map.items():
        if val is not None:
            updates[col] = int(val)
            changes.append(col)

    # Handle cash/financed sync
    if financed is not None:
        updates["is_cash_offer"] = int(not financed)

    # Recalculate option end if dates changed
    if option_end:
        updates["option_period_end"] = _parse_date(option_end, "option-end")
        changes.append("option_period_end")
    else:
        eff = updates.get("effective_date") or row["effective_date"]
        days = updates.get("option_period_days") or row["option_period_days"]
        if eff and days and ("effective_date" in updates or "option_period_days" in updates):
            updates["option_period_end"] = _calc_option_end(eff, days)
            changes.append("option_period_end")

    if not updates:
        conn.close()
        emit_error("No fields to update", settings, code="INVALID_INPUT", exit_code=ExitCode.INVALID_ARGS)

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    conn.execute(f"UPDATE transactions SET {set_clause} WHERE id = ?", [*updates.values(), id])
    conn.commit()

    # Log status change specifically
    if status:
        old_status = row["status"]
        log_event(conn, id, "status_changed", f"Status: {old_status} -> {status}")
    if changes:
        log_event(conn, id, "updated", f"Updated: {', '.join(changes)}")

    conn.close()

    emit_success({"id": id, "updated": changes}, settings, text=f"Updated transaction #{id}: {', '.join(changes)}")


def search(
    ctx: typer.Context,
    query: str = typer.Argument(..., help="Search query (matches address, city, person name, company, email)"),
) -> None:
    """Search transactions by address, city, or people."""
    settings = get_settings(ctx)
    conn = get_connection()
    pattern = f"%{query}%"

    # Search transactions directly + via people, include match context
    rows = conn.execute(
        """SELECT DISTINCT t.* FROM transactions t
        LEFT JOIN people p ON p.transaction_id = t.id
        WHERE t.address LIKE ? OR t.city LIKE ? OR t.county LIKE ?
           OR p.name LIKE ? OR p.company LIKE ? OR p.email LIKE ?
        ORDER BY t.updated_at DESC""",
        (pattern, pattern, pattern, pattern, pattern, pattern),
    ).fetchall()

    txns = [Transaction.from_row(r) for r in rows]

    # For each transaction, find WHY it matched and who's on it
    results = []
    for txn in txns:
        match_reasons = []
        if txn.address and query.lower() in txn.address.lower():
            match_reasons.append(f"address: {txn.address}")
        if txn.city and query.lower() in txn.city.lower():
            match_reasons.append(f"city: {txn.city}")
        if txn.county and query.lower() in txn.county.lower():
            match_reasons.append(f"county: {txn.county}")

        # Get matched people
        matched_people = conn.execute(
            """SELECT name, role, company, email FROM people
            WHERE transaction_id = ? AND (name LIKE ? OR company LIKE ? OR email LIKE ?)""",
            (txn.id, pattern, pattern, pattern),
        ).fetchall()
        for p in matched_people:
            match_reasons.append(f"{p['role']}: {p['name']}" + (f" ({p['company']})" if p['company'] else ""))

        # Get all people on this transaction for context
        all_people = conn.execute(
            "SELECT name, role FROM people WHERE transaction_id = ?",
            (txn.id,),
        ).fetchall()

        results.append({
            "transaction": txn,
            "matched_on": match_reasons,
            "people": [(p["role"], p["name"]) for p in all_people],
        })

    conn.close()

    if settings.format == "text":
        if not results:
            print(f"No transactions matching '{query}'")
            raise typer.Exit(ExitCode.SUCCESS)
        table = Table(title=f"Search: '{query}'")
        table.add_column("ID", style="bold")
        table.add_column("Address")
        table.add_column("City")
        table.add_column("Status")
        table.add_column("Closing")
        table.add_column("Matched On")
        table.add_column("People")
        for r in results:
            t = r["transaction"]
            matched = "; ".join(r["matched_on"]) if r["matched_on"] else "-"
            people_str = ", ".join(f"{role}: {name}" for role, name in r["people"]) if r["people"] else "-"
            table.add_row(
                str(t.id), t.address or "-", t.city or "-",
                t.status, t.closing_date or "-", matched, people_str,
            )
        Console().print(table)
        raise typer.Exit(ExitCode.SUCCESS)

    emit_success([
        {
            **r["transaction"].to_dict(),
            "matched_on": r["matched_on"],
            "people": [{"role": role, "name": name} for role, name in r["people"]],
        }
        for r in results
    ], settings)
