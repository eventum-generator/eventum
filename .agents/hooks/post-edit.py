#!/usr/bin/env python3
"""Run the canonical format hooks for files edited by Claude or Codex."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

_PATH_PATTERN = re.compile(
    r'^\*\*\* (?:Add|Update) File: (?P<path>.+)$|'
    r'^\*\*\* Move to: (?P<move_path>.+)$',
    re.MULTILINE,
)


def _project_root(event: dict[str, Any]) -> Path:
    """Return the Git root for the active agent session."""
    cwd = event.get('cwd') or Path.cwd()
    result = subprocess.run(
        ['/usr/bin/git', 'rev-parse', '--show-toplevel'],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
    return Path(result.stdout.strip()).resolve()


def _existing_path(value: str, root: Path) -> Path | None:
    """Resolve an existing project file from a hook payload path."""
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = root / candidate
    candidate = candidate.resolve()
    if candidate.is_relative_to(root) and candidate.is_file():
        return candidate
    return None


def _edited_paths(event: dict[str, Any], root: Path) -> list[Path]:
    """Extract files from Claude path input or a Codex patch input."""
    paths: set[Path] = set()
    tool_input = event.get('tool_input', {})
    commands: list[str] = []

    if isinstance(tool_input, dict):
        file_path = tool_input.get('file_path')
        if isinstance(file_path, str):
            candidate = _existing_path(file_path, root)
            if candidate is not None:
                paths.add(candidate)

        for key in ('command', 'input', 'patch'):
            value = tool_input.get(key)
            if isinstance(value, str):
                commands.append(value)
    elif isinstance(tool_input, str):
        commands.append(tool_input)

    for command in commands:
        for match in _PATH_PATTERN.finditer(command):
            value = match.group('path') or match.group('move_path')
            candidate = _existing_path(value, root)
            if candidate is not None:
                paths.add(candidate)
    return sorted(paths)


def _run_hook(
    hook: Path,
    file_path: Path,
    root: Path,
) -> subprocess.CompletedProcess[str]:
    """Run one canonical edit hook with a Claude-compatible payload."""
    payload = json.dumps({'tool_input': {'file_path': str(file_path)}})
    environment = os.environ.copy()
    environment['CLAUDE_PROJECT_DIR'] = str(root)
    return subprocess.run(  # noqa: S603
        ['/usr/bin/bash', str(hook)],
        input=payload,
        text=True,
        capture_output=True,
        env=environment,
        check=False,
    )


def main() -> int:
    """Format and lint files edited by Claude or Codex."""
    event = json.load(sys.stdin)
    root = _project_root(event)
    hooks = (
        root / '.agents/hooks/python-format-lint.sh',
        root / '.agents/hooks/ts-format-lint.sh',
    )
    failures: list[str] = []

    for file_path in _edited_paths(event, root):
        for hook in hooks:
            result = _run_hook(hook, file_path, root)
            if result.returncode != 0:
                message = result.stderr.strip() or result.stdout.strip()
                fallback = f'{hook.name} exited {result.returncode}'
                failures.append(message or fallback)

    if failures:
        sys.stderr.write('\n'.join(failures))
        sys.stderr.write('\n')
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
