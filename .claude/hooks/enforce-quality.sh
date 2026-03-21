#!/bin/bash
# TeammateIdle hook: enforce quality gates before teammate finishes.
# Checks which files were changed and runs relevant linters/tests.
# Exit 0 = allow completion, exit 2 = block and send feedback.
set -euo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
cd "$PROJECT_DIR"

ERRORS=""

# Detect changed files (unstaged + staged)
CHANGED_PY=$(git diff --name-only --diff-filter=ACMR HEAD -- '*.py' 2>/dev/null || true)
CHANGED_TS=$(git diff --name-only --diff-filter=ACMR HEAD -- '*.ts' '*.tsx' '*.js' '*.jsx' 2>/dev/null || true)
CHANGED_MDX=$(git diff --name-only --diff-filter=ACMR HEAD -- '*.mdx' 2>/dev/null || true)

# Python quality gates
if [ -n "$CHANGED_PY" ]; then
  if ! uv run ruff check --quiet 2>&1; then
    ERRORS="${ERRORS}\n- Ruff lint errors found. Run: uv run ruff check --fix"
  fi

  if ! uv run mypy --no-error-summary $CHANGED_PY 2>&1; then
    ERRORS="${ERRORS}\n- MyPy type errors found in changed files"
  fi

  # Run tests related to changed files (fast check)
  CHANGED_MODULES=$(echo "$CHANGED_PY" | grep -v '__pycache__' | head -5)
  if [ -n "$CHANGED_MODULES" ]; then
    if ! uv run pytest --co -q 2>/dev/null | head -1 | grep -q "no tests"; then
      if ! uv run pytest -x --timeout=60 -q 2>&1 | tail -5; then
        ERRORS="${ERRORS}\n- Pytest failures detected"
      fi
    fi
  fi
fi

# TypeScript/JS quality gates (for UI changes)
if [ -n "$CHANGED_TS" ]; then
  UI_DIR="$PROJECT_DIR/eventum/ui"
  if [ -d "$UI_DIR" ]; then
    cd "$UI_DIR"
    if ! npx eslint --quiet $CHANGED_TS 2>&1; then
      ERRORS="${ERRORS}\n- ESLint errors in TypeScript files"
    fi
    cd "$PROJECT_DIR"
  fi
fi

# Docs quality gate (build check for MDX changes)
if [ -n "$CHANGED_MDX" ]; then
  DOCS_DIR="$PROJECT_DIR/../docs"
  if [ -d "$DOCS_DIR" ]; then
    cd "$DOCS_DIR"
    if ! pnpm build 2>&1 | tail -3; then
      ERRORS="${ERRORS}\n- Docs build failed after MDX changes"
    fi
    cd "$PROJECT_DIR"
  fi
fi

# Report results
if [ -n "$ERRORS" ]; then
  echo -e "Quality gate FAILED. Fix these issues before completing:$ERRORS"
  exit 2
fi

exit 0
