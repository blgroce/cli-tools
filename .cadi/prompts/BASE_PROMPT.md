# CADI - Run <RUN_ID>

**IMPORTANT: This is a non-interactive autonomous session. Do NOT ask questions or wait for user input. Make reasonable decisions and proceed. If you encounter a blocker you cannot resolve, log it in the activity and mark the task as blocked (passes=0), then stop.**

Scripts: `.claude/skills/project-context/scripts/`

---

## CRITICAL: Avoid Long-Running Commands

**You will be killed after 5 minutes of inactivity.** Never run commands that don't exit:

❌ **DO NOT RUN:**
- `npm run dev` / `npm start` / `vite` (dev servers)
- `uvicorn main:app` / `flask run` / `python -m http.server` (backend servers)
- `tail -f` / `watch` (continuous monitoring)
- Any command that waits for input or runs forever

✅ **INSTEAD:**
- For verification: Use `/agent-browser` which handles server lifecycle
- For build checks: `npm run build` (exits when done)
- For quick server tests: Start server in background with timeout:
  ```bash
  timeout 10 npm run dev &
  sleep 3
  curl http://localhost:5173 || echo "Server check"
  pkill -f vite
  ```
- For type/lint checks: `npm run lint`, `tsc --noEmit`

---

Execute these steps IN ORDER. Do not skip steps.

## Step 1: Understand the Run Context

```bash
python3 .claude/skills/project-context/scripts/run_get.py <RUN_ID>
```

Read the run's `summary` field to understand the overall goal of this feature/project. This provides important context for your specific task. **However, you are only responsible for completing the single task assigned to you - do not work on other parts of the run.**

## Step 2: Get Next Task

```bash
python3 .claude/skills/project-context/scripts/task_list.py --run-id <RUN_ID> --pending
```

Take the first task from the list.

## Step 3: Implement

Follow the task's steps. Run appropriate checks (lint, build, test).

## Step 4: Verify & Capture Proof (REQUIRED)

You MUST verify the implementation works AND capture proof. This is NOT optional.

**UI/Frontend projects:**
- Use `/agent-browser` to test in the browser - it handles starting/stopping servers
- Check for console errors - FIX ANY ERRORS before proceeding
- Screenshot: `.cadi/screenshots/<task_id>_<short_description>.png`
- **DO NOT manually run dev servers** - use agent-browser or build checks only

**Backend/API projects:**
- For quick checks: Use curl/httpie with backgrounded server + timeout
- Capture output/response as proof
- Save to: `.cadi/proof/<task_id>_<short_description>.txt`
- Kill any servers you start: `pkill -f uvicorn` or similar

**CLI/Library projects:**
- Run commands or tests that exercise the feature
- Capture output as proof
- Save to: `.cadi/proof/<task_id>_<short_description>.txt`

**Build verification (always safe):**
- `npm run build` - verifies code compiles
- `tsc --noEmit` - type checks without emitting
- `npm run lint` - checks for errors

If issues found, go back to Step 3 and fix. Loop until working.

## Step 5: Document (REQUIRED)

You MUST create documentation using `/cadi-doc` for every completed task. This is NOT optional.

Document what was implemented, changed, or fixed. The documentation creates both a file AND syncs to the database for future context.

## Step 6: Log Activity

```bash
python3 .claude/skills/project-context/scripts/activity_add.py <task_id> \
  --changes '["change1", "change2"]' \
  --commands '["cmd1", "cmd2"]' \
  --screenshot "<proof_path>" \
  --issues "<any issues and resolutions>"
```

## Step 7: Completion Checklist

**BEFORE marking complete, verify ALL:**

- [ ] Code builds without errors
- [ ] No runtime errors
- [ ] Feature works as described (manually verified)
- [ ] Proof captured (screenshot or output file)
- [ ] Documentation created via /cadi-doc
- [ ] Activity logged with proof path
- [ ] All task steps completed

**If ANY fails, DO NOT mark complete. Fix first.**

## Step 8: Mark Complete

```bash
python3 .claude/skills/project-context/scripts/task_update.py <task_id> --passes 1
```

## Step 9: Commit

```bash
git add -A && git commit -m "<type>: <description>"
```

Do NOT push.

---

## Handling Failures

### When to Fail a Task

Mark a task as FAILED when you encounter an **unrecoverable blocker**:
- Missing credentials/access you cannot obtain
- Impossible requirements or contradictions
- External service unavailable (after reasonable retry)
- Architectural mismatch (wrong framework, incompatible versions, etc.)

**Do NOT fail a task for:**
- Fixable bugs or errors
- Missing files you can create
- Configuration you can add
- Dependencies you can install

### How to Fail a Task

1. Log the error:
```bash
python3 .claude/skills/project-context/scripts/agent_message.py \
  --type error \
  --message "Clear explanation of the blocker" \
  --task-id <task_id> \
  --run-id <RUN_ID>
```

2. Mark the task as failed:
```bash
python3 .claude/skills/project-context/scripts/task_fail.py <task_id> \
  --reason "Same explanation"
```

3. STOP - do not attempt other tasks this iteration. The loop will continue to the next iteration.

### Critical Failures (Abort Run)

If a failure blocks ALL remaining tasks (e.g., database corruption, missing core dependency):
```bash
python3 .claude/skills/project-context/scripts/agent_message.py \
  --type abort \
  --message "Critical issue that blocks all work" \
  --run-id <RUN_ID>
```

The loop will terminate immediately after an abort message.

---

ONE task per iteration. Stop after Step 9 (or after failing a task).
