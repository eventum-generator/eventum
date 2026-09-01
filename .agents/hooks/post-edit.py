#!/usr/bin/env python3
"""Run the canonical format hooks for files edited by Claude or Codex."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from _payload import edited_paths, project_root, tool


def _run_hook(
    hook: Path,
    file_path: Path,
    root: Path,
) -> subprocess.CompletedProcess[str] | None:
    """Run one canonical edit hook with a Claude-compatible payload.

    Returns None when the hook could not be started at all, which must
    leave the agent running rather than surface as an edit failure.
    """
    payload = json.dumps({'tool_input': {'file_path': str(file_path)}})
    environment = os.environ.copy()
    environment['CLAUDE_PROJECT_DIR'] = str(root)

    try:
        return subprocess.run(  # noqa: S603
            [tool('bash', '/bin/bash'), str(hook)],
            input=payload,
            text=True,
            capture_output=True,
            env=environment,
            check=False,
        )
    except OSError:
        return None


def _digest(file_path: Path) -> bytes | None:
    """Return a content digest, or None when the file cannot be read."""
    try:
        return hashlib.sha256(file_path.read_bytes()).digest()
    except OSError:
        return None


def _report_reformatted(files: list[str]) -> None:
    """Tell the agent the formatter rewrote what it just wrote.

    Without this the rewrite is invisible, and an agent whose edit the
    formatter undid retries it instead of accepting the result.
    """
    listed = ', '.join(files)
    json.dump(
        {
            'hookSpecificOutput': {
                'hookEventName': 'PostToolUse',
                'additionalContext': (
                    f'The project formatter rewrote {listed} after your '
                    f'edit. That formatting is authoritative - read the '
                    f'file if you need its current content, and do not '
                    f'reapply an edit it removed.'
                ),
            },
        },
        sys.stdout,
    )


def _process(
    files: list[Path],
    root: Path,
) -> tuple[list[str], list[str]]:
    """Format and lint each file, reporting failures and rewrites."""
    hooks = (
        root / '.agents/hooks/python-format-lint.sh',
        root / '.agents/hooks/ts-format-lint.sh',
    )
    failures: list[str] = []
    reformatted: list[str] = []

    for file_path in files:
        before = _digest(file_path)

        for hook in hooks:
            if not hook.is_file():
                continue

            result = _run_hook(hook, file_path, root)
            if result is not None and result.returncode != 0:
                message = result.stderr.strip() or result.stdout.strip()
                fallback = f'{hook.name} exited {result.returncode}'
                failures.append(message or fallback)

        if before is not None and _digest(file_path) != before:
            reformatted.append(str(file_path.relative_to(root)))

    return failures, reformatted


def main() -> int:
    """Format and lint files edited by Claude or Codex."""
    try:
        event = json.load(sys.stdin)
    except ValueError:
        # A payload this hook cannot read must not block the agent.
        return 0

    if not isinstance(event, dict):
        return 0

    cwd = Path(event.get('cwd') or Path.cwd()).resolve()
    root = project_root(cwd)
    if root is None:
        return 0

    failures, reformatted = _process(edited_paths(event, root, cwd), root)

    if failures:
        sys.stderr.write('\n'.join(failures))
        sys.stderr.write('\n')
        return 2

    if reformatted:
        _report_reformatted(reformatted)

    return 0


if __name__ == '__main__':
    try:
        _code = main()
    except Exception as error:  # noqa: BLE001 - a hook must never block the agent
        sys.stderr.write(f'post-edit.py: {error}\n')
        _code = 0

    raise SystemExit(_code)
