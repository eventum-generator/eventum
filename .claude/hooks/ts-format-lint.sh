#!/usr/bin/env bash
# PostToolUse hook: format and auto-fix lint for TypeScript files in eventum/ui.
# Format failures never block (prettier piped to /dev/null).
# Remaining lint issues after eslint --fix exit 2 so Claude sees them as
# actionable feedback in the PostToolUse blocking-error channel.

set -uo pipefail

input=$(cat)
file_path=$(echo "$input" | python3 -c 'import sys, json; print(json.load(sys.stdin).get("tool_input", {}).get("file_path", ""))')

# Scope: .ts or .tsx files inside eventum/ui
[[ "$file_path" =~ \.(ts|tsx)$ ]] || exit 0
[[ "$file_path" == "$CLAUDE_PROJECT_DIR/eventum/ui/"* ]] || exit 0
[[ -f "$file_path" ]] || exit 0

cd "$CLAUDE_PROJECT_DIR/eventum/ui"

# Prettier first (order matters: prettier must run before eslint)
timeout 15 pnpm exec prettier --write "$file_path" >/dev/null 2>&1 || true

# ESLint with auto-fix and cache (~1.5s warm vs ~5s uncached)
lint_out=$(timeout 30 pnpm exec eslint --fix --cache --cache-location .eslintcache "$file_path" 2>&1 || true)
if [[ -n "$lint_out" ]]; then
    echo "[ts-format-lint]" >&2
    echo "$lint_out" >&2
    # exit 2 surfaces stderr as blocking-error context to Claude
    exit 2
fi

exit 0
