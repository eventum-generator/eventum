#!/usr/bin/env bash
# Stop hook: run mypy on Python files modified in the current session.
#
# Loop protection:
#   1. stop_hook_active guard - gives Claude exactly one chance to fix issues,
#      then exits silently to let the turn end.
#   2. Silent exit on clean runs - no stdout/stderr output when everything
#      passes, preventing the empty-output loop documented in memory.
#
# Diff base: merge-base with develop. This covers all commits on the current
# feature branch plus uncommitted changes. On develop directly it degrades to
# uncommitted only (known limitation).

set -uo pipefail

# Prevent uv warnings when the caller has VIRTUAL_ENV from another venv
unset VIRTUAL_ENV

input=$(cat)

# Loop guard: second+ invocation in a Stop chain exits silently
stop_hook_active=$(echo "$input" | python3 -c 'import sys, json; print("true" if json.load(sys.stdin).get("stop_hook_active", False) else "false")')
if [[ "$stop_hook_active" == "true" ]]; then
    exit 0
fi

cd "$CLAUDE_PROJECT_DIR"

# Diff base: merge-base with develop if available, otherwise HEAD
diff_base=$(git merge-base HEAD develop 2>/dev/null || echo HEAD)

# Collect modified Python files in the eventum package (skip deleted -
# mypy would fail on paths that no longer exist)
py_files=$( { git diff --name-only --diff-filter=d "$diff_base" 2>/dev/null; \
              git diff --name-only --diff-filter=d --cached 2>/dev/null; } \
           | sort -u | grep -E '^eventum/.*\.py$' || true)

if [[ -z "$py_files" ]]; then
    exit 0
fi

mypy_out=$(echo "$py_files" | xargs timeout 90 uv run mypy 2>&1)
mypy_rc=$?

if [[ $mypy_rc -ne 0 ]]; then
    echo "[python-typecheck] mypy failures:" >&2
    echo "$mypy_out" >&2
    exit 2
fi

exit 0
