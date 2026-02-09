#!/bin/bash
# Activity logger hook for CADI runs
# Logs all tool usage and updates last-activity timestamp

TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
EPOCH=$(date '+%s')

# Read the hook input from stdin
INPUT=$(cat)

# Extract cwd and tool info from JSON, using cwd for absolute paths
read -r PROJECT_ROOT TOOL_INFO <<< $(echo "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    cwd = d.get('cwd', '.')
    tool_name = d.get('tool_name', 'unknown')
    tool_input = d.get('tool_input', {})

    # Build tool info string
    if tool_name == 'Bash' and isinstance(tool_input, dict):
        cmd = tool_input.get('command', '')
        if len(cmd) > 100:
            cmd = cmd[:100] + '...'
        cmd = cmd.replace('\n', ' ').replace('\r', '')
        info = f'Bash: {cmd}'
    elif tool_name == 'Read' and isinstance(tool_input, dict):
        path = tool_input.get('file_path', '')
        info = f'Read: {path}'
    elif tool_name == 'Write' and isinstance(tool_input, dict):
        path = tool_input.get('file_path', '')
        info = f'Write: {path}'
    elif tool_name == 'Edit' and isinstance(tool_input, dict):
        path = tool_input.get('file_path', '')
        info = f'Edit: {path}'
    elif tool_name == 'Glob' and isinstance(tool_input, dict):
        pattern = tool_input.get('pattern', '')
        info = f'Glob: {pattern}'
    elif tool_name == 'Grep' and isinstance(tool_input, dict):
        pattern = tool_input.get('pattern', '')
        info = f'Grep: {pattern}'
    else:
        info = tool_name
    # Output cwd and info separated by space (first word is cwd)
    print(f'{cwd} {info}')
except Exception as e:
    print(f'. parse_error: {e}')
" 2>/dev/null || echo ". unknown")

# Use absolute paths based on project root
LOG_FILE="$PROJECT_ROOT/.cadi/activity.log"
HEARTBEAT_FILE="$PROJECT_ROOT/.cadi/last_activity"
DEBUG_LOG="$PROJECT_ROOT/.cadi/hook_debug.log"

# Save raw input for debugging
echo "[$TIMESTAMP] RAW INPUT:" >> "$DEBUG_LOG"
echo "$INPUT" >> "$DEBUG_LOG"
echo "---" >> "$DEBUG_LOG"

# Log the activity with details
echo "[$TIMESTAMP] $TOOL_INFO" >> "$LOG_FILE"

# Update heartbeat file with epoch timestamp (for loop to check staleness)
echo "$EPOCH|$TOOL_INFO" > "$HEARTBEAT_FILE"

# Exit 0 to allow the tool to proceed
exit 0
