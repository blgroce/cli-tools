# Company Commands

> CRUD commands for managing companies in the CRM CLI

## Location

| Type | Path |
|------|------|
| Script | `crm/src/crm/commands/company.py` |

## How It Works

- add: Insert company with unique name, status, industry, website, notes
- list: Query all companies with optional --status filter, rich table for text format
- show: Look up by name, include contacts_count and deals_count
- edit: Update only provided fields, handle duplicate name on rename
- rm: Delete company, require --force if has related contacts/deals, cascade deletes interactions->deals->contacts->company

## Usage

```bash
crm company add 'Acme Corp' --status active --industry logistics\ncrm company list --status active\ncrm company show 'Acme Corp'\ncrm company edit 'Acme Corp' --status past\ncrm company rm 'Acme Corp' --force
```

## Related Docs

- [describe-image Auth Subcommand](./api-describe-image-auth.md)
- [describe-image describe Command](./api-describe-image-describe.md)
- [describe-image CLI - Core Structure](./api-describe-image-core.md)

---
*Created: 2026-02-20 | Task: #8*
