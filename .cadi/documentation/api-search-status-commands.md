# Search and Status Commands

> Cross-entity search and CRM dashboard summary commands

## Location

| Type | Path |
|------|------|
| API | `crm/src/crm/commands/search.py, crm/src/crm/commands/status.py` |

## How It Works

- Search: takes query arg, uses SQL LIKE across companies (name/industry/notes), contacts (name/email/role/tags/notes), interactions (summary/followup_note), deals (title/notes)
- Status: no args, queries active_deals count+value, pipeline_deals count+value, overdue_followups count, upcoming_followups count (7 days), recent_interactions (last 5), company_counts by status
- Both registered as app.command() on main app (not sub-typer groups)
- Both support --format text with Rich tables/panels
- Search text mode: grouped Rich tables per entity type, 'No results' for empty
- Status text mode: Rich Panel titled 'CRM Dashboard' with formatted sections

## Usage

```bash
crm search <query>\ncrm --format text search <query>\ncrm status\ncrm --format text status
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
