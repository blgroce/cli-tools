# CRM CLI — Specification

## Overview

A lightweight CLI CRM for BCG Ventures. Manages contacts, companies, interactions, deals, and follow-ups from the terminal. Designed to be called by both humans (`--format text`) and AI agents (JSON default).

## Storage

- **SQLite** — single file at `~/.local/share/crm/crm.db`
- Portable, zero-config, queryable
- Schema managed with simple version table for future migrations

## Data Model

### companies
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | auto |
| name | TEXT NOT NULL | unique |
| industry | TEXT | optional |
| status | TEXT | active / prospect / past / lead |
| website | TEXT | optional |
| notes | TEXT | optional |
| created_at | DATETIME | auto |
| updated_at | DATETIME | auto |

### contacts
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | auto |
| name | TEXT NOT NULL | |
| company_id | INTEGER FK | nullable (independent contacts ok) |
| role | TEXT | optional title/role |
| email | TEXT | optional |
| phone | TEXT | optional |
| tags | TEXT | comma-separated, optional |
| notes | TEXT | optional |
| created_at | DATETIME | auto |
| updated_at | DATETIME | auto |

### interactions
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | auto |
| contact_id | INTEGER FK | required |
| company_id | INTEGER FK | nullable (auto-resolve from contact) |
| type | TEXT | call / email / meeting / note |
| summary | TEXT NOT NULL | what happened |
| occurred_at | DATETIME | when it happened (default now) |
| followup_date | DATE | nullable — when to follow up |
| followup_note | TEXT | nullable — what the follow-up is about |
| created_at | DATETIME | auto |

### deals
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | auto |
| title | TEXT NOT NULL | |
| company_id | INTEGER FK | required |
| contact_id | INTEGER FK | nullable — primary contact |
| value | REAL | dollar amount, nullable |
| stage | TEXT | lead / proposal / negotiation / active / closed-won / closed-lost |
| notes | TEXT | optional |
| created_at | DATETIME | auto |
| updated_at | DATETIME | auto |

## CLI Interface

### Company commands
```bash
crm company add "Acme Corp" --status active --industry "logistics"
crm company list [--status active|prospect|past|lead]
crm company show "Acme Corp"
crm company edit "Acme Corp" --status past
crm company rm "Acme Corp"          # requires --force if has contacts/deals
```

### Contact commands
```bash
crm contact add "Jane Doe" --company "Acme Corp" --email jane@acme.com --role "CEO" --phone "555-1234"
crm contact list [--company "Acme Corp"] [--tag vip]
crm contact show "Jane Doe"
crm contact edit "Jane Doe" --role "COO"
crm contact rm "Jane Doe"
```

### Interaction logging
```bash
crm log call "Jane Doe" --summary "Discussed Q2 timeline" [--followup 7d] [--followup-note "Send proposal"]
crm log email "Jane Doe" --summary "Sent invoice #1234"
crm log meeting "Jane Doe" --summary "Quarterly review" --date 2026-02-15
crm log note "Jane Doe" --summary "Prefers morning meetings"
```

- `--followup` accepts: `Nd` (N days), `Nw` (N weeks), or `YYYY-MM-DD`
- `--date` defaults to now if omitted

### Deal commands
```bash
crm deal add "Website Redesign" --company "Acme Corp" --value 15000 --stage proposal [--contact "Jane Doe"]
crm deal list [--stage active|proposal|...] [--company "Acme Corp"]
crm deal show "Website Redesign"
crm deal move "Website Redesign" --stage active
crm deal rm "Website Redesign"
```

### Follow-ups
```bash
crm followups                  # due today + overdue
crm followups --week           # next 7 days
crm followups --all            # all pending
crm followups done <id>        # mark follow-up complete (clears followup_date)
```

### Search
```bash
crm search "pricing"           # searches across contacts, interactions, deals, companies
```

### Dashboard
```bash
crm status                     # summary: active deals, overdue follow-ups, recent interactions
```

## Output Rules

Follow cli-tools conventions:
- JSON to stdout by default (agents parse it)
- `--format text` for human-readable rich tables
- Errors to stderr
- Standard exit codes (0/1/2/3/4)
- No interactive prompts

## Architecture

```
crm/
├── pyproject.toml
├── src/
│   └── crm/
│       ├── __init__.py        # version
│       ├── main.py            # typer app, subcommand registration
│       ├── db.py              # SQLite connection, schema init, migrations
│       ├── models.py          # dataclasses for Company, Contact, Interaction, Deal
│       ├── commands/
│       │   ├── __init__.py
│       │   ├── company.py     # company subcommands
│       │   ├── contact.py     # contact subcommands
│       │   ├── log.py         # interaction logging subcommands
│       │   ├── deal.py        # deal subcommands
│       │   ├── followup.py    # follow-up subcommands
│       │   ├── search.py      # cross-entity search
│       │   └── status.py      # dashboard
│       └── output.py          # emit_success/emit_error helpers (JSON + text)
└── tests/
    ├── __init__.py
    ├── test_db.py
    ├── test_company.py
    ├── test_contact.py
    ├── test_log.py
    ├── test_deal.py
    └── test_followup.py
```

## Dependencies

- `typer` — CLI framework
- `rich` — terminal tables and formatting for `--format text`
- Standard library only for everything else (sqlite3, dataclasses, datetime, json)

## Future (not in v0.1)

These are explicitly out of scope for the initial build but worth noting:
- Taskwarrior sync (follow-ups ↔ TW tasks)
- Obsidian export (contact cards as markdown notes)
- memory-search integration (store interactions in vector DB)
- Import from CSV/vCard
- Email integration via himalaya
