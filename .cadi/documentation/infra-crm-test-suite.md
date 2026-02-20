# CRM Test Suite

> Comprehensive pytest test suite covering all CRM CLI modules with 87 tests

## Location

| Type | Path |
|------|------|
| Script | `crm/tests/` |

## How It Works

- conftest.py provides shared fixtures: tmp_db (patches get_connection for test isolation), runner (Typer CliRunner), seeded_db (pre-populated with sample data)
- test_db.py: 9 tests covering schema init, columns, FK enforcement, uniqueness, idempotent init
- test_company.py: 16 tests for add, list, show, edit, rm, duplicate errors, not_found, force delete
- test_contact.py: 13 tests for add (with/without company), list (company/tag filters), show, edit, rm
- test_log.py: 16 tests for all 4 interaction types, followup parsing (Nd/Nw/ISO), date override, auto company_id resolution
- test_deal.py: 15 tests for add, list, show, move, rm, stage validation, stage/company filters
- test_followup.py: 7 tests for default/week/all views, done command, empty state, days_overdue field
- test_search.py: 6 tests for cross-entity search, per-entity results, no results
- test_status.py: 5 tests for dashboard metrics, empty db, pipeline/overdue counts

## Usage

```bash
cd crm && . .venv/bin/activate && python -m pytest tests/ -v
```

## Related Docs

- [Output Saving for describe-image CLI](./infra-describe-image-output-saving.md)
- [CLI Tools Standards](./infra-cli-tools-standards.md)
- [describe-image Package Structure](./infra-describe-image-structure.md)
- [describe-image CLI End-to-End Testing](./infra-describe-image-testing.md)
- [CLI Shared Library](./infra-cli-shared-library.md)

---
*Created: 2026-02-20 | Task: #14*
