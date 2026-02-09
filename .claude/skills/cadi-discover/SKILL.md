---
name: cadi-discover
description: >
  Interactive discovery process to gather context and create a well-planned CADI run.
  Use this before autonomous development to ensure requirements are clear.
allowed-tools: Read, Glob, Grep, WebSearch, WebFetch, AskUserQuestion, Bash
argument-hint: <mode> [initial description]
---

# /cadi-discover

Interactive discovery to gather context and create a CADI run with well-defined tasks.

## Usage

```
/cadi-discover <mode> [initial description]
```

- **mode**: `feature`, `bug`, or `prototype`
- **description**: Optional starting point for what you want to build

## Phase 1: Discovery Questions

Ask questions **one at a time** using the AskUserQuestion tool. Be concise and focused. Gather just enough context to create good tasks.

### Question Flow

**1. What are you building?**
If no description provided, start here:
- "What do you want to build or fix? Describe it in a sentence or two."

**2. Where in the codebase?**
- "Which part of the codebase is this for? (e.g., specific directory, component, or 'new feature')"
- Use this to scope your research in Phase 2.

**3. Core requirements**
- "What are the 2-4 must-have requirements? List them in priority order."

**4. Existing patterns** (if modifying existing code)
- "Are there existing patterns or components I should follow or extend?"
- Offer: "I can research the codebase to find relevant patterns. Want me to do that?"

**5. Success criteria**
- "How will you know it's done? What should work when complete?"

**6. Constraints** (optional, only ask if relevant)
- "Any constraints I should know about? (specific libraries to use/avoid, compatibility requirements, etc.)"

### Adaptive Questioning

- Skip questions that don't apply to the mode
- For `bug`: focus on reproduction steps, expected vs actual behavior
- For `prototype`: keep it minimal, focus on core demo functionality
- For `feature`: thorough requirements gathering

## Phase 2: Codebase Research

Based on answers from Phase 1, research the codebase:

```bash
# Find relevant files
Glob for patterns in the target directory
Grep for related code patterns
Read key files to understand structure
```

Look for:
- Existing patterns to follow
- Dependencies to reuse
- Naming conventions
- File organization

Summarize findings briefly to the user.

## Phase 3: Task Breakdown

Based on discovery and research, break down into atomic tasks.

### Task Guidelines

Each task must be:
- **Atomic**: One focused piece of work
- **Testable**: Clear success criteria
- **Small**: Completable in 1 CADI iteration (~1 Claude conversation)
- **Ordered**: Dependencies first

### Good vs Bad Tasks

Good:
- "Create UserProfile component with avatar and name display"
- "Add POST /api/users endpoint with validation"
- "Fix cart total calculation when removing items"

Bad:
- "Build the user system" (too big)
- "Make it work" (unclear)
- "Implement everything" (not atomic)

### Steps Format

Each task needs clear steps:
```
1. Create file at src/components/UserProfile.tsx
2. Add props interface for user data
3. Implement avatar and name display
4. Export from components/index.ts
```

## Phase 4: Create the Run

Present the plan to the user for approval:

```
Here's the plan for your [mode]:

**Goal**: [summary from discovery]

**Tasks**:
1. [task 1 description]
2. [task 2 description]
3. [task 3 description]
...

Ready to create this run?
```

Use AskUserQuestion with options:
- "Create run" - proceed
- "Modify tasks" - adjust the plan
- "Add more tasks" - expand scope
- "Start over" - redo discovery

Once approved, use the **project-context** skill commands to create the run and tasks.

> **IMPORTANT**: Always use the commands documented in `project-context` skill.
> Reference: `.claude/skills/project-context/SKILL.md`

### Create Run
Use project-context's run_create command:
```bash
python3 .claude/skills/project-context/scripts/run_create.py --mode <mode>
```
Capture the returned run_id.

### Add Tasks
For each task, use project-context's task_add command:
```bash
python3 .claude/skills/project-context/scripts/task_add.py \
  --run-id <run_id> \
  --category <mode> \
  --description "<what to do>" \
  --steps "<step-by-step instructions>"
```

### Verify
List tasks to confirm they were created:
```bash
python3 .claude/skills/project-context/scripts/task_list.py --run-id <run_id>
```

## Phase 5: Confirmation

After creating all tasks, show the task list output and provide next steps:

```
Run created!

Run ID: <id>
Mode: <mode>
Tasks: <count>

[task list output]

To start autonomous development:
  .cadi/loop.sh <run_id> [max_iterations]
```

## Mode-Specific Behavior

### Feature Mode
- Thorough discovery (all questions)
- Research existing patterns
- Break into small, testable tasks
- Consider edge cases

### Bug Mode
- Focus on reproduction steps
- Ask about expected vs actual behavior
- Research related code
- Single task or minimal task set

### Prototype Mode
- Minimal discovery
- Focus on core demo functionality
- Skip edge cases and polish
- Favor speed over completeness
