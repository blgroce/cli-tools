#!/bin/bash
set -e

# Set working directory to project root (parent of .cadi)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

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

## Variables
DB=".cadi/cadi-project.sqlite"

# Function to print the CADI banner (planning variant)
print_banner() {
    echo ""
    echo -e "${MAGENTA}"
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
    echo -e "    |       ${WHITE}Autonomous Feature Planning${MAGENTA}              |"
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
    echo -e "${MAGENTA}┌──────────────────────────────────────────────────┐${NC}"
    printf "${MAGENTA}│${NC}%*s${BOLD}%s${NC}%*s${MAGENTA}│${NC}\n" $padding "" "$title" $((width - padding - ${#title})) ""
    echo -e "${MAGENTA}└──────────────────────────────────────────────────┘${NC}"
}

# Function to print a status line
print_status() {
    local label="$1"
    local value="$2"
    local color="${3:-$GREEN}"
    printf "  ${DIM}%-18s${NC} ${color}%s${NC}\n" "$label:" "$value"
}

# Function to print completion status
print_complete() {
    local run_id="$1"
    local task_count="$2"
    echo ""
    echo -e "${GREEN}"
    echo "   ╔════════════════════════════════════════════════╗"
    echo "   ║                                                ║"
    echo "   ║         ✓  PLANNING COMPLETE  ✓                ║"
    echo "   ║                                                ║"
    echo -e "   ║  ${WHITE}Run $run_id created with $task_count tasks${GREEN}              ║"
    echo "   ║                                                ║"
    echo "   ╚════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Function to print error
print_error() {
    local message="$1"
    echo ""
    echo -e "  ${RED}${CROSS} Error:${NC} $message"
    echo ""
}

# Function to print note
print_note() {
    local message="$1"
    echo -e "  ${YELLOW}${BULLET}${NC} ${DIM}$message${NC}"
}

### Parse arguments
DEBUG_MODE=false
VERBOSE_MODE=false
SKIP_PERMISSIONS=true  # Default to skipping permissions for headless operation
DESCRIPTION=""

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
        --description|-d)
            DESCRIPTION="$2"
            shift 2
            ;;
        *)
            # If no flag, treat as description
            if [ -z "$DESCRIPTION" ]; then
                DESCRIPTION="$1"
            fi
            shift
            ;;
    esac
done

### Validate description
if [ -z "$DESCRIPTION" ]; then
    print_banner
    print_error "Please provide a feature description"
    echo -e "  ${DIM}Usage:${NC} ${BOLD}plan_loop.sh${NC} ${CYAN}<description>${NC} [options]"
    echo -e "         ${BOLD}plan_loop.sh${NC} ${CYAN}--description \"<description>\"${NC} [options]"
    echo ""
    echo -e "  ${DIM}Options:${NC}"
    echo -e "    ${CYAN}--debug${NC}              Enable Claude debug mode"
    echo -e "    ${CYAN}--verbose${NC}            Enable Claude verbose mode"
    echo -e "    ${CYAN}--ask-permissions${NC}    Enable permission prompts (alias: --no-yolo)"
    echo -e "    ${DIM}Note: Permissions are skipped by default for headless operation${NC}"
    echo ""
    echo -e "  ${DIM}Example:${NC}"
    echo -e "    ${CYAN}plan_loop.sh \"Add user authentication with JWT tokens\"${NC}"
    echo ""
    exit 1
fi

# Verify prompt file exists
PLAN_PROMPT=".cadi/prompts/PLAN_PROMPT.md"
if [ ! -f "$PLAN_PROMPT" ]; then
    print_banner
    print_error "$PLAN_PROMPT not found"
    exit 1
fi

# Display startup info
print_banner

print_header "PLANNING SESSION"
echo ""
print_status "Mode" "Planning" "$MAGENTA"
print_status "Description" "${DESCRIPTION:0:40}..." "$CYAN"
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

echo -e "  ${DIM}Press ${WHITE}Ctrl+C${DIM} to abort${NC}"
echo ""

# Build Claude prompt
PLAN_CONTENT=$(cat "$PLAN_PROMPT")

FULL_PROMPT="# Feature Planning Request

## Feature Description

$DESCRIPTION

---

$PLAN_CONTENT"

# Build Claude command with flags
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

echo -e "  ${DIM}Invoking Claude for planning...${NC}"
echo ""

# Run Claude and capture output
# We stream output to both stdout and capture it for parsing
CLAUDE_OUTPUT_FILE=$(mktemp)

# Run Claude, tee output to both terminal and file
# Use stdbuf to disable buffering for real-time streaming
stdbuf -oL -eL claude -p "$FULL_PROMPT" $CLAUDE_FLAGS 2>&1 | stdbuf -oL tee "$CLAUDE_OUTPUT_FILE"

CLAUDE_EXIT=${PIPESTATUS[0]}

# Read captured output
CLAUDE_OUTPUT=$(cat "$CLAUDE_OUTPUT_FILE")
rm -f "$CLAUDE_OUTPUT_FILE"

# Check for success
if [ $CLAUDE_EXIT -ne 0 ]; then
    print_error "Claude exited with code $CLAUDE_EXIT"
    exit 1
fi

# Strip ANSI escape codes from output for reliable parsing
CLEAN_OUTPUT=$(echo "$CLAUDE_OUTPUT" | sed 's/\x1b\[[0-9;]*m//g')

# Parse output for run_id
# Look for the [PLANNING_COMPLETE] block and extract values
# Note: RUN_ID= might appear before or after the marker, so search the whole output
if echo "$CLEAN_OUTPUT" | grep -q '\[PLANNING_COMPLETE\]'; then
    # Extract RUN_ID and TASK_COUNT from anywhere in the output
    RUN_ID=$(echo "$CLEAN_OUTPUT" | grep -oE 'RUN_ID=[0-9]+' | head -1 | sed 's/RUN_ID=//')
    TASK_COUNT=$(echo "$CLEAN_OUTPUT" | grep -oE 'TASK_COUNT=[0-9]+' | head -1 | sed 's/TASK_COUNT=//')

    if [ -n "$RUN_ID" ]; then
        echo ""
        print_complete "$RUN_ID" "$TASK_COUNT"

        # Output structured result for backend to capture
        echo ""
        echo "PLAN_RESULT:RUN_ID=$RUN_ID"
        echo "PLAN_RESULT:TASK_COUNT=$TASK_COUNT"
        echo "PLAN_RESULT:STATUS=success"
        exit 0
    fi
fi

# If we got here, planning may have succeeded but output format wasn't as expected
# Check if any run was created by looking at recent runs
RECENT_RUN=$(sqlite3 "$DB" "SELECT id FROM runs ORDER BY id DESC LIMIT 1;" 2>/dev/null || echo "")

if [ -n "$RECENT_RUN" ]; then
    RECENT_TASK_COUNT=$(sqlite3 "$DB" "SELECT COUNT(*) FROM tasks WHERE run_id = $RECENT_RUN;" 2>/dev/null || echo "0")

    if [ "$RECENT_TASK_COUNT" -gt 0 ]; then
        echo ""
        print_note "Planning completed but output format unexpected"
        print_note "Most recent run: $RECENT_RUN with $RECENT_TASK_COUNT tasks"

        echo ""
        echo "PLAN_RESULT:RUN_ID=$RECENT_RUN"
        echo "PLAN_RESULT:TASK_COUNT=$RECENT_TASK_COUNT"
        echo "PLAN_RESULT:STATUS=success"
        exit 0
    fi
fi

# If truly failed
print_error "Planning did not create a run"
echo "PLAN_RESULT:STATUS=failed"
exit 1
