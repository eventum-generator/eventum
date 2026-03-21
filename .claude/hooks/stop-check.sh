#!/bin/bash
# Stop hook: verify that changed files have been properly validated.
# Reads the stop_hook_active JSON from stdin.
# Exit 0 = allow stop, exit 2 = force continuation with feedback.
set -euo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
cd "$PROJECT_DIR"

ISSUES=""

# Get files changed since last commit (working tree)
CHANGED_PY=$(git diff --name-only HEAD -- '*.py' 2>/dev/null || true)
CHANGED_TS=$(git diff --name-only HEAD -- '*.ts' '*.tsx' 2>/dev/null || true)
CHANGED_MDX=$(git diff --name-only HEAD -- '*.mdx' 2>/dev/null || true)
CHANGED_JINJA=$(git diff --name-only HEAD -- '*.jinja' '*.json.jinja' 2>/dev/null || true)

# No changes = nothing to check
if [ -z "$CHANGED_PY" ] && [ -z "$CHANGED_TS" ] && [ -z "$CHANGED_MDX" ] && [ -z "$CHANGED_JINJA" ]; then
  exit 0
fi

# Check: Python changed but ruff not run recently
if [ -n "$CHANGED_PY" ]; then
  if ! uv run ruff check --quiet $CHANGED_PY 2>/dev/null; then
    ISSUES="${ISSUES}\n- Python files changed but have lint errors. Run: uv run ruff check --fix"
  fi
fi

# Check: MDX changed but docs not built
if [ -n "$CHANGED_MDX" ]; then
  DOCS_DIR="$PROJECT_DIR/../docs"
  if [ -d "$DOCS_DIR" ]; then
    # Quick check: try build, capture exit code
    if ! (cd "$DOCS_DIR" && pnpm build --no-clean 2>&1 | tail -1 | grep -q "Export successful"); then
      ISSUES="${ISSUES}\n- MDX files changed but docs build not verified. Run: cd ../docs && pnpm build"
    fi
  fi
fi

# Check: cross-cutting — plugin files changed, check if related UI/docs also changed
if [ -n "$CHANGED_PY" ]; then
  PLUGIN_CHANGES=$(echo "$CHANGED_PY" | grep 'eventum/plugins/' || true)
  if [ -n "$PLUGIN_CHANGES" ]; then
    # Check if any Zod/UI files were also modified
    ZOD_CHANGES=$(git diff --name-only HEAD -- 'eventum/ui/src/api/routes/generator-configs/schemas/' 2>/dev/null || true)
    if [ -z "$ZOD_CHANGES" ]; then
      ISSUES="${ISSUES}\n- Plugin files changed but no Zod schema updates detected. Check cross-cutting checklist."
    fi
  fi
fi

# Check: generator templates changed but not validated
if [ -n "$CHANGED_JINJA" ]; then
  ISSUES="${ISSUES}\n- Generator templates changed. Verify with: eventum generate --path <generator.yml> --id test"
fi

if [ -n "$ISSUES" ]; then
  echo -e "Before finishing, address these items:$ISSUES"
  exit 2
fi

exit 0
