"""Port manager — see what's listening and kill it."""

import typer
from rich.console import Console
from rich.table import Table

from ports.scanner import get_listeners, kill_port

app = typer.Typer(help="Manage active ports on your machine.")
console = Console()


@app.callback(invoke_without_command=True)
def list_ports(
    ctx: typer.Context,
    interactive: bool = typer.Option(False, "--ui", "-u", help="Launch interactive TUI"),
):
    """Show all listening ports (default command)."""
    if ctx.invoked_subcommand is not None:
        return

    if interactive:
        from ports.tui import run_tui
        run_tui()
        return

    entries = get_listeners()
    if not entries:
        console.print("[dim]No listening ports found.[/dim]")
        raise typer.Exit()

    table = Table(title="Listening Ports", show_lines=False)
    table.add_column("Port", style="cyan bold", justify="right")
    table.add_column("PID", style="yellow", justify="right")
    table.add_column("Process", style="green")
    table.add_column("Command", style="dim", max_width=80, overflow="ellipsis")

    for e in entries:
        table.add_row(
            str(e["port"]),
            str(e["pid"] or "—"),
            e["process"] or "—",
            e["cmdline"] or "—",
        )

    console.print(table)


@app.command()
def ui():
    """Launch interactive TUI."""
    from ports.tui import run_tui
    run_tui()


@app.command()
def kill(
    port: int = typer.Argument(help="Port number to kill"),
    force: bool = typer.Option(False, "--force", "-f", help="Send SIGKILL instead of SIGTERM"),
):
    """Kill the process listening on a port."""
    entries = get_listeners()
    match = [e for e in entries if e["port"] == port]

    if not match:
        console.print(f"[red]Nothing listening on port {port}.[/red]")
        raise typer.Exit(1)

    entry = match[0]
    if not entry["pid"]:
        console.print(f"[red]Can't determine PID for port {port}. Try with sudo.[/red]")
        raise typer.Exit(1)

    pid = entry["pid"]
    sig_name = "SIGKILL" if force else "SIGTERM"
    console.print(
        f"Killing [cyan]:{port}[/cyan] → "
        f"PID [yellow]{pid}[/yellow] ([green]{entry['process']}[/green]) "
        f"with {sig_name}"
    )

    result = kill_port(pid, force=force)
    if result == "killed":
        console.print("[green]Done.[/green]")
    elif result == "permission_denied":
        console.print(f"[red]Permission denied. Try: sudo ports kill {port}[/red]")
        raise typer.Exit(1)
    elif result == "already_gone":
        console.print("[yellow]Process already gone.[/yellow]")


@app.command()
def killall(
    force: bool = typer.Option(False, "--force", "-f", help="Send SIGKILL instead of SIGTERM"),
    above: int = typer.Option(1024, "--above", help="Only kill ports above this number"),
):
    """Kill all dev server ports (above 1024 by default)."""
    entries = [e for e in get_listeners() if e["port"] > above and e["pid"]]

    if not entries:
        console.print(f"[dim]No killable ports above {above}.[/dim]")
        raise typer.Exit()

    table = Table(title=f"Will kill {len(entries)} process(es)", show_lines=False)
    table.add_column("Port", style="cyan bold", justify="right")
    table.add_column("PID", style="yellow", justify="right")
    table.add_column("Process", style="green")
    for e in entries:
        table.add_row(str(e["port"]), str(e["pid"]), e["process"] or "—")
    console.print(table)

    if not typer.confirm("Proceed?"):
        raise typer.Abort()

    for e in entries:
        result = kill_port(e["pid"], force=force)
        if result == "killed":
            console.print(f"  [green]✓[/green] :{e['port']} (PID {e['pid']})")
        elif result == "permission_denied":
            console.print(f"  [red]✗[/red] :{e['port']} — permission denied")
        elif result == "already_gone":
            console.print(f"  [yellow]~[/yellow] :{e['port']} — already gone")

    console.print("[green]Done.[/green]")
