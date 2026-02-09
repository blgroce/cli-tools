#!/bin/bash
# Stop hook - logs when Claude session ends and why
# Based on Claude Code hooks documentation:
# - stop_hook_active=false means Claude stopped naturally (first stop)
# - stop_hook_active=true means Claude is continuing due to a stop hook

TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Read the hook input from stdin
INPUT=$(cat)

# Extract cwd and stop info from JSON using a temp file for reliable parsing
# Per docs: The only stop-related field is stop_hook_active (boolean)
# We interpret: stop_hook_active=false -> natural_stop, stop_hook_active=true -> hook_continue
TMPFILE=$(mktemp)
echo "$INPUT" > "$TMPFILE"

PARSED=$(python3 << PYEOF
import json
try:
    with open('$TMPFILE', 'r') as f:
        d = json.load(f)
    cwd = d.get('cwd', '.')
    session_id = d.get('session_id', 'unknown')
    stop_hook_active = d.get('stop_hook_active', False)
    permission_mode = d.get('permission_mode', 'unknown')

    # Determine stop status based on stop_hook_active
    # stop_hook_active=false means this is a natural stop (Claude finished on its own)
    # stop_hook_active=true means Claude is continuing after a hook blocked a previous stop
    if stop_hook_active:
        status = 'hook_continue'
    else:
        status = 'natural_stop'

    # Output: PROJECT_ROOT|STOP_INFO
    print(f'{cwd}|STOPPED: status={status} session={session_id[:8]} mode={permission_mode}')
except Exception as e:
    print(f'.|STOPPED: status=parse_error error={e}')
PYEOF
)

rm -f "$TMPFILE"

# Split the parsed output
PROJECT_ROOT=$(echo "$PARSED" | cut -d'|' -f1)
STOP_INFO=$(echo "$PARSED" | cut -d'|' -f2-)

# Use absolute paths based on project root
LOG_FILE="$PROJECT_ROOT/.cadi/activity.log"
STOP_LOG="$PROJECT_ROOT/.cadi/stop.log"
CURRENT_TOOL="$PROJECT_ROOT/.cadi/current_tool"

# Log to both files
echo "[$TIMESTAMP] $STOP_INFO" >> "$LOG_FILE"
echo "[$TIMESTAMP] $STOP_INFO" >> "$STOP_LOG"

# Also dump raw input for debugging
echo "[$TIMESTAMP] RAW:" >> "$STOP_LOG"
echo "$INPUT" >> "$STOP_LOG"
echo "---" >> "$STOP_LOG"

# Clear current tool file
rm -f "$CURRENT_TOOL"

exit 0
