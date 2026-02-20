# CRM CLI Test Suite

> Complete test coverage for all CRM CLI modules - 87 tests across 8 test files

## Location

| Type | Path |
|------|------|
| Script | `crm/tests/` |

## How It Works

- Database isolation: Each test uses a temp SQLite database via tmp_db fixture that patches get_connection in all command modules
- Seeded data: seeded_db fixture provides Acme Corp company, Alice Smith contact, a call interaction with followup, and an Acme Deal
- JSON output parsing: All tests parse JSON from result.output (stderr is mixed into output by CliRunner default)
- Error testing: Error responses also parsed from result.output since CliRunner mixes stderr
- Exit code verification: Tests verify correct exit codes (0=success, 1=general error, 2=invalid args, 3=not found)
- Test files: conftest.py (fixtures), test_db.py (9 tests), test_company.py (16 tests), test_contact.py (13 tests), test_log.py (16 tests), test_deal.py (14 tests), test_followup.py (7 tests), test_search.py (6 tests), test_status.py (5 tests)

## Usage

```bash
python3 -m pytest crm/tests/ -v
```

## Related Docs

- [Output Saving for describe-image CLI](./infra-describe-image-output-saving.md)
- [CLI Tools Standards](./infra-cli-tools-standards.md)
- [describe-image Package Structure](./infra-describe-image-structure.md)
- [describe-image CLI End-to-End Testing](./infra-describe-image-testing.md)
- [CLI Shared Library](./infra-cli-shared-library.md)

---
*Created: 2026-02-20 | Task: #14*
