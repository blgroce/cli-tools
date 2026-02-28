"""Lookup command — combined Zillow + districts in one call."""
from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from ..output import get_settings, emit_success, emit_error
from ..main import ExitCode


def lookup(
    ctx: typer.Context,
    address: Optional[str] = typer.Argument(
        None,
        help="Property address to look up.",
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
    skip_zillow: bool = typer.Option(
        False,
        "--skip-zillow",
        help="Skip Zillow lookup, only fetch district data.",
    ),
    skip_districts: bool = typer.Option(
        False,
        "--skip-districts",
        help="Skip district lookup, only fetch Zillow data.",
    ),
) -> None:
    """Combined property lookup: Zillow details + water districts."""
    settings = get_settings(ctx)

    if not any([address, zpid, url]):
        emit_error(
            "Provide an address, --zpid, or --url.",
            settings,
            code="MISSING_INPUT",
            exit_code=ExitCode.INVALID_ARGS,
        )

    result = {"zillow": None, "districts": None}
    lat, lon = None, None
    zillow_error = None
    district_error = None

    # Step 1: Zillow lookup
    if not skip_zillow:
        from ..zillow import lookup_by_zpid, lookup_by_url, search_by_address, ZillowError
        try:
            if zpid:
                zillow_data = lookup_by_zpid(zpid)
            elif url:
                zillow_data = lookup_by_url(url)
            else:
                zillow_data = search_by_address(address)

            result["zillow"] = zillow_data
            # Extract coords for district lookup
            prop = zillow_data.get("property", {})
            lat = prop.get("latitude")
            lon = prop.get("longitude")
        except ZillowError as e:
            zillow_error = str(e)
        except Exception as e:
            zillow_error = f"Zillow lookup failed: {e}"

    # Step 2: District lookup
    if not skip_districts:
        # Get coordinates if we don't have them from Zillow
        if lat is None or lon is None:
            if address:
                from ..geocode import geocode_address
                coords = geocode_address(address)
                if coords:
                    lat, lon = coords

        if lat is not None and lon is not None:
            from ..districts import lookup_districts
            try:
                result["districts"] = lookup_districts(lat, lon)
            except Exception as e:
                district_error = f"District lookup failed: {e}"
        elif not zillow_error:
            district_error = "No coordinates available for district lookup."

    # If both failed, error out
    if zillow_error and (district_error or skip_districts):
        emit_error(
            zillow_error,
            settings,
            code="LOOKUP_FAILED",
            exit_code=ExitCode.EXTERNAL_FAILURE,
        )
    if district_error and (zillow_error or skip_zillow):
        emit_error(
            district_error,
            settings,
            code="LOOKUP_FAILED",
            exit_code=ExitCode.EXTERNAL_FAILURE,
        )

    # Add any non-fatal errors
    errors = []
    if zillow_error:
        errors.append({"source": "zillow", "message": zillow_error})
    if district_error:
        errors.append({"source": "districts", "message": district_error})
    if errors:
        result["errors"] = errors

    # Text output
    if settings.format == "text":
        _render_combined_text(result, address)
        raise typer.Exit(ExitCode.SUCCESS)

    emit_success(result, settings)


def _render_combined_text(data: dict, address: str | None) -> None:
    """Render combined Zillow + districts as Rich text."""
    console = Console()

    # Zillow section
    zillow = data.get("zillow")
    if zillow:
        from .zillow_cmd import _render_text
        _render_text(zillow)
    elif data.get("errors"):
        for err in data["errors"]:
            if err["source"] == "zillow":
                console.print(f"\n[yellow]Zillow: {err['message']}[/yellow]")

    # Districts section
    districts_data = data.get("districts")
    if districts_data:
        console.print()  # spacing

        if districts_data.get("mud"):
            console.print(Panel(
                f"[bold green]{districts_data['mud']}[/bold green]",
                title="MUD District",
                border_style="green",
            ))

        districts_list = districts_data.get("districts", [])
        if districts_list:
            table = Table(title="Water Districts")
            table.add_column("Name", style="bold")
            table.add_column("Type")
            table.add_column("Status")
            table.add_column("County")

            for d in districts_list:
                status_style = "green" if d["isActive"] else "dim"
                name_style = "bold green" if d["type"] == "Municipal Utility District" else ""
                table.add_row(
                    f"[{name_style}]{d['name']}[/{name_style}]" if name_style else d["name"],
                    d["type"],
                    f"[{status_style}]{'Active' if d['isActive'] else 'Inactive'}[/{status_style}]",
                    d.get("county") or "",
                )
            console.print(table)
    elif data.get("errors"):
        for err in data["errors"]:
            if err["source"] == "districts":
                console.print(f"\n[yellow]Districts: {err['message']}[/yellow]")

    # Summary line
    console.print()
    parts = []
    if zillow:
        fin = zillow.get("financials", {})
        hoa = fin.get("hoaFeeMonthly")
        parts.append(f"HOA: {'$' + str(hoa) + '/mo' if hoa else 'None'}")
    if districts_data:
        parts.append(f"MUD: {districts_data.get('mud') or 'None'}")
    if parts:
        console.print(f"[bold]Summary:[/bold] {' | '.join(parts)}")
