# CLI Shared Library

> Common utilities for CLI tools - output formatting, error handling, and exit codes

## Location

| Type | Path |
|------|------|
| Script | `shared/src/cli_shared/` |

## How It Works

- Provides standard JSON output format (success/error)
- Defines exit codes: 0=success, 1=general, 2=invalid args, 3=not found, 4=external failure
- Exception classes map to exit codes automatically
- Tools can depend on cli-shared or copy what they need for standalone deployment

## Usage

```python
from cli_shared import success, NotFoundError, handle_error

try:
    result = do_something()
    success({"result": result})
except NotFoundError as e:
    handle_error(e)
```

## Related Docs

- None yet

---
*Created: 2026-02-04 | Task: #0*
