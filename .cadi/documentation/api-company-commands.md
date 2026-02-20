# Company Commands Module

> CRUD commands for managing companies in the CRM CLI

## Location

| Type | Path |
|------|------|
| Script | `crm/src/crm/commands/company.py` |

## How It Works

- add: Create company with name, status, industry, website, notes. Handles duplicate names via unique constraint.
- list: All companies or filtered by --status. Text format renders rich table with ID/Name/Industry/Status.
- show: Company details with contacts_count and deals_count from joined queries.
- edit: Update any fields by name, supports --name rename. Only updates provided fields.
- rm: Delete company. Requires --force if has contacts/deals; cascade deletes interactions, deals, contacts.
- Registered in main.py via app.add_typer(company_app).
- All commands follow cli-tools conventions: JSON to stdout, errors to stderr, exit codes 0/1/3.

## Usage

```bash
crm company add "Acme Corp" --status active --industry logistics\ncrm company list --status active\ncrm company show "Acme Corp"\ncrm company edit "Acme Corp" --status past\ncrm company rm "Acme Corp" --force
```

## Related Docs

- [describe-image Auth Subcommand](./api-describe-image-auth.md)
- [describe-image describe Command](./api-describe-image-describe.md)
- [describe-image CLI - Core Structure](./api-describe-image-core.md)

---
*Created: 2026-02-20 | Task: #8*
