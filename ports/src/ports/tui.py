"""Interactive TUI for port management."""

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, Horizontal
from textual.widgets import DataTable, Header, Footer, Static
from textual.screen import ModalScreen

from ports.scanner import get_listeners, kill_port


class ConfirmKillScreen(ModalScreen[bool]):
    """Modal confirmation before killing a port."""

    BINDINGS = [
        Binding("y", "confirm", "Yes"),
        Binding("n", "cancel", "No"),
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, port: int, process: str, pid: int) -> None:
        super().__init__()
        self.port = port
        self.process = process
        self.pid = pid

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static(
                f"\n  Kill port [bold cyan]{self.port}[/]?"
                f"\n  Process: [green]{self.process}[/] (PID [yellow]{self.pid}[/])"
                f"\n\n  [dim]y = kill  /  n = cancel[/]\n",
                id="confirm-dialog",
            ),
            id="confirm-container",
        )

    def action_confirm(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)


class ConfirmKillAllScreen(ModalScreen[bool]):
    """Modal confirmation before killing all dev ports."""

    BINDINGS = [
        Binding("y", "confirm", "Yes"),
        Binding("n", "cancel", "No"),
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, count: int) -> None:
        super().__init__()
        self.count = count

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static(
                f"\n  Kill [bold red]{self.count}[/] dev server port(s) (above 1024)?"
                f"\n\n  [dim]y = kill all  /  n = cancel[/]\n",
                id="confirm-dialog",
            ),
            id="confirm-container",
        )

    def action_confirm(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)


class PortsApp(App):
    """Interactive port manager."""

    CSS = """
    Screen {
        background: $surface;
    }

    #status-bar {
        dock: bottom;
        height: 1;
        padding: 0 1;
        background: $primary-background;
        color: $text-muted;
    }

    #confirm-container {
        align: center middle;
        width: 100%;
        height: 100%;
    }

    #confirm-dialog {
        width: 50;
        height: auto;
        border: thick $accent;
        background: $surface;
        padding: 1;
    }

    DataTable {
        height: 1fr;
    }

    DataTable > .datatable--cursor {
        background: $accent 40%;
    }
    """

    TITLE = "ports"
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("k", "kill_selected", "Kill"),
        Binding("K", "kill_all_dev", "Kill All Dev"),
        Binding("f", "force_kill", "Force Kill"),
        Binding("r", "refresh", "Refresh"),
    ]

    def __init__(self):
        super().__init__()
        self.status_message = ""

    def compose(self) -> ComposeResult:
        yield Header()
        yield DataTable(id="ports-table")
        yield Static("", id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        self._build_table()

    def _build_table(self) -> None:
        table = self.query_one("#ports-table", DataTable)
        table.clear(columns=True)
        table.cursor_type = "row"

        table.add_column("Port", key="port")
        table.add_column("PID", key="pid")
        table.add_column("Process", key="process")
        table.add_column("Directory", key="cwd")
        table.add_column("Command", key="cmd")

        entries = get_listeners()
        for e in entries:
            # Shorten the cwd for display
            cwd = e["cwd"]
            home = "/home/"
            if home in cwd:
                cwd = "~/" + cwd.split(home, 1)[1].split("/", 1)[-1]

            # Shorten cmdline — strip the binary path, keep args
            cmd = e["cmdline"]
            if cmd and "/" in cmd.split(" ")[0]:
                parts = cmd.split(" ", 1)
                binary = parts[0].rsplit("/", 1)[-1]
                cmd = binary + (" " + parts[1] if len(parts) > 1 else "")

            table.add_row(
                str(e["port"]),
                str(e["pid"] or "—"),
                e["process"] or "—",
                cwd or "—",
                cmd or "—",
                key=str(e["port"]),
            )

        self._set_status(f"{len(entries)} port(s) listening")

    def _set_status(self, msg: str) -> None:
        self.status_message = msg
        self.query_one("#status-bar", Static).update(msg)

    def _get_selected_entry(self) -> dict | None:
        table = self.query_one("#ports-table", DataTable)
        if table.row_count == 0:
            return None
        row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
        port = int(row_key.value)
        entries = get_listeners()
        for e in entries:
            if e["port"] == port:
                return e
        return None

    def _do_kill(self, entry: dict, force: bool = False) -> None:
        if not entry or not entry["pid"]:
            self._set_status("No killable process on this port")
            return

        result = kill_port(entry["pid"], force=force)
        mode = "SIGKILL" if force else "SIGTERM"
        if result == "killed":
            self._set_status(f"Killed :{entry['port']} ({mode})")
        elif result == "permission_denied":
            self._set_status(f"Permission denied for :{entry['port']} — try sudo")
        elif result == "already_gone":
            self._set_status(f":{entry['port']} already gone")

        self._build_table()

    def action_refresh(self) -> None:
        self._build_table()
        self._set_status("Refreshed")

    def action_kill_selected(self) -> None:
        entry = self._get_selected_entry()
        if not entry or not entry["pid"]:
            self._set_status("No killable process selected")
            return

        def on_confirm(confirmed: bool) -> None:
            if confirmed:
                self._do_kill(entry)

        self.push_screen(
            ConfirmKillScreen(entry["port"], entry["process"], entry["pid"]),
            on_confirm,
        )

    def action_force_kill(self) -> None:
        entry = self._get_selected_entry()
        if not entry or not entry["pid"]:
            self._set_status("No killable process selected")
            return

        def on_confirm(confirmed: bool) -> None:
            if confirmed:
                self._do_kill(entry, force=True)

        self.push_screen(
            ConfirmKillScreen(entry["port"], entry["process"], entry["pid"]),
            on_confirm,
        )

    def action_kill_all_dev(self) -> None:
        entries = [e for e in get_listeners() if e["port"] > 1024 and e["pid"]]
        if not entries:
            self._set_status("No dev ports to kill")
            return

        def on_confirm(confirmed: bool) -> None:
            if confirmed:
                killed = 0
                for e in entries:
                    if kill_port(e["pid"]) == "killed":
                        killed += 1
                self._set_status(f"Killed {killed}/{len(entries)} dev port(s)")
                self._build_table()

        self.push_screen(ConfirmKillAllScreen(len(entries)), on_confirm)


def run_tui():
    app = PortsApp()
    app.run()
