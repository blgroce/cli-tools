#!/bin/bash
set -e

# Set working directory to project root (parent of .cadi)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# Set unique agent-browser session based on project path
# This prevents cross-contamination when multiple CADI projects run simultaneously
export AGENT_BROWSER_SESSION="cadi-$(basename "$PROJECT_ROOT")"

### Color codes for CADI branding
CYAN='\033[0;36m'
CYAN_BOLD='\033[1;36m'
WHITE='\033[1;37m'
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
DIM='\033[2m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Unicode characters for visual elements
CHECK="✓"
CROSS="✗"
ARROW="→"
BULLET="●"
SPINNER_CHARS="⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

## Variables
DB=".cadi/cadi-project.sqlite"

# Function to print the CADI banner
print_banner() {
    echo ""
    echo -e "${CYAN_BOLD}"
    cat << 'BANNER'
    +--------------------------------------------------+
    |                                                  |
    |      .d8888b.        d8888 8888888b. 8888888     |
    |     d88P  Y88b      d88888 888  "Y88b  888       |
    |     888    888     d88P888 888    888  888       |
    |     888           d88P 888 888    888  888       |
    |     888          d88P  888 888    888  888       |
    |     888    888  d88P   888 888    888  888       |
    |     Y88b  d88P d8888888888 888  .d88P  888       |
    |      "Y8888P" d88P     888 8888888P" 8888888     |
    |                                                  |
BANNER
    echo -e "    |    ${WHITE}Claude Autonomous Development Interface${CYAN_BOLD}       |"
    cat << 'BANNER'
    |                                                  |
    +--------------------------------------------------+
BANNER
    echo -e "${NC}"
}

# Function to print a section header
print_header() {
    local title="$1"
    local width=50
    local padding=$(( (width - ${#title}) / 2 ))
    echo ""
    echo -e "${CYAN}┌──────────────────────────────────────────────────┐${NC}"
    printf "${CYAN}│${NC}%*s${BOLD}%s${NC}%*s${CYAN}│${NC}\n" $padding "" "$title" $((width - padding - ${#title})) ""
    echo -e "${CYAN}└──────────────────────────────────────────────────┘${NC}"
}

# Function to print a status line
print_status() {
    local label="$1"
    local value="$2"
    local color="${3:-$GREEN}"
    printf "  ${DIM}%-18s${NC} ${color}%s${NC}\n" "$label:" "$value"
}

# Function to print iteration header
print_iteration() {
    local current="$1"
    local max="$2"
    local remaining="$3"
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN_BOLD}  ${ARROW} ITERATION ${WHITE}$current${CYAN_BOLD} of ${WHITE}$max${NC}"
    echo -e "${DIM}    $remaining task(s) remaining${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

# Function to show a countdown with animation
countdown() {
    local seconds=$1
    echo ""
    for ((s=seconds; s>0; s--)); do
        printf "\r  ${DIM}Starting in ${WHITE}%d${DIM}...${NC}  " "$s"
        sleep 1
    done
    printf "\r  ${GREEN}${CHECK} Launching!${NC}          \n"
    echo ""
}

# Function to print completion status
print_complete() {
    echo ""
    echo -e "${GREEN}"
    echo "   ╔════════════════════════════════════════════════╗"
    echo "   ║                                                ║"
    echo "   ║            ✓  RUN COMPLETE  ✓                  ║"
    echo "   ║                                                ║"
    echo -e "   ║  ${WHITE}All tasks finished successfully!${GREEN}              ║"
    echo "   ║                                                ║"
    echo "   ╚════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Function to print max iterations reached
print_max_iterations() {
    echo ""
    echo -e "${YELLOW}"
    echo "   ╔════════════════════════════════════════════════╗"
    echo "   ║                                                ║"
    echo "   ║          ⚠  MAX ITERATIONS  ⚠                  ║"
    echo "   ║                                                ║"
    echo -e "   ║  ${WHITE}Run stopped at iteration limit${YELLOW}               ║"
    echo "   ║                                                ║"
    echo "   ╚════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Function to print run failed (some tasks failed)
print_failed() {
    echo ""
    echo -e "${RED}"
    echo "   ╔════════════════════════════════════════════════╗"
    echo "   ║                                                ║"
    echo "   ║            ✗  RUN FAILED  ✗                    ║"
    echo "   ║                                                ║"
    echo -e "   ║  ${WHITE}Some tasks could not be completed${RED}             ║"
    echo "   ║                                                ║"
    echo "   ╚════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Function to print run aborted
print_aborted() {
    local message="$1"
    echo ""
    echo -e "${RED}"
    echo "   ╔════════════════════════════════════════════════╗"
    echo "   ║                                                ║"
    echo "   ║            ⊘  RUN ABORTED  ⊘                   ║"
    echo "   ║                                                ║"
    echo -e "   ║  ${WHITE}Agent requested immediate stop${RED}                ║"
    echo "   ║                                                ║"
    echo "   ╚════════════════════════════════════════════════╝"
    echo -e "${NC}"
    if [ -n "$message" ]; then
        echo -e "  ${RED}Reason:${NC} $message"
        echo ""
    fi
}

# Function to print error
print_error() {
    local message="$1"
    echo ""
    echo -e "  ${RED}${CROSS} Error:${NC} $message"
    echo ""
}

# Function to print warning/note
print_note() {
    local message="$1"
    echo -e "  ${YELLOW}${BULLET}${NC} ${DIM}$message${NC}"
}

# Function to display current activity and recent activity feed
display_current_activity() {
    local LAST_ACTIVITY_FILE=".cadi/last_activity"
    local ACTIVITY_LOG=".cadi/activity.log"

    # Get current tool from last_activity file
    local current_tool="No activity"
    if [ -f "$LAST_ACTIVITY_FILE" ]; then
        local content
        content=$(cat "$LAST_ACTIVITY_FILE" 2>/dev/null)
        if [ -n "$content" ]; then
            # Format: EPOCH|TOOL_INFO
            current_tool=$(echo "$content" | cut -d'|' -f2)
            if [ -z "$current_tool" ]; then
                current_tool="No activity"
            fi
        fi
    fi

    # Display current tool prominently
    echo -e "  ${CYAN}${BULLET} Current:${NC} ${WHITE}${current_tool}${NC}"

    # Get last 3 activity entries from activity.log
    if [ -f "$ACTIVITY_LOG" ]; then
        # Read last 3 lines, filter out === headers and STOPPED/NOTIFY lines
        local recent_activities
        recent_activities=$(tail -10 "$ACTIVITY_LOG" 2>/dev/null | grep -v "^===" | grep -v "STOPPED:" | grep -v "NOTIFY" | tail -3)

        if [ -n "$recent_activities" ]; then
            echo -e "  ${DIM}Recent activity:${NC}"
            while IFS= read -r line; do
                # Parse format: [TIMESTAMP] Tool: command or [TIMESTAMP] ToolName
                # Extract just the tool/action part
                local activity
                activity=$(echo "$line" | sed 's/^\[[^]]*\] *//')
                if [ -n "$activity" ]; then
                    echo -e "    ${DIM}${ARROW} ${activity}${NC}"
                fi
            done <<< "$recent_activities"
        fi
    fi
}

# Function to check for natural stop and determine if we should auto-continue
# Returns 0 if natural stop detected, 1 otherwise
# Sets NATURAL_STOP_DETECTED=true if detected
check_natural_stop() {
    local STOP_LOG=".cadi/stop.log"
    local STOP_POS=".cadi/stop_pos"

    # If stop log doesn't exist, nothing to do
    if [ ! -f "$STOP_LOG" ]; then
        return 1
    fi

    # Get current file line count
    local current_lines
    current_lines=$(wc -l < "$STOP_LOG" 2>/dev/null || echo "0")

    # Get last read position (line number)
    local last_pos=0
    if [ -f "$STOP_POS" ]; then
        last_pos=$(cat "$STOP_POS" 2>/dev/null || echo "0")
        # Validate it's a number
        if ! [[ "$last_pos" =~ ^[0-9]+$ ]]; then
            last_pos=0
        fi
    fi

    # If no new lines, return
    if [ "$current_lines" -le "$last_pos" ]; then
        return 1
    fi

    # Read new lines and look for stop entries
    local new_lines
    new_lines=$(tail -n +$((last_pos + 1)) "$STOP_LOG" 2>/dev/null)

    local found_stop=false
    while IFS= read -r line; do
        # Skip empty lines, RAW: lines, raw JSON, and separators
        if [ -z "$line" ]; then
            continue
        fi
        if [[ "$line" == *"RAW:"* ]] || [[ "$line" == "{"* ]] || [[ "$line" == "---" ]]; then
            continue
        fi

        # Match stop format: [TIMESTAMP] STOPPED: ...
        if [[ "$line" == *"STOPPED:"* ]]; then
            # Check if this is a natural stop (Stop hook only fires for natural completions,
            # not user interrupts or errors per Claude CLI documentation)
            # Since we're in the monitoring loop during iteration, any STOPPED entry
            # indicates Claude finished its response naturally

            # Extract session info if available
            local session_info
            session_info=$(echo "$line" | grep -oP 'session=[^ ]+' || echo "")

            # Check for explicit status=natural_stop or treat any stop as natural
            # (per Claude docs, Stop hook doesn't fire on user interrupt)
            if [[ "$line" == *"status=natural_stop"* ]] || [[ "$line" == *"STOPPED:"* ]]; then
                found_stop=true
                # Don't echo here - let the caller decide what to display
            fi
        fi
    done <<< "$new_lines"

    # Update position marker
    echo "$current_lines" > "$STOP_POS"

    if [ "$found_stop" = true ]; then
        NATURAL_STOP_DETECTED=true
        return 0
    fi

    return 1
}

# Function to display new notifications from notifications.log
display_notifications() {
    local NOTIFY_LOG=".cadi/notifications.log"
    local NOTIFY_POS=".cadi/notification_pos"

    # If notification log doesn't exist, nothing to do
    if [ ! -f "$NOTIFY_LOG" ]; then
        return
    fi

    # Get current file size/line count
    local current_lines
    current_lines=$(wc -l < "$NOTIFY_LOG" 2>/dev/null || echo "0")

    # Get last read position (line number)
    local last_pos=0
    if [ -f "$NOTIFY_POS" ]; then
        last_pos=$(cat "$NOTIFY_POS" 2>/dev/null || echo "0")
        # Validate it's a number
        if ! [[ "$last_pos" =~ ^[0-9]+$ ]]; then
            last_pos=0
        fi
    fi

    # If no new lines, return
    if [ "$current_lines" -le "$last_pos" ]; then
        return
    fi

    # Read new lines (from last_pos+1 to current_lines)
    local new_lines
    new_lines=$(tail -n +$((last_pos + 1)) "$NOTIFY_LOG" 2>/dev/null)

    # Process new lines - only show actual NOTIFY lines (skip RAW/--- debug lines)
    while IFS= read -r line; do
        # Skip empty lines
        if [ -z "$line" ]; then
            continue
        fi

        # Skip RAW: debug lines and --- separators
        if [[ "$line" == *"RAW:"* ]] || [[ "$line" == "---" ]] || [[ "$line" == "{"* ]]; then
            continue
        fi

        # Match notification format: [TIMESTAMP] NOTIFY [type]: message
        if [[ "$line" == *"NOTIFY"* ]]; then
            # Extract timestamp and message
            local timestamp
            local notify_msg
            timestamp=$(echo "$line" | grep -oP '^\[\K[^\]]+' || echo "")
            notify_msg=$(echo "$line" | sed 's/^\[[^]]*\] *//')

            # Display with yellow color for visibility
            if [ -n "$timestamp" ]; then
                echo -e "  ${YELLOW}${BULLET} [${timestamp}] ${notify_msg}${NC}"
            else
                echo -e "  ${YELLOW}${BULLET} ${notify_msg}${NC}"
            fi
        fi
    done <<< "$new_lines"

    # Update position marker
    echo "$current_lines" > "$NOTIFY_POS"
}

### Parse arguments
DEBUG_MODE=false
VERBOSE_MODE=false
SKIP_PERMISSIONS=true  # Default to skipping permissions for headless operation
POSITIONAL_ARGS=()

while [[ $# -gt 0 ]]; do
    case $1 in
        --debug)
            DEBUG_MODE=true
            shift
            ;;
        --verbose|-v)
            VERBOSE_MODE=true
            shift
            ;;
        --dangerously-skip-permissions|--yolo)
            SKIP_PERMISSIONS=true
            shift
            ;;
        --ask-permissions|--no-yolo)
            SKIP_PERMISSIONS=false
            shift
            ;;
        *)
            POSITIONAL_ARGS+=("$1")
            shift
            ;;
    esac
done

# Restore positional args
set -- "${POSITIONAL_ARGS[@]}"

### Run ID validation
if [ -z "$1" ]; then
    print_banner
    print_error "Please provide a run ID"
    echo -e "  ${DIM}Usage:${NC} ${BOLD}loop.sh${NC} ${CYAN}<run_id>${NC} [max_iterations] [options]"
    echo ""
    echo -e "  ${DIM}Options:${NC}"
    echo -e "    ${CYAN}--debug${NC}                          Enable Claude debug mode (shows API calls)"
    echo -e "    ${CYAN}--verbose${NC}                        Enable Claude verbose mode"
    echo -e "    ${CYAN}--ask-permissions${NC}                Enable permission prompts (alias: --no-yolo)"
    echo -e "    ${DIM}Note: Permissions are skipped by default for headless operation${NC}"
    echo ""
    echo -e "  ${DIM}Create a run first with:${NC}"
    echo -e "    ${CYAN}python3 .claude/skills/project-context/scripts/run_create.py --mode <mode>${NC}"
    echo ""
    echo -e "  ${DIM}Then add tasks with:${NC}"
    echo -e "    ${CYAN}python3 .claude/skills/project-context/scripts/task_add.py --run-id <run_id> ...${NC}"
    echo ""
    exit 1
fi
RUN_ID=$1

# Verify the run exists and get its details
RUN_INFO=$(sqlite3 "$DB" "SELECT mode, max_iterations, status FROM runs WHERE id = $RUN_ID;" 2>/dev/null || echo "")
if [ -z "$RUN_INFO" ]; then
    print_banner
    print_error "Run $RUN_ID not found in database"
    exit 1
fi

# Parse run info (format: mode|max_iterations|status)
MODE=$(echo "$RUN_INFO" | cut -d'|' -f1)
DB_MAX_ITERATIONS=$(echo "$RUN_INFO" | cut -d'|' -f2)
STATUS=$(echo "$RUN_INFO" | cut -d'|' -f3)

# Check if run is in a valid state to execute
if [ "$STATUS" = "complete" ]; then
    print_banner
    print_error "Run $RUN_ID is already complete"
    exit 1
fi

# For any other status, check if there are workable tasks (pending only, not failed)
PENDING_TASKS=$(sqlite3 "$DB" "SELECT COUNT(*) FROM tasks WHERE run_id = $RUN_ID AND status = 'pending';")
FAILED_TASKS=$(sqlite3 "$DB" "SELECT COUNT(*) FROM tasks WHERE run_id = $RUN_ID AND status = 'failed';")

if [ "$PENDING_TASKS" -eq 0 ]; then
    print_banner
    if [ "$FAILED_TASKS" -gt 0 ]; then
        print_error "Run $RUN_ID has no workable tasks ($FAILED_TASKS failed)"
        sqlite3 "$DB" "UPDATE runs SET status = 'failed', completed_at = CURRENT_TIMESTAMP WHERE id = $RUN_ID;"
    else
        print_error "Run $RUN_ID has no incomplete tasks remaining"
        sqlite3 "$DB" "UPDATE runs SET status = 'complete', completed_at = CURRENT_TIMESTAMP WHERE id = $RUN_ID;"
    fi
    exit 1
fi

# For backwards compatibility, also track incomplete via passes
INCOMPLETE_TASKS=$PENDING_TASKS

### Iterations (optional override)
if [ -n "$2" ] && [ "$2" -gt 0 ]; then
    MAX_ITERATIONS=$2
    sqlite3 "$DB" "UPDATE runs SET max_iterations = $MAX_ITERATIONS WHERE id = $RUN_ID;"
else
    MAX_ITERATIONS=$DB_MAX_ITERATIONS
fi

# Update run status to running
sqlite3 "$DB" "UPDATE runs SET status = 'running' WHERE id = $RUN_ID;"

# Set prompt files based on mode
BASE_PROMPT=".cadi/prompts/BASE_PROMPT.md"
MODE_PROMPT=".cadi/prompts/${MODE^^}_PROMPT.md"

# Verify prompt files exist
if [ ! -f "$BASE_PROMPT" ]; then
    print_banner
    print_error "$BASE_PROMPT not found"
    exit 1
fi
if [ ! -f "$MODE_PROMPT" ]; then
    print_banner
    print_error "$MODE_PROMPT not found"
    exit 1
fi

# Count tasks for this run
TASK_COUNT=$(sqlite3 "$DB" "SELECT COUNT(*) FROM tasks WHERE run_id = $RUN_ID;")

if [ "$TASK_COUNT" -eq 0 ]; then
    print_banner
    print_error "No tasks assigned to run $RUN_ID"
    sqlite3 "$DB" "UPDATE runs SET status = 'no_tasks', completed_at = CURRENT_TIMESTAMP WHERE id = $RUN_ID;"
    exit 1
fi

# Display startup info
clear 2>/dev/null || true
print_banner

print_header "RUN CONFIGURATION"
echo ""
print_status "Run ID" "$RUN_ID"
print_status "Mode" "$MODE" "$MAGENTA"
print_status "Max Iterations" "$MAX_ITERATIONS" "$YELLOW"
print_status "Total Tasks" "$TASK_COUNT"
print_status "Incomplete" "$INCOMPLETE_TASKS" "$CYAN"
if [ "$DEBUG_MODE" = true ]; then
    print_status "Debug" "enabled" "$YELLOW"
fi
if [ "$VERBOSE_MODE" = true ]; then
    print_status "Verbose" "enabled" "$YELLOW"
fi
if [ "$SKIP_PERMISSIONS" = true ]; then
    print_status "Permissions" "SKIPPED" "$RED"
fi
echo ""

if [ "$STATUS" = "running" ]; then
    print_note "Resuming run (was in 'running' status)"
fi

echo -e "  ${DIM}Press ${WHITE}Ctrl+C${DIM} to abort${NC}"
echo -e "  ${DIM}Monitor activity: ${WHITE}tail -f .cadi/activity.log${NC}"

# Initialize activity log for this run
echo "" >> .cadi/activity.log
echo "=== Run $RUN_ID started at $(date) ===" >> .cadi/activity.log

countdown 3

# Main loop
for (( i=1; i<=MAX_ITERATIONS; i++ )); do
    # Check for abort signal at start of each iteration
    ABORT_MSG=$(sqlite3 "$DB" "SELECT message FROM agent_messages WHERE run_id = $RUN_ID AND type = 'abort' LIMIT 1;" 2>/dev/null || echo "")
    if [ -n "$ABORT_MSG" ]; then
        # Clear abort messages and exit
        sqlite3 "$DB" "DELETE FROM agent_messages WHERE run_id = $RUN_ID AND type = 'abort';"
        sqlite3 "$DB" "UPDATE runs SET status = 'aborted', completed_at = CURRENT_TIMESTAMP WHERE id = $RUN_ID;"
        print_aborted "$ABORT_MSG"
        print_status "Run ID" "$RUN_ID" "$RED"
        print_status "Iterations" "$((i-1))"
        echo ""
        exit 1
    fi

    # Count workable tasks (pending only, not failed)
    REMAINING=$(sqlite3 "$DB" "SELECT COUNT(*) FROM tasks WHERE run_id = $RUN_ID AND status = 'pending';")
    FAILED=$(sqlite3 "$DB" "SELECT COUNT(*) FROM tasks WHERE run_id = $RUN_ID AND status = 'failed';")

    if [ "$REMAINING" -eq 0 ]; then
        if [ "$FAILED" -gt 0 ]; then
            # Any failures = run failed
            sqlite3 "$DB" "UPDATE runs SET status = 'failed', completed_at = CURRENT_TIMESTAMP WHERE id = $RUN_ID;"
            print_failed
            print_status "Run ID" "$RUN_ID" "$RED"
            print_status "Iterations" "$((i-1))"
            print_status "Failed Tasks" "$FAILED" "$RED"
            echo ""
            exit 1
        else
            # All tasks complete, no failures
            sqlite3 "$DB" "UPDATE runs SET status = 'complete', completed_at = CURRENT_TIMESTAMP WHERE id = $RUN_ID;"
            print_complete
            print_status "Run ID" "$RUN_ID"
            print_status "Iterations" "$((i-1))"
            echo ""
            exit 0
        fi
    fi

    print_iteration "$i" "$MAX_ITERATIONS" "$REMAINING"

    # Run Claude with base + mode prompt
    BASE_CONTENT=$(cat "$BASE_PROMPT" | sed "s/<RUN_ID>/$RUN_ID/g")
    MODE_CONTENT=$(cat "$MODE_PROMPT")

    # Run Claude with activity monitoring
    MAX_RETRIES=3
    RETRY_DELAY=5
    IDLE_TIMEOUT=1200  # 20 minutes without activity = considered stuck
    CLAUDE_SUCCESS=false

    # Clean up signal/heartbeat files
    rm -f .cadi/hook_signal .cadi/last_activity

    # Initialize natural stop detection - capture current stop.log position
    NATURAL_STOP_DETECTED=false
    if [ -f ".cadi/stop.log" ]; then
        wc -l < ".cadi/stop.log" > ".cadi/stop_pos"
    else
        echo "0" > ".cadi/stop_pos"
    fi

    for (( retry=1; retry<=MAX_RETRIES; retry++ )); do
        echo -e "  ${CYAN}${ARROW}${NC} ${WHITE}Invoking Claude...${NC} ${DIM}(watching for activity)${NC}"

        # Build Claude command with optional flags
        CLAUDE_FLAGS="--output-format text"
        if [ "$DEBUG_MODE" = true ]; then
            CLAUDE_FLAGS="$CLAUDE_FLAGS --debug"
        fi
        if [ "$VERBOSE_MODE" = true ]; then
            CLAUDE_FLAGS="$CLAUDE_FLAGS --verbose"
        fi
        if [ "$SKIP_PERMISSIONS" = true ]; then
            CLAUDE_FLAGS="$CLAUDE_FLAGS --dangerously-skip-permissions"
        fi

        # Run Claude in background and monitor activity
        CLAUDE_OUTPUT_FILE=$(mktemp)
        claude -p "RUN_ID: $RUN_ID | ITERATION: $i of $MAX_ITERATIONS

$BASE_CONTENT

$MODE_CONTENT" $CLAUDE_FLAGS > "$CLAUDE_OUTPUT_FILE" 2>&1 &
        CLAUDE_PID=$!

        # Initialize heartbeat
        echo "$(date '+%s')|started" > .cadi/last_activity

        # Monitor loop - display activity every 5 seconds
        TIMED_OUT=false
        NATURAL_STOP_BREAK=false
        QUESTION_BLOCKED=false
        MONITOR_INTERVAL=5
        LAST_ACTIVITY_DISPLAY=""

        while kill -0 $CLAUDE_PID 2>/dev/null; do
            sleep $MONITOR_INTERVAL

            # Display current activity status (every interval)
            # Get current tool for status line
            CURRENT_TOOL="working"
            if [ -f .cadi/last_activity ]; then
                ACTIVITY_CONTENT=$(cat .cadi/last_activity 2>/dev/null)
                CURRENT_TOOL=$(echo "$ACTIVITY_CONTENT" | cut -d'|' -f2 | tr -d '\n')
                if [ -z "$CURRENT_TOOL" ]; then
                    CURRENT_TOOL="working"
                fi
            fi

            # Only update display if activity changed (avoid flooding)
            if [ "$CURRENT_TOOL" != "$LAST_ACTIVITY_DISPLAY" ]; then
                echo -e "  ${CYAN}${BULLET} Current:${NC} ${WHITE}${CURRENT_TOOL}${NC}"
                LAST_ACTIVITY_DISPLAY="$CURRENT_TOOL"
            fi

            # Check for and display new notifications
            display_notifications

            # Check for natural stop during execution
            if check_natural_stop; then
                echo -e "  ${GREEN}${CHECK} Natural stop detected${NC}"
                # Kill the Claude process and break to start next iteration
                echo -e "  ${CYAN}${ARROW}${NC} Restarting for next task..."
                kill $CLAUDE_PID 2>/dev/null || true
                wait $CLAUDE_PID 2>/dev/null || true
                NATURAL_STOP_BREAK=true
                break
            fi

            # Check for blocked question signal
            if [ -f .cadi/hook_signal ]; then
                SIGNAL=$(cat .cadi/hook_signal)
                if [[ "$SIGNAL" == QUESTION_BLOCKED* ]]; then
                    echo -e "  ${YELLOW}${BULLET} Claude tried to ask a question (blocked by hook)${NC}"
                    QUESTION_BLOCKED=true
                    rm -f .cadi/hook_signal
                    # Don't kill - let Claude handle the rejection and continue
                fi
            fi

            # Check for idle timeout
            if [ -f .cadi/last_activity ]; then
                # Read file atomically to avoid race condition with hook writing
                ACTIVITY_CONTENT=$(cat .cadi/last_activity 2>/dev/null)
                LAST_EPOCH=$(echo "$ACTIVITY_CONTENT" | cut -d'|' -f1 | tr -d '\n')
                LAST_TOOL=$(echo "$ACTIVITY_CONTENT" | cut -d'|' -f2 | tr -d '\n')
                NOW_EPOCH=$(date '+%s')

                # Validate LAST_EPOCH is a number before arithmetic
                if [[ "$LAST_EPOCH" =~ ^[0-9]+$ ]]; then
                    IDLE_TIME=$((NOW_EPOCH - LAST_EPOCH))

                    if [ $IDLE_TIME -gt $IDLE_TIMEOUT ]; then
                        echo -e "  ${YELLOW}${BULLET} No activity for ${IDLE_TIME}s (last: $LAST_TOOL)${NC}"
                        echo -e "  ${YELLOW}${BULLET} Killing idle Claude process...${NC}"
                        kill $CLAUDE_PID 2>/dev/null || true
                        wait $CLAUDE_PID 2>/dev/null || true
                        TIMED_OUT=true
                        break
                    fi
                fi
            fi
        done

        # Get exit code if not killed
        # Note: Use || to prevent set -e from exiting on non-zero Claude exit codes
        if [ "$NATURAL_STOP_BREAK" = true ]; then
            # Natural stop - treat as success, already waited above
            CLAUDE_EXIT=0
            CLAUDE_SUCCESS=true
            CLAUDE_OUTPUT=$(cat "$CLAUDE_OUTPUT_FILE" 2>/dev/null || echo "")
            rm -f "$CLAUDE_OUTPUT_FILE"
            break  # Exit retry loop, continue to next iteration
        elif [ "$TIMED_OUT" = false ]; then
            CLAUDE_EXIT=0
            wait $CLAUDE_PID || CLAUDE_EXIT=$?
        else
            CLAUDE_EXIT=124  # Use timeout exit code
        fi

        CLAUDE_OUTPUT=$(cat "$CLAUDE_OUTPUT_FILE")
        rm -f "$CLAUDE_OUTPUT_FILE"

        # Check for idle timeout
        if [ "$TIMED_OUT" = true ]; then
            echo -e "  ${YELLOW}${BULLET} Claude was idle too long (attempt $retry/$MAX_RETRIES)${NC}"
            if [ $retry -lt $MAX_RETRIES ]; then
                echo -e "  ${DIM}Retrying in ${RETRY_DELAY}s...${NC}"
                sleep $RETRY_DELAY
                RETRY_DELAY=$((RETRY_DELAY * 2))
                continue
            fi
        fi

        # Check for known transient errors
        if echo "$CLAUDE_OUTPUT" | grep -q "No messages returned"; then
            echo -e "  ${YELLOW}${BULLET} API returned no messages (attempt $retry/$MAX_RETRIES)${NC}"
            if [ $retry -lt $MAX_RETRIES ]; then
                echo -e "  ${DIM}Retrying in ${RETRY_DELAY}s...${NC}"
                sleep $RETRY_DELAY
                RETRY_DELAY=$((RETRY_DELAY * 2))  # Exponential backoff
                continue
            fi
        elif [ $CLAUDE_EXIT -ne 0 ] && [ -z "$CLAUDE_OUTPUT" ]; then
            echo -e "  ${YELLOW}${BULLET} Claude exited with code $CLAUDE_EXIT, no output (attempt $retry/$MAX_RETRIES)${NC}"
            if [ $retry -lt $MAX_RETRIES ]; then
                echo -e "  ${DIM}Retrying in ${RETRY_DELAY}s...${NC}"
                sleep $RETRY_DELAY
                RETRY_DELAY=$((RETRY_DELAY * 2))
                continue
            fi
        else
            # Success or non-retryable error
            CLAUDE_SUCCESS=true
            echo "$CLAUDE_OUTPUT"
            break
        fi
    done

    if [ "$CLAUDE_SUCCESS" = false ]; then
        echo -e "  ${RED}${CROSS} Claude failed after $MAX_RETRIES attempts${NC}"
        echo -e "  ${DIM}Last output:${NC}"
        echo "$CLAUDE_OUTPUT" | head -20
        echo ""
        echo -e "  ${YELLOW}Continuing to next iteration...${NC}"
    fi

    # Check for natural stop after Claude completes
    if check_natural_stop; then
        echo -e "  ${GREEN}${CHECK} Natural stop detected - continuing to next task...${NC}"
    fi

    echo ""
    echo -e "${DIM}  ─── End of iteration $i ───${NC}"
    echo ""

    # Shorter sleep between iterations when natural stop detected
    if [ "$NATURAL_STOP_DETECTED" = true ]; then
        sleep 1
    else
        sleep 2
    fi
done

# Mark run as max iterations reached
sqlite3 "$DB" "UPDATE runs SET status = 'max_iterations', completed_at = CURRENT_TIMESTAMP WHERE id = $RUN_ID;"

print_max_iterations
print_status "Run ID" "$RUN_ID" "$YELLOW"
print_status "Max Iterations" "$MAX_ITERATIONS" "$RED"
echo ""
exit 1
