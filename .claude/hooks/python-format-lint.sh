#!/usr/bin/env bash
# PostToolUse hook: format and auto-fix lint for Python files.
# Format failures never block (ruff format piped to /dev/null).
# Remaining lint issues after --fix exit 2 so Claude sees them as
# actionable feedback in the PostToolUse blocking-error channel.

set -uo pipefail

# Prevent uv warnings when the caller has VIRTUAL_ENV from another venv
unset VIRTUAL_ENV

input=$(cat)
file_path=$(echo "$input" | python3 -c 'import sys, json; print(json.load(sys.stdin).get("tool_input", {}).get("file_path", ""))')

# Scope: Python files only, inside this project
[[ "$file_path" =~ \.py$ ]] || exit 0
[[ "$file_path" == "$CLAUDE_PROJECT_DIR"/* ]] || exit 0
[[ -f "$file_path" ]] || exit 0

cd "$CLAUDE_PROJECT_DIR"

# Format silently - only output on failures
timeout 15 uv run ruff format "$file_path" >/dev/null 2>&1 || true

# Auto-fix lint issues, then report anything still remaining
lint_out=$(timeout 30 uv run ruff check --fix "$file_path" 2>&1 || true)
lint_out=$(echo "$lint_out" | grep -v "^All checks passed!" || true)
if [[ -n "$lint_out" ]]; then
    echo "[python-format-lint]" >&2
    echo "$lint_out" >&2
    # exit 2 surfaces stderr as additional context to Claude so it can fix
    # issues that ruff could not auto-fix (e.g. missing docstrings).
    exit 2
fi

exit 0
