# Search and Status Commands

> Cross-entity search and CRM dashboard summary commands

## Location

| Type | Path |
|------|------|
| API | `crm/src/crm/commands/search.py, crm/src/crm/commands/status.py` |

## How It Works

- search: Accepts query arg, searches across companies/contacts/interactions/deals using SQL LIKE on text columns
- search returns grouped results by entity type with Rich tables in text mode
- status: No args, queries active deals, pipeline deals, overdue/upcoming followups, recent interactions, company counts
- status displays a Rich panel dashboard in text mode
- Both registered as top-level commands via app.command() in main.py

## Usage

```bash
crm search <query>\ncrm status\ncrm --format text search <query>\ncrm --format text status
```

## Related Docs

- [Interaction Logging Commands](./api-log-commands.md)
- [Company Commands](./api-company-commands.md)
- [describe-image Auth Subcommand](./api-describe-image-auth.md)
- [Deal Commands (add, list, show, move, rm)](./api-deal-commands.md)
- [describe-image describe Command](./api-describe-image-describe.md)
- [Contact Commands](./api-contact-commands.md)
- [CRM Interaction Logging Commands](./api-crm-log-commands.md)
- [Followup Commands](./api-followup-commands.md)
- [describe-image CLI - Core Structure](./api-describe-image-core.md)

---
*Created: 2026-02-20 | Task: #13*
