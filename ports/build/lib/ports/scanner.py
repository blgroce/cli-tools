"""Port scanning logic — shared by CLI and TUI."""

import os
import re
import signal
import subprocess


def get_listeners() -> list[dict]:
    """Parse `ss -tlnp` for listening TCP ports."""
    result = subprocess.run(
        ["ss", "-tlnp"],
        capture_output=True, text=True,
    )
    entries = []
    for line in result.stdout.strip().splitlines()[1:]:
        parts = line.split()
        if len(parts) < 5:
            continue

        local_addr = parts[3]
        port = local_addr.rsplit(":", 1)[-1] if ":" in local_addr else None
        if not port or not port.isdigit():
            continue

        proc_info = ""
        pid = None
        for p in parts:
            if p.startswith("users:"):
                proc_info = p
                break

        proc_name = ""
        if proc_info:
            name_match = re.search(r'\("([^"]+)"', proc_info)
            pid_match = re.search(r"pid=(\d+)", proc_info)
            if name_match:
                proc_name = name_match.group(1)
            if pid_match:
                pid = int(pid_match.group(1))

        cmdline = ""
        if pid:
            try:
                with open(f"/proc/{pid}/cmdline") as f:
                    cmdline = f.read().replace("\x00", " ").strip()
            except (FileNotFoundError, PermissionError):
                pass

        # Try to extract a meaningful working directory / project name
        cwd = ""
        if pid:
            try:
                cwd = os.readlink(f"/proc/{pid}/cwd")
            except (FileNotFoundError, PermissionError):
                pass

        entries.append({
            "port": int(port),
            "pid": pid,
            "process": proc_name,
            "cmdline": cmdline,
            "address": local_addr,
            "cwd": cwd,
        })

    # Deduplicate by port (ss can show both IPv4 and IPv6)
    seen = {}
    for e in entries:
        if e["port"] not in seen or e["pid"]:
            seen[e["port"]] = e
    return sorted(seen.values(), key=lambda e: e["port"])


def kill_port(pid: int, force: bool = False) -> str:
    """Kill a process. Returns a status message."""
    sig = signal.SIGKILL if force else signal.SIGTERM
    try:
        os.kill(pid, sig)
        return "killed"
    except PermissionError:
        return "permission_denied"
    except ProcessLookupError:
        return "already_gone"
