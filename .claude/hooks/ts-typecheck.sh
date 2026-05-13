#!/usr/bin/env bash
# Stop hook: run tsc (project-wide) on the Eventum Studio UI when TypeScript
# files were modified in the current session. tsc cannot reliably type-check
# a single file in a project context, so it runs over the whole ui package.
# Uses --incremental + .tsbuildinfo cache for speed (warm run ~2.5s vs ~7.5s).
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

input=$(cat)

# Loop guard: second+ invocation in a Stop chain exits silently
stop_hook_active=$(echo "$input" | python3 -c 'import sys, json; print("true" if json.load(sys.stdin).get("stop_hook_active", False) else "false")')
if [[ "$stop_hook_active" == "true" ]]; then
    exit 0
fi

cd "$CLAUDE_PROJECT_DIR"

# Diff base: merge-base with develop if available, otherwise HEAD
diff_base=$(git merge-base HEAD develop 2>/dev/null || echo HEAD)

# Collect modified TypeScript files in the UI package
ts_files=$( { git diff --name-only "$diff_base" 2>/dev/null; \
              git diff --name-only --cached 2>/dev/null; } \
           | sort -u | grep -E '^eventum/ui/.*\.(ts|tsx)$' || true)

if [[ -z "$ts_files" ]]; then
    exit 0
fi

tsc_out=$(cd eventum/ui && timeout 120 pnpm exec tsc --noEmit --incremental --tsBuildInfoFile .tsbuildinfo 2>&1)
tsc_rc=$?

if [[ $tsc_rc -ne 0 ]]; then
    echo "[ts-typecheck] tsc failures:" >&2
    echo "$tsc_out" >&2
    exit 2
fi

exit 0
