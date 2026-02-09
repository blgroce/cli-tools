#!/bin/bash
# Notification hook - logs all notifications (errors, warnings, info)

TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Read the hook input from stdin
INPUT=$(cat)

# Extract cwd and notification details from JSON
read -r PROJECT_ROOT NOTIFY_INFO <<< $(echo "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    cwd = d.get('cwd', '.')
    notif_type = d.get('type', 'unknown')
    message = d.get('message', '')
    # Truncate long messages
    if len(message) > 200:
        message = message[:200] + '...'
    message = message.replace('\n', ' ')
    print(f'{cwd} NOTIFY [{notif_type}]: {message}')
except Exception as e:
    print(f'. NOTIFY [error]: parse_error={e}')
" 2>/dev/null || echo ". NOTIFY: unknown")

# Use absolute paths based on project root
LOG_FILE="$PROJECT_ROOT/.cadi/activity.log"
NOTIFY_LOG="$PROJECT_ROOT/.cadi/notifications.log"

# Log to both files
echo "[$TIMESTAMP] $NOTIFY_INFO" >> "$LOG_FILE"
echo "[$TIMESTAMP] $NOTIFY_INFO" >> "$NOTIFY_LOG"

# Dump raw for debugging
echo "[$TIMESTAMP] RAW:" >> "$NOTIFY_LOG"
echo "$INPUT" >> "$NOTIFY_LOG"
echo "---" >> "$NOTIFY_LOG"

exit 0
