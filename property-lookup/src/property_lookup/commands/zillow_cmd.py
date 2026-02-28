"""Zillow command — look up property details from Zillow via Apify."""
from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text

from ..output import get_settings, emit_success, emit_error
from ..main import ExitCode


def zillow(
    ctx: typer.Context,
    address: Optional[str] = typer.Argument(
        None,
        help="Property address to search Zillow for.",
    ),
    zpid: Optional[str] = typer.Option(
        None,
        "--zpid",
        help="Zillow Property ID (skips address search).",
    ),
    url: Optional[str] = typer.Option(
        None,
        "--url",
        help="Zillow homedetails URL (skips address search).",
    ),
) -> None:
    """Look up property details from Zillow."""
    settings = get_settings(ctx)

    if not any([address, zpid, url]):
        emit_error(
            "Provide an address, --zpid, or --url.",
            settings,
            code="MISSING_INPUT",
            exit_code=ExitCode.INVALID_ARGS,
        )

    from ..zillow import lookup_by_zpid, lookup_by_url, search_by_address, ZillowError

    try:
        if zpid:
            result = lookup_by_zpid(zpid)
        elif url:
            result = lookup_by_url(url)
        else:
            result = search_by_address(address)
    except ZillowError as e:
        emit_error(str(e), settings, code="ZILLOW_ERROR", exit_code=ExitCode.EXTERNAL_FAILURE)
    except Exception as e:
        emit_error(
            f"Zillow lookup failed: {e}",
            settings,
            code="EXTERNAL_FAILURE",
            exit_code=ExitCode.EXTERNAL_FAILURE,
        )

    # Text output
    if settings.format == "text":
        _render_text(result)
        raise typer.Exit(ExitCode.SUCCESS)

    emit_success(result, settings)


def _render_text(data: dict) -> None:
    """Render Zillow data as Rich-formatted text."""
    console = Console()
    prop = data.get("property", {})
    details = data.get("details", {})
    fin = data.get("financials", {})
    agent = data.get("agent", {})

    # Header
    addr = prop.get("address", "Unknown")
    city_state = f"{prop.get('city', '')}, {prop.get('state', '')} {prop.get('zip', '')}"
    price = fin.get("price")
    price_str = f"${price:,.0f}" if price else "N/A"

    console.print(Panel(
        f"[bold]{addr}[/bold]\n{city_state}\n\n"
        f"[bold green]{price_str}[/bold green]"
        f"  |  Zestimate: ${fin.get('zestimate', 0):,.0f}" if fin.get("zestimate") else "",
        title="Property",
        border_style="blue",
    ))

    # Details table
    detail_items = [
        ("Beds", details.get("beds")),
        ("Baths", details.get("baths")),
        ("SqFt", f"{details['sqft']:,}" if details.get("sqft") else None),
        ("Lot Size", f"{details['lotSize']:,} sqft" if details.get("lotSize") else None),
        ("Year Built", details.get("yearBuilt")),
        ("Type", details.get("homeType")),
        ("Status", details.get("homeStatus")),
        ("County", prop.get("county")),
        ("Subdivision", prop.get("subdivision")),
        ("Parcel ID", prop.get("parcelId")),
    ]

    table = Table(title="Details", show_header=False, border_style="dim")
    table.add_column("Field", style="bold")
    table.add_column("Value")
    for label, val in detail_items:
        if val is not None:
            table.add_row(label, str(val))
    console.print(table)

    # Financials
    fin_items = [
        ("HOA", f"${fin['hoaFeeMonthly']}/mo" if fin.get("hoaFeeMonthly") else "None"),
        ("Tax Rate", f"{fin['taxRate']}%" if fin.get("taxRate") else "N/A"),
        ("Tax Annual", f"${fin['taxAnnualAmount']:,.0f}" if fin.get("taxAnnualAmount") else "N/A"),
        ("Insurance", f"${fin['annualInsurance']:,.0f}/yr" if fin.get("annualInsurance") else "N/A"),
        ("Rent Zest.", f"${fin['rentZestimate']:,.0f}/mo" if fin.get("rentZestimate") else "N/A"),
    ]

    fin_table = Table(title="Financials", show_header=False, border_style="dim")
    fin_table.add_column("Field", style="bold")
    fin_table.add_column("Value")
    for label, val in fin_items:
        fin_table.add_row(label, val)
    console.print(fin_table)

    # Agent
    if agent.get("agentName"):
        agent_text = f"[bold]{agent['agentName']}[/bold]"
        if agent.get("agentPhone"):
            agent_text += f"  {agent['agentPhone']}"
        if agent.get("agentLicense"):
            agent_text += f"  ({agent['agentLicense']})"
        if agent.get("brokerName"):
            agent_text += f"\n{agent['brokerName']}"
        if agent.get("mlsId"):
            agent_text += f"  |  MLS# {agent['mlsId']}"
        console.print(Panel(agent_text, title="Listing Agent", border_style="dim"))

    # Schools
    schools = data.get("schools", [])
    if schools:
        sch_table = Table(title="Schools")
        sch_table.add_column("Name")
        sch_table.add_column("Type")
        sch_table.add_column("Rating", justify="center")
        sch_table.add_column("Distance")
        for s in schools:
            rating = s.get("rating")
            rating_style = "green" if rating and rating >= 7 else "yellow" if rating and rating >= 5 else "red"
            sch_table.add_row(
                s.get("name", ""),
                s.get("type", ""),
                f"[{rating_style}]{rating}/10[/{rating_style}]" if rating else "N/A",
                f"{s.get('distance', '')} mi" if s.get("distance") else "",
            )
        console.print(sch_table)

    # Description (truncated)
    desc = details.get("description", "")
    if desc:
        if len(desc) > 300:
            desc = desc[:300] + "..."
        console.print(Panel(desc, title="Description", border_style="dim"))

    # URL
    if data.get("url"):
        console.print(f"\n[dim]Zillow: {data['url']}[/dim]")
