#!/bin/bash

# Diagnostic Agent CLI Wrapper Script
# Makes it easy to interact with the diagnostic agent

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLI_SCRIPT="$SCRIPT_DIR/cli_prompt.py"

# Default host (can be overridden with environment variable)
DEFAULT_HOST="${DIAGNOSTIC_AGENT_HOST:-localhost}"
DEFAULT_PORT="${DIAGNOSTIC_AGENT_PORT:-5000}"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if Python script exists
if [ ! -f "$CLI_SCRIPT" ]; then
    echo -e "${RED}Error: CLI script not found at $CLI_SCRIPT${NC}"
    exit 1
fi

# Show usage if no arguments
if [ $# -eq 0 ]; then
    echo -e "${GREEN}Diagnostic Agent CLI${NC}"
    echo ""
    echo "Usage:"
    echo "  $0 \"Your question here\"                    # Ask a single question"
    echo "  $0 --interactive                           # Start interactive mode"
    echo "  $0 --status                                # Check agent status"
    echo ""
    echo "Options:"
    echo "  --host HOST      Host where agent is running (default: $DEFAULT_HOST)"
    echo "  --port PORT      Port where agent is listening (default: $DEFAULT_PORT)"
    echo "  --verbose        Enable debug output"
    echo ""
    echo "Examples:"
    echo "  $0 \"What is the system status?\""
    echo "  $0 \"Check network connectivity\""
    echo "  $0 \"Scan for running processes\""
    echo "  $0 --interactive"
    echo "  $0 --host 192.168.1.100 \"System health check\""
    echo ""
    exit 0
fi

# Execute the Python CLI script with all arguments
python3 "$CLI_SCRIPT" --host "$DEFAULT_HOST" --port "$DEFAULT_PORT" "$@"
