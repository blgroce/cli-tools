# Followup Commands

> View and manage follow-up reminders attached to interactions

## Location

| Type | Path |
|------|------|
| API | `crm/src/crm/commands/followup.py` |

## How It Works

- Default: lists interactions with followup_date <= today (due + overdue)
- --week flag: shows follow-ups due within next 7 days
- --all flag: shows all pending follow-ups (non-null followup_date)
- done subcommand: clears followup_date and followup_note by interaction ID
- JSON output includes days_overdue calculation
- Text output uses rich table with color coding (red=overdue, yellow=today, green=upcoming)
- Returns NOT_FOUND (exit 3) for invalid interaction IDs

## Usage

```bash
crm followups                  # due today + overdue
crm followups --week           # next 7 days
crm followups --all            # all pending
crm followups done <id>        # mark follow-up complete
```

## Related Docs

- [Interaction Logging Commands](./api-log-commands.md)
- [Company Commands](./api-company-commands.md)
- [describe-image Auth Subcommand](./api-describe-image-auth.md)
- [Deal Commands (add, list, show, move, rm)](./api-deal-commands.md)
- [describe-image describe Command](./api-describe-image-describe.md)
- [Contact Commands](./api-contact-commands.md)
- [CRM Interaction Logging Commands](./api-crm-log-commands.md)
- [describe-image CLI - Core Structure](./api-describe-image-core.md)

---
*Created: 2026-02-20 | Task: #12*
