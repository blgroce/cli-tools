# Contact Commands

> CRM contact management commands: add, list, show, edit, rm

## Location

| Type | Path |
|------|------|
| Script | `crm/src/crm/commands/contact.py` |

## How It Works

- add: Create contact with optional company, email, phone, role, tags, notes
- list: List contacts with --company and --tag filters, joins company name
- show: Display contact details with company_name and interactions_count
- edit: Update specific fields only (name, company, email, phone, role, tags, notes)
- rm: Delete contact and cascade-delete related interactions
- Company resolved by name, exit code 3 if not found
- Independent contacts (no company) supported

## Usage

```bash
crm contact add "Jane Doe" --company "Acme" --email jane@acme.com --role CEO\ncrm contact list --company "Acme" --tag vip\ncrm contact show "Jane Doe"\ncrm contact edit "Jane Doe" --role COO\ncrm contact rm "Jane Doe"
```

## Related Docs

- [Company Commands](./api-company-commands.md)

---
*Created: 2026-02-20 | Task: #9*
