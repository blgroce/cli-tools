# Contact Commands

> CRM contact subcommands: add, list, show, edit, rm

## Location

| Type | Path |
|------|------|
| Script | `crm/src/crm/commands/contact.py` |

## How It Works

- add: Create contact with optional company link, email, phone, role, tags, notes
- list: List contacts with optional --company and --tag filters, joins company name
- show: Display contact details with company name and interactions count
- edit: Update specific fields only (name, company, email, phone, role, tags, notes)
- rm: Delete contact and cascade-delete related interactions
- Bug fix: models.py from_row() now filters to valid dataclass fields for JOINed queries

## Usage

```bash
crm contact add "Jane Doe" --company "Acme Corp" --email jane@acme.com --role CEO\ncrm contact list --company "Acme Corp" --tag vip\ncrm contact show "Jane Doe"\ncrm contact edit "Jane Doe" --role COO\ncrm contact rm "Jane Doe"
```

## Related Docs

- [CRM Foundation Modules](./data-crm-foundation.md)

---
*Created: 2026-02-20 | Task: #9*
