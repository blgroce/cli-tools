# CRM Foundation Modules

> Core modules (db.py, models.py, output.py) that all CRM commands depend on

## Location

| Type | Path |
|------|------|
| Service | `crm/src/crm/` |

## How It Works

- db.py: get_db_path() returns ~/.local/share/crm/crm.db, get_connection() with WAL+FK, init_db() creates 4 tables + triggers
- models.py: Company, Contact, Interaction, Deal dataclasses with from_row() and to_dict()
- output.py: OutputSettings dataclass, get_settings(ctx), emit_success(), emit_error()
- main.py: --format (json/text) and --quiet global options stored in ctx.obj, init_db() on startup

## Usage

```python
from crm.db import get_connection, init_db\nfrom crm.models import Company, Contact, Interaction, Deal\nfrom crm.output import get_settings, emit_success, emit_error
```

## Related Docs

- None yet

---
*Created: 2026-02-20 | Task: #7*
