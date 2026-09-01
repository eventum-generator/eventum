#!/usr/bin/env python3
"""Run the canonical format hooks for files edited by Claude or Codex."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

_PATH_PATTERN = re.compile(
    r'^\*\*\* (?:Add|Update) File: (?P<path>.+)$|'
    r'^\*\*\* Move to: (?P<move_path>.+)$',
    re.MULTILINE,
)

# Codex may deliver a patch nested in source code, where the newlines are
# still escaped. Unescape them so the line-anchored pattern can match.
_ESCAPED_NEWLINE = re.compile(r'\\+n')

# An agent driving the shell writes files through a redirection or an
# in-place edit. Reading a file must not match, or every test run would
# lint its target.
_REDIRECT_PATTERN = re.compile(
    r"(?:>>?|\btee\b(?:\s+-\S+)*)\s*['\"]?(?P<path>[\w./@+-]+)",
)
_SEGMENT_PATTERN = re.compile(r'[|;&\n]+')
_SED_INPLACE_PATTERN = re.compile(r'\bsed\b.*\s-{1,2}i')
_TOKEN_PATTERN = re.compile(r"['\"]?(?P<path>[\w./@+-]+)['\"]?")


def _tool(name: str, fallback: str) -> str:
    """Return the absolute path of a required external tool."""
    return shutil.which(name) or fallback


def _project_root(cwd: Path) -> Path | None:
    """Return the Git root for the active agent session."""
    try:
        result = subprocess.run(  # noqa: S603
            [_tool('git', '/usr/bin/git'), 'rev-parse', '--show-toplevel'],
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None

    if result.returncode != 0:
        return None

    return Path(result.stdout.strip()).resolve()


def _existing_path(value: str, root: Path, cwd: Path) -> Path | None:
    """Resolve an existing project file from a hook payload path."""
    candidate = Path(value)
    bases = (cwd, root) if not candidate.is_absolute() else (None,)

    for base in bases:
        resolved = (base / candidate if base else candidate).resolve()
        if resolved.is_relative_to(root) and resolved.is_file():
            return resolved
    return None


def _strings(value: Any) -> Iterator[str]:
    """Yield every string nested anywhere inside a hook payload value."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        yield from (s for v in value.values() for s in _strings(v))
    elif isinstance(value, list | tuple):
        yield from (s for v in value for s in _strings(v))


def _shell_written(command: str, root: Path, cwd: Path) -> set[Path]:
    """Return project files a shell command writes to."""
    written: set[Path] = set()

    for segment in _SEGMENT_PATTERN.split(command):
        candidates = [
            m.group('path') for m in _REDIRECT_PATTERN.finditer(segment)
        ]

        # sed names its target as a plain argument, so an in-place run is
        # the only case where every token of the segment is worth testing.
        if _SED_INPLACE_PATTERN.search(segment):
            candidates += [
                m.group('path') for m in _TOKEN_PATTERN.finditer(segment)
            ]

        for value in candidates:
            resolved = _existing_path(value, root, cwd)
            if resolved is not None:
                written.add(resolved)

    return written


def _edited_paths(event: dict[str, Any], root: Path, cwd: Path) -> list[Path]:
    """Extract files from Claude path input or a Codex patch input."""
    paths: set[Path] = set()
    tool_input = event.get('tool_input')

    if isinstance(tool_input, dict):
        file_path = tool_input.get('file_path')
        if isinstance(file_path, str):
            candidate = _existing_path(file_path, root, cwd)
            if candidate is not None:
                paths.add(candidate)

    # Codex carries the patch as text, and its shape varies by tool: a bare
    # string, a list of command arguments, or a field of a structured call.
    for text in _strings(tool_input):
        unescaped = _ESCAPED_NEWLINE.sub('\n', text)

        for match in _PATH_PATTERN.finditer(unescaped):
            value = match.group('path') or match.group('move_path')
            candidate = _existing_path(value.strip(), root, cwd)
            if candidate is not None:
                paths.add(candidate)

        paths.update(_shell_written(unescaped, root, cwd))

    return sorted(paths)


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
            [_tool('bash', '/bin/bash'), str(hook)],
            input=payload,
            text=True,
            capture_output=True,
            env=environment,
            check=False,
        )
    except OSError:
        return None


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
    root = _project_root(cwd)
    if root is None:
        return 0

    hooks = (
        root / '.agents/hooks/python-format-lint.sh',
        root / '.agents/hooks/ts-format-lint.sh',
    )
    failures: list[str] = []

    for file_path in _edited_paths(event, root, cwd):
        for hook in hooks:
            if not hook.is_file():
                continue

            result = _run_hook(hook, file_path, root)
            if result is not None and result.returncode != 0:
                message = result.stderr.strip() or result.stdout.strip()
                fallback = f'{hook.name} exited {result.returncode}'
                failures.append(message or fallback)

    if failures:
        sys.stderr.write('\n'.join(failures))
        sys.stderr.write('\n')
        return 2
    return 0


if __name__ == '__main__':
    try:
        _code = main()
    except Exception as error:  # noqa: BLE001 - a hook must never block the agent
        sys.stderr.write(f'post-edit.py: {error}\n')
        _code = 0

    raise SystemExit(_code)
