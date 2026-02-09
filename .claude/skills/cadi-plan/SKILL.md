---
name: cadi-plan
description: >
  Plan and break down work into tasks for a CADI run.
  Use this to create a structured plan before starting autonomous development.
---

# /cadi-plan

Plan and break down work into tasks for a CADI run.

## Usage

```
/cadi-plan <mode> <description>
```

- **mode**: `feature`, `bug`, or `prototype`
- **description**: What you want to build or fix

## Examples

```
/cadi-plan feature Add user authentication with login and signup pages
/cadi-plan bug Fix the cart total not updating when items are removed
/cadi-plan prototype Quick dashboard with charts showing sales data
```

## Process

1. **Analyze** the request and understand the scope
2. **Research** the codebase to understand existing patterns and structure
3. **Write a summary** describing the overall goal and context of what's being built
4. **Break down** into small, atomic tasks (each completable in one iteration)
5. **Create run** with summary:
   ```bash
   python3 .claude/skills/project-context/scripts/run_create.py --mode <mode> --summary "Overall context about what this run is building. This helps each Claude instance understand the bigger picture while working on individual tasks."
   ```
6. **Add each task**:
   ```bash
   python3 .claude/skills/project-context/scripts/task_add.py \
     --run-id <run_id> \
     --category <mode> \
     --description "<what to do>" \
     --steps "<step-by-step instructions>"
   ```
7. **List tasks** to confirm:
   ```bash
   python3 .claude/skills/project-context/scripts/task_list.py --run-id <run_id>
   ```

## Task Guidelines

Each task should be:
- **Atomic**: One focused piece of work
- **Testable**: Clear success criteria
- **Small**: Completable in a single iteration
- **Ordered**: Dependencies come first (add in order)

Good task:
> "Create login form component with email and password fields"

Bad task:
> "Build the entire authentication system"

## Steps Format

Steps should be clear and actionable:
```
1. Create component file
2. Add form fields
3. Add validation
4. Connect to API
```

## Output

After planning, show:
1. Run ID created with summary
2. List of all tasks with IDs
3. Command to start the run:
   ```bash
   .cadi/loop.sh <run_id> [max_iterations]
   ```
