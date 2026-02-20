# Followup Commands

> crm followups command group for listing and completing follow-ups on interactions

## Location

| Type | Path |
|------|------|
| API | `crm/src/crm/commands/followup.py` |

## How It Works

- Default list: shows interactions with followup_date <= today (due + overdue)
- --week flag: shows followup_date <= today + 7 days
- --all flag: shows all where followup_date IS NOT NULL
- JSON output includes id, contact_name, company_name, type, summary, followup_date, followup_note, days_overdue
- Text format renders Rich table with color coding (red=overdue, yellow=today, green=upcoming)
- done subcommand: clears followup_date and followup_note by interaction ID
- Returns NOT_FOUND (exit 3) if interaction ID doesn't exist
- Uses invoke_without_command=True on callback so bare 'crm followups' triggers list

## Usage

```bash
crm followups              # due today + overdue\ncrm followups --week       # next 7 days\ncrm followups --all        # all pending\ncrm followups done <id>    # mark complete
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
