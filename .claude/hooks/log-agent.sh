#!/bin/bash
# SubagentStop hook: log agent activity for audit trail.
# Reads JSON from stdin with agent metadata.
# Always exits 0 (non-blocking, informational only).
set -uo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
LOG_DIR="$PROJECT_DIR/.claude/logs"
LOG_FILE="$LOG_DIR/agents.log"

mkdir -p "$LOG_DIR"

# Read stdin
INPUT=$(cat)

# Extract fields from hook payload
AGENT_ID=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('agent_id', d.get('agentId', 'unknown')))
except:
    print('unknown')
" 2>/dev/null || echo "unknown")

TIMESTAMP=$(date -u '+%Y-%m-%dT%H:%M:%SZ')

# Get files changed in working tree (proxy for what agent modified)
CHANGED_FILES=$(cd "$PROJECT_DIR" && git diff --name-only HEAD 2>/dev/null | head -20 || echo "none")
CHANGED_COUNT=$(echo "$CHANGED_FILES" | grep -c '[^[:space:]]' 2>/dev/null || echo "0")

# Log entry
cat >> "$LOG_FILE" << EOF
---
timestamp: $TIMESTAMP
agent: $AGENT_ID
files_changed: $CHANGED_COUNT
changed_files: |
$(echo "$CHANGED_FILES" | sed 's/^/  /')
EOF

# Rotate log if > 1MB
if [ -f "$LOG_FILE" ] && [ "$(stat -c%s "$LOG_FILE" 2>/dev/null || echo 0)" -gt 1048576 ]; then
  mv "$LOG_FILE" "$LOG_FILE.$(date +%Y%m%d).bak"
fi

exit 0
