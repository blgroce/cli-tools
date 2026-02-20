# Interaction Logging Commands

> CLI commands for logging calls, emails, meetings, and notes with contacts

## Location

| Type | Path |
|------|------|
| Script | `crm/src/crm/commands/log.py` |

## How It Works

- Four subcommands: call, email, meeting, note - all share same structure
- Contact name resolved from contacts table; auto-resolves company_id
- Followup date parsing: Nd (days), Nw (weeks), or YYYY-MM-DD
- Date validation rejects non-YYYY-MM-DD formats
- Uses shared _log_interaction() helper for DRY implementation
- Success output includes contact_name and company_name fields
- Text format shows confirmation message with follow-up details

## Usage

```bash
crm log call "Jane Doe" --summary "Discussed Q2" --followup 7d --followup-note "Send proposal"\ncrm log email "Jane Doe" --summary "Sent invoice #1234"\ncrm log meeting "Jane Doe" --summary "Quarterly review" --date 2026-02-15\ncrm log note "Jane Doe" --summary "Prefers morning meetings"
```

## Related Docs

- [Company Commands](./api-company-commands.md)
- [describe-image Auth Subcommand](./api-describe-image-auth.md)
- [describe-image describe Command](./api-describe-image-describe.md)
- [Contact Commands](./api-contact-commands.md)
- [describe-image CLI - Core Structure](./api-describe-image-core.md)

---
*Created: 2026-02-20 | Task: #10*
