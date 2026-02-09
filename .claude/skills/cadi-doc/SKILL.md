---
name: cadi-doc
description: >
  REQUIRED for creating documentation. Do NOT manually create files in .cadi/documentation/.
  Use this skill: when documenting ANY feature/component/system, when user asks for docs,
  when completing tasks that need documentation, after implementing significant features.
  This creates the file AND registers in database in ONE command (manual approach requires both).
  Auto-finds related docs in same category. Ensures consistent format and searchability.
---

# /cadi-doc - Documentation Creator

**ALWAYS use this instead of manually creating docs.** One command creates the file AND registers it in the database.

## Why Use This (Not Manual)

| This Skill | Manual Approach |
|------------|-----------------|
| One command | Create file + separate DB insert |
| Auto-finds related docs | Must find and link manually |
| Consistent template | May forget sections |
| Searchable via `doc_search.py` | Only if you remember to register |
| Links to task ID | Easy to forget |

## Quick Start

```bash
# Minimal - creates file + registers in DB
python3 .claude/skills/project-context/scripts/doc_create.py \
  -c infra \
  -n "feature-name" \
  -t "Feature Title" \
  -s "One-line description" \
  --location-type "Script" \
  --location-path ".cadi/scripts/example.sh" \
  --how "- Does X\n- Then Y\n- Finally Z" \
  --usage "example command or code" \
  --task-id 1
```

## Parameters

| Flag | Required | Description |
|------|----------|-------------|
| `-c, --category` | Yes | `auth`, `api`, `ui`, `data`, `infra`, `flow` |
| `-n, --name` | Yes | Short kebab-case name (e.g., `loop-script`) |
| `-t, --title` | Yes | Human-readable title |
| `-s, --summary` | Yes | One-line description |
| `--location-type` | Yes | What it is: `Script`, `Component`, `API`, `Service`, `Config` |
| `--location-path` | Yes | File path to the thing being documented |
| `--how` | Yes | Bullet points explaining how it works (use `\n` for newlines) |
| `--usage` | Yes | Example code or command |
| `--task-id` | Yes | Task ID that created this (use 0 if no task) |
| `--lang` | No | Code block language (default: `typescript`) |
| `--related` | No | Related doc links (auto-detected if omitted) |
| `--tags` | No | JSON array of search tags |

## Categories

| Category | Use For |
|----------|---------|
| `infra` | Config, deployment, tooling, scripts, CI/CD |
| `api` | API endpoints, services, integrations |
| `auth` | Authentication, authorization, permissions |
| `ui` | UI components, pages, styling |
| `data` | Database, models, state management |
| `flow` | User flows, processes, workflows |

## Examples

### Document a script
```bash
python3 .claude/skills/project-context/scripts/doc_create.py \
  -c infra -n "loop-script" -t "Loop Script" \
  -s "Main execution loop that runs Claude iteratively" \
  --location-type "Script" --location-path ".cadi/loop.sh" \
  --how "- Validates run exists\n- Loops up to max_iterations\n- Calls claude -p each iteration" \
  --usage ".cadi/loop.sh <run_id> [max_iterations]" \
  --task-id 1 --lang bash
```

### Document an API endpoint
```bash
python3 .claude/skills/project-context/scripts/doc_create.py \
  -c api -n "user-endpoints" -t "User API" \
  -s "CRUD operations for user management" \
  --location-type "API" --location-path "src/api/users.ts" \
  --how "- GET /users - list all\n- POST /users - create\n- DELETE /users/:id - remove" \
  --usage "fetch('/api/users').then(r => r.json())" \
  --task-id 5
```

### Document a UI component
```bash
python3 .claude/skills/project-context/scripts/doc_create.py \
  -c ui -n "dashboard-charts" -t "Dashboard Charts" \
  -s "Interactive charts for the main dashboard" \
  --location-type "Component" --location-path "src/components/Dashboard/Charts.tsx" \
  --how "- Uses recharts library\n- Fetches data from /api/metrics\n- Auto-refreshes every 30s" \
  --usage "<DashboardCharts data={metrics} />" \
  --task-id 12 --tags '["charts", "dashboard", "metrics"]'
```

## After Creating

Your doc is automatically:
- Written to `.cadi/documentation/<category>-<name>.md`
- Registered in database with ID
- Searchable via `doc_search.py --query "term"`
- Listed via `doc_list.py --category <category>`

## Finding Your Docs Later

```bash
# List all docs in a category
python3 .claude/skills/project-context/scripts/doc_list.py --category infra

# Search by keyword
python3 .claude/skills/project-context/scripts/doc_search.py --query "loop"

# Get specific doc with content
python3 .claude/skills/project-context/scripts/doc_get.py 1 --content
```
