# CLI Tools
The purpose of this entire project is to build cli tools that other agents will call.

## RULES
- Keep the scope simple but expandable.
- After planning or creating, always ask yourself "Can I get the same outcome in a simpler way?"

---

## Language & Framework
- **Python** with **Typer** (or Click) for CLI framework
- Typer is preferred - cleaner syntax, auto-generates `--help`

## Installation
- Each tool is its own package with its own `pyproject.toml`
- Installable via `pip install .` or `pipx install .`
- Tools are standalone - install only what you need on each machine/container

## Output Rules
| Rule | Rationale |
|------|-----------|
| JSON to stdout by default | Agents parse it reliably |
| Errors to stderr | Keeps stdout clean for piping |
| No interactive prompts | Agents can't respond to "Are you sure?" |
| `--format text` option for humans | Optional override |

## Standard Flags (all tools)
```
--help, -h       Show help
--version        Show version
--quiet, -q      Suppress non-error output
--format         json (default) | text
```

## Exit Codes
```
0 = Success
1 = General error
2 = Invalid arguments
3 = Resource not found
4 = External failure (API, network)
```

## Error Output Format
```json
{"error": true, "code": "INVALID_INPUT", "message": "Expected file path"}
```

## Success Output Format
```json
{"success": true, "data": { ... }}
```

## Project Structure
Each tool is independently installable. Tools may be installed alone on a container without the others.

```
cli-tools/
├── shared/                     # Common utilities (optional dependency)
│   ├── pyproject.toml
│   └── src/
│       └── cli_shared/
│           ├── __init__.py
│           ├── output.py       # JSON output helpers
│           └── errors.py       # Standard error handling
│
├── toolname/                   # Each tool is its own package
│   ├── pyproject.toml          # Independent install: pip install .
│   ├── src/
│   │   └── toolname/
│   │       ├── __init__.py
│   │       └── main.py
│   └── tests/
│
└── anothertool/
    ├── pyproject.toml
    ├── src/
    │   └── anothertool/
    │       ├── __init__.py
    │       └── main.py
    └── tests/
```

Example install:
```bash
cd toolname && pip install .
# or from git
pip install git+https://github.com/user/cli-tools.git#subdirectory=toolname
```

Tools can optionally depend on `cli-shared` for common utilities, or inline what they need to stay fully standalone.