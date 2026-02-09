# CLI Tools Standards

> Guidelines and conventions for building CLI tools in this project

## Location

| Type | Path |
|------|------|
| Config | `CLAUDE.md` |

## How It Works

- All tools use Python with Typer framework
- JSON output to stdout by default, errors to stderr
- Standard flags: --help, --version, --quiet, --format
- Exit codes: 0=success, 1=error, 2=invalid args, 3=not found, 4=external failure
- Each tool is independently installable with its own pyproject.toml
- No interactive prompts (agents cannot respond to them)

## Usage

```bash
# Create a new tool
mkdir -p newtool/src/newtool
# Add pyproject.toml, __init__.py, main.py
# Install: cd newtool && pip install .

# Output format
{"success": true, "data": {...}}
{"error": true, "code": "NOT_FOUND", "message": "..."}
```

## Related Docs

- [CLI Shared Library](./infra-cli-shared-library.md)

---
*Created: 2026-02-04 | Task: #0*
