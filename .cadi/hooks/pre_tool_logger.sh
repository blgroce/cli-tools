#!/bin/bash
# Pre-tool logger - logs what Claude is ABOUT to do before execution
# This helps identify hanging commands since we see the intent before it runs

TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
EPOCH=$(date '+%s')

# Read the hook input from stdin
INPUT=$(cat)

# Extract cwd and tool details from JSON
read -r PROJECT_ROOT TOOL_INFO <<< $(echo "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    cwd = d.get('cwd', '.')
    tool_name = d.get('tool_name', 'unknown')
    tool_input = d.get('tool_input', {})

    if tool_name == 'Bash' and isinstance(tool_input, dict):
        cmd = tool_input.get('command', '')
        # Full command for pre-log (we want to see what's about to run)
        cmd_preview = cmd.replace('\n', '\\\\n')[:200]
        info = f'STARTING Bash: {cmd_preview}'
    elif tool_name == 'Read':
        path = tool_input.get('file_path', '') if isinstance(tool_input, dict) else ''
        info = f'STARTING Read: {path}'
    elif tool_name == 'Write':
        path = tool_input.get('file_path', '') if isinstance(tool_input, dict) else ''
        info = f'STARTING Write: {path}'
    elif tool_name == 'Edit':
        path = tool_input.get('file_path', '') if isinstance(tool_input, dict) else ''
        info = f'STARTING Edit: {path}'
    elif tool_name == 'Task':
        desc = tool_input.get('description', '') if isinstance(tool_input, dict) else ''
        info = f'STARTING Task: {desc}'
    elif tool_name == 'Skill':
        skill = tool_input.get('skill', '') if isinstance(tool_input, dict) else ''
        info = f'STARTING Skill: {skill}'
    else:
        info = f'STARTING {tool_name}'
    print(f'{cwd} {info}')
except Exception as e:
    print(f'. STARTING unknown (parse error: {e})')
" 2>/dev/null || echo ". STARTING unknown")

# Use absolute paths based on project root
PRE_LOG="$PROJECT_ROOT/.cadi/pre_tool.log"
CURRENT_TOOL="$PROJECT_ROOT/.cadi/current_tool"

# Log to pre-tool log with timestamp
echo "[$TIMESTAMP] $TOOL_INFO" >> "$PRE_LOG"

# Also update a "currently running" file so we know what's in progress
echo "$EPOCH|$TOOL_INFO" > "$CURRENT_TOOL"

# Exit 0 to allow tool to proceed
exit 0
