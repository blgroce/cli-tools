# Plan Mode - Headless Feature Planning

**CRITICAL: You are running in a NON-INTERACTIVE headless session. You MUST NOT ask questions or wait for user input. Make reasonable decisions based on existing codebase patterns and proceed.**

## Your Mission

You will receive a feature description. Your job is to:
1. Understand what the user wants
2. Research the codebase to understand existing patterns
3. Create a run with a comprehensive summary
4. Break down the work into atomic, implementable tasks
5. Output the run_id so the UI can display it

## Workflow

### Step 1: Understand the Request

Parse the feature description provided. Identify:
- What functionality is being requested
- What user-facing outcomes are expected
- Any implicit requirements

**Do NOT ask clarifying questions.** If something is ambiguous, make the reasonable choice and note it in the summary.

### Step 2: Research the Codebase

Use search tools to understand:
- Existing file structure and patterns
- Similar features already implemented
- Technologies and frameworks in use
- Naming conventions and code style

Output progress updates as you research:
```
[PLANNING] Researching codebase structure...
[PLANNING] Found existing patterns in <directory>...
[PLANNING] Analyzing <component type>...
```

### Step 3: Write Run Summary

Write a comprehensive summary that:
- Describes the overall goal of the feature
- Explains the approach being taken
- Notes any decisions made (and why)
- Lists key files/areas that will be affected

This summary helps each Claude instance understand context while working on individual tasks.

### Step 4: Break Down into Tasks

Create atomic tasks following these guidelines:

**Each task MUST be:**
- **Atomic**: One focused piece of work
- **Small**: Completable in a single iteration (5-15 minutes of work)
- **Testable**: Clear success criteria
- **Self-contained**: Can be verified independently

**Task ordering:**
- Dependencies come first (add tasks in dependency order)
- Backend before frontend (if both needed)
- Core functionality before UI polish
- Create components before integrating them

**Task format:**
- **Description**: What to do (short, action-oriented)
- **Steps**: Numbered step-by-step instructions
- **Category**: Usually matches the run mode (feature, bug, prototype)

**Good task examples:**
```
Description: Create LoginForm component with email/password fields
Steps:
1. Create zoe/frontend/src/components/LoginForm.tsx
2. Add form with email and password inputs
3. Add basic validation (required fields)
4. Add submit button with loading state
5. Export from components/index.ts
```

**Bad task (too large):**
```
Description: Build the entire authentication system
```

### Step 5: Create Run and Tasks

1. Create the run with summary:
```bash
python3 .claude/skills/project-context/scripts/run_create.py \
  --mode feature \
  --summary "<comprehensive summary>"
```

2. Add each task in order:
```bash
python3 .claude/skills/project-context/scripts/task_add.py \
  --run-id <run_id> \
  --category feature \
  --description "<what to do>" \
  --steps "<step-by-step instructions>"
```

3. List tasks to confirm:
```bash
python3 .claude/skills/project-context/scripts/task_list.py --run-id <run_id>
```

### Step 6: Output Results

After creating all tasks, output the final result in this exact format for the UI to capture:

```
[PLANNING_COMPLETE]
RUN_ID=<run_id>
TASK_COUNT=<number of tasks>
SUMMARY=<brief one-line summary>
[/PLANNING_COMPLETE]
```

## Progress Output Format

Throughout the planning process, output status updates for the UI to stream:

```
[PLANNING] Starting analysis of feature request...
[PLANNING] Researching existing codebase patterns...
[PLANNING] Found X relevant files...
[PLANNING] Designing task breakdown...
[PLANNING] Creating run with Y tasks...
[PLANNING] Task 1: <description>
[PLANNING] Task 2: <description>
...
[PLANNING_COMPLETE]
RUN_ID=<id>
...
```

## Decision Making Guidelines

When you encounter ambiguity:

1. **Check existing patterns** - How is it done elsewhere in the codebase?
2. **Favor simplicity** - Choose the simpler approach when equivalent
3. **Be consistent** - Match existing conventions and styles
4. **Document decisions** - Note non-obvious choices in the summary

Common decisions to make autonomously:
- Component structure → Follow existing patterns
- File locations → Match existing directory structure
- Naming → Follow existing conventions
- Technology choices → Use what's already in the project
- API design → Match existing API patterns

## Constraints

- **NO user interaction** - Don't use AskUserQuestion or similar tools
- **Time limit** - Complete planning efficiently (single iteration)
- **Focus on planning** - Don't implement anything, just create the plan
- **Output progress** - Keep the UI informed of what you're doing
