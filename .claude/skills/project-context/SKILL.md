---
name: project-context
description: >
  REQUIRED for all CADI task/run/activity operations. Do NOT query the database directly.
  Use this skill: at SESSION START (run task_list.py), BEFORE coding (run doc_search.py),
  AFTER completing work (run activity_add.py to log changes), when creating runs/tasks,
  when user asks about progress/history/tasks/documentation.
  This is your project memory - one command instead of writing raw SQL.

  TRIGGERS: "how does X work", "where is X implemented", "what does X do",
  "explain the X system", "find documentation for", "search docs", "list docs",
  "what tasks are pending", "show me the tasks", "what's the status",
  "what have we done", "recent activity", "project history", "what changed",
  "how is X built", "understand the codebase", "explore the project",
  "what features exist", "how does this app work", "architecture overview"
---

# Project Context

Database: `.cadi/cadi-project.sqlite` | Scripts: `.claude/skills/project-context/scripts/`

## Commands

### Runs
```bash
python3 .claude/skills/project-context/scripts/run_create.py --mode <bug|prototype|feature> [--max-iterations N] [--summary "Overall context"]
python3 .claude/skills/project-context/scripts/run_get.py <id>  # Get single run with full summary
python3 .claude/skills/project-context/scripts/run_list.py [--status "planning|running|complete"] [--mode "feature"]
```

### Tasks
```bash
python3 .claude/skills/project-context/scripts/task_list.py [--category "area"] [--run-id N] [--pending]
python3 .claude/skills/project-context/scripts/task_get.py <id>
python3 .claude/skills/project-context/scripts/task_add.py --category "area" --description "what" [--steps "how"] [--run-id N]
python3 .claude/skills/project-context/scripts/task_update.py <id> [--description ""] [--steps ""] [--passes N]
```

### Activity
```bash
python3 .claude/skills/project-context/scripts/activity_add.py <task_id> \
  --changes '["change1", "change2"]' \
  --commands '["cmd1", "cmd2"]' \
  [--issues "problem - resolution"] \
  [--screenshot "/path/to/img"]
python3 .claude/skills/project-context/scripts/activity_get.py <task_id>
python3 .claude/skills/project-context/scripts/activity_get.py --recent 10
```

### Documentation
```bash
# Create new doc (file + DB sync)
python3 .claude/skills/project-context/scripts/doc_create.py \
  --category <auth|api|ui|data|infra|flow> \
  --name "feature-name" \
  --title "Title" \
  --summary "One-line desc" \
  --location-type "Component" \
  --location-path "src/..." \
  --how "- Bullet 1\n- Bullet 2" \
  --usage "code example" \
  --task-id N

# Search/list
python3 .claude/skills/project-context/scripts/doc_list.py [--category "area"]
python3 .claude/skills/project-context/scripts/doc_search.py --query "term"
python3 .claude/skills/project-context/scripts/doc_get.py <id> [--content]

# Update DB record
python3 .claude/skills/project-context/scripts/doc_update.py <id> [--summary ""] [--tags '[]']
```

## Workflow

1. **Session start**: `task_list.py` → see current state
2. **Before work**: `doc_search.py` → find relevant context
3. **After work**: `activity_add.py` → log what you did, commands that worked, issues resolved
