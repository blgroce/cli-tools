# CRM Test Suite

> Complete pytest test suite for CRM CLI - 87 tests across 8 modules

## Location

| Type | Path |
|------|------|
| Script | `crm/tests/` |

## How It Works

- conftest.py: tmp_db, runner, seeded_db fixtures patching all command modules
- test_db.py (9 tests): schema creation, column validation, FK enforcement, unique constraints
- test_company.py (16 tests): CRUD, duplicate errors, force cascade delete, status filter
- test_contact.py (13 tests): CRUD with/without company, tag/company filters, cascade delete
- test_log.py (16 tests): all 4 interaction types, followup parsing (Nd/Nw/ISO), date override, auto company_id
- test_deal.py (14 tests): CRUD, stage validation, stage/company filters, move command
- test_followup.py (7 tests): default/week/all views, done command, days_overdue field
- test_search.py (6 tests): cross-entity LIKE search, empty results
- test_status.py (5 tests): dashboard data, pipeline counts, empty DB handling

## Usage

```bash
cd crm && python3 -m pytest tests/ -v
```

## Related Docs

- [Output Saving for describe-image CLI](./infra-describe-image-output-saving.md)
- [CLI Tools Standards](./infra-cli-tools-standards.md)
- [describe-image Package Structure](./infra-describe-image-structure.md)
- [describe-image CLI End-to-End Testing](./infra-describe-image-testing.md)
- [CLI Shared Library](./infra-cli-shared-library.md)

---
*Created: 2026-02-20 | Task: #14*
