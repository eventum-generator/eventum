#!/bin/bash
set -e

FILE_PATH=$(python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('file_path',''))")

[ -z "$FILE_PATH" ] && exit 0

# Python: ruff format + lint fix
if [[ "$FILE_PATH" == *.py ]]; then
  ruff format "$FILE_PATH" &>/dev/null || true
  ruff check --fix "$FILE_PATH" &>/dev/null || true
# TypeScript/JavaScript: prettier + eslint fix
elif [[ "$FILE_PATH" =~ \.(ts|tsx|js|jsx)$ ]]; then
  npx prettier --write "$FILE_PATH" &>/dev/null || true
  npx eslint --fix "$FILE_PATH" &>/dev/null || true
fi

exit 0
