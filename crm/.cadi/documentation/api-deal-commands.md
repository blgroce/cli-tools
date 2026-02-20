# Deal Commands (add, list, show, move, rm)

> CRUD operations for managing deals in the CRM pipeline

## Location

| Type | Path |
|------|------|
| API | `crm/src/crm/commands/deal.py` |

## How It Works

- add: Creates deal with company/contact name resolution, stage validation
- list: Returns deals with JOINed company/contact names, supports --stage and --company filters
- show: Returns full deal details by title lookup
- move: Updates deal stage with validation (lead/proposal/negotiation/active/closed-won/closed-lost)
- rm: Deletes deal by title
- Stage validation via _validate_stage() helper
- Text format uses rich tables with formatted currency values

## Usage

```bash
crm deal add "Website Redesign" --company "Acme Corp" --value 15000 --stage proposal --contact "Jane Doe"\ncrm deal list --stage active --company "Acme Corp"\ncrm deal show "Website Redesign"\ncrm deal move "Website Redesign" --stage active\ncrm deal rm "Website Redesign"
```

## Related Docs

- [Interaction Logging Commands](./api-log-commands.md)
- [Company Commands](./api-company-commands.md)
- [Contact Commands](./api-contact-commands.md)
- [CRM Interaction Logging Commands](./api-crm-log-commands.md)

---
*Created: 2026-02-20 | Task: #11*
