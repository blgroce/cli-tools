#!/bin/bash
# Block AskUserQuestion in automated CADI runs
# This tool hangs forever in non-interactive mode

TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Read the hook input from stdin
INPUT=$(cat)

# Extract cwd and tool name from JSON
read -r PROJECT_ROOT TOOL_NAME <<< $(echo "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    cwd = d.get('cwd', '.')
    tool_name = d.get('tool_name', 'unknown')
    print(f'{cwd} {tool_name}')
except:
    print('. unknown')
" 2>/dev/null || echo ". unknown")

# Use absolute paths based on project root
LOG_FILE="$PROJECT_ROOT/.cadi/activity.log"
SIGNAL_FILE="$PROJECT_ROOT/.cadi/hook_signal"

if [ "$TOOL_NAME" = "AskUserQuestion" ]; then
    echo "[$TIMESTAMP] BLOCKED: AskUserQuestion (not supported in automated mode)" >> "$LOG_FILE"
    # Signal the loop that a question was blocked
    echo "QUESTION_BLOCKED|$TIMESTAMP" > "$SIGNAL_FILE"
    # Output error message that Claude will see
    echo "AskUserQuestion is not available in automated CADI runs. Make a reasonable decision and proceed, or mark the task as failed with a clear reason if you truly cannot proceed without user input."
    exit 1
fi

exit 0
