"""Districts command — look up MUD/drainage/water districts for a location."""
from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from ..output import get_settings, emit_success, emit_error
from ..main import ExitCode


def districts(
    ctx: typer.Context,
    address: Optional[str] = typer.Argument(
        None,
        help="Property address to look up (geocoded to lat/lon).",
    ),
    lat: Optional[float] = typer.Option(
        None,
        "--lat",
        help="Latitude (use with --lon instead of address).",
    ),
    lon: Optional[float] = typer.Option(
        None,
        "--lon",
        help="Longitude (use with --lat instead of address).",
    ),
) -> None:
    """Look up water districts (MUD, drainage, etc.) for a Texas property."""
    settings = get_settings(ctx)

    # Resolve coordinates
    if lat is not None and lon is not None:
        pass  # use provided coords
    elif address:
        from ..geocode import geocode_address
        coords = geocode_address(address)
        if not coords:
            emit_error(
                f"Could not geocode address: {address}",
                settings,
                code="GEOCODE_FAILED",
                exit_code=ExitCode.NOT_FOUND,
            )
        lat, lon = coords
    else:
        emit_error(
            "Provide an address or --lat/--lon coordinates.",
            settings,
            code="MISSING_INPUT",
            exit_code=ExitCode.INVALID_ARGS,
        )

    # Query districts
    from ..districts import lookup_districts

    try:
        result = lookup_districts(lat, lon)
    except Exception as e:
        emit_error(
            f"District lookup failed: {e}",
            settings,
            code="EXTERNAL_FAILURE",
            exit_code=ExitCode.EXTERNAL_FAILURE,
        )

    # Text output
    if settings.format == "text":
        console = Console()

        if address:
            console.print(f"\n[bold]Districts for:[/bold] {address}")
        console.print(f"[dim]Coordinates: {lat:.6f}, {lon:.6f}[/dim]\n")

        if result["mud"]:
            console.print(Panel(
                f"[bold green]{result['mud']}[/bold green]",
                title="MUD District",
                border_style="green",
            ))

        districts_list = result["districts"]
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
        else:
            console.print("[dim]No water districts found at this location.[/dim]")

        raise typer.Exit(ExitCode.SUCCESS)

    emit_success(result, settings)
