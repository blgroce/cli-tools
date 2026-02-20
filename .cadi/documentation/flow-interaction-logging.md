# Interaction Logging Commands

> crm log subcommands for recording calls, emails, meetings, and notes with contacts

## Location

| Type | Path |
|------|------|
| Script | `crm/src/crm/commands/log.py` |

## How It Works

- 4 subcommands (call, email, meeting, note) share _log_interaction() logic
- Resolves contact by name, auto-resolves company_id from contact's company
- Parses followup shorthand: Nd (days), Nw (weeks), YYYY-MM-DD exact date
- Inserts into interactions table with all fields
- Emits success JSON with contact_name and company_name included
- Text format shows confirmation with followup date if set
- Error handling: NOT_FOUND (exit 3) for missing contact, INVALID_INPUT (exit 2) for bad followup format

## Usage

```bash
crm log call "Jane Doe" --summary "Discussed Q2 timeline" --followup 7d --followup-note "Send proposal"\ncrm log email "Jane Doe" --summary "Sent invoice #1234"\ncrm log meeting "Jane Doe" --summary "Quarterly review" --date 2026-02-15\ncrm log note "Jane Doe" --summary "Prefers morning meetings"
```

## Related Docs

- None yet

---
*Created: 2026-02-20 | Task: #10*
