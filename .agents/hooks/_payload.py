"""Read the files an agent is about to edit, or has just edited.

Claude and Codex describe an edit differently - a path field, a patch,
or a shell command - so both edit hooks share this reader.
"""

from __future__ import annotations

import re
import shutil
import subprocess
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


def tool(name: str, fallback: str) -> str:
    """Return the absolute path of a required external tool."""
    return shutil.which(name) or fallback


def project_root(cwd: Path) -> Path | None:
    """Return the Git root for the active agent session."""
    try:
        result = subprocess.run(  # noqa: S603
            [tool('git', '/usr/bin/git'), 'rev-parse', '--show-toplevel'],
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


def _existing_path(
    value: str,
    roots: tuple[Path, ...],
    cwd: Path,
) -> Path | None:
    """Resolve an existing file from a hook payload path.

    Anything outside the given roots is dropped, so a payload cannot
    point a hook at a file the agent is not working on.
    """
    candidate = Path(value)
    bases = (cwd, *roots) if not candidate.is_absolute() else (None,)

    for base in bases:
        resolved = (base / candidate if base else candidate).resolve()
        inside = any(resolved.is_relative_to(root) for root in roots)
        if inside and resolved.is_file():
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


def _shell_written(
    command: str,
    roots: tuple[Path, ...],
    cwd: Path,
) -> set[Path]:
    """Return project files a shell command writes to."""
    written: set[Path] = set()

    for segment in _SEGMENT_PATTERN.split(command):
        found = [m.group('path') for m in _REDIRECT_PATTERN.finditer(segment)]

        # sed names its target as a plain argument, so an in-place run is
        # the only case where every token of the segment is worth testing.
        if _SED_INPLACE_PATTERN.search(segment):
            found += [
                m.group('path') for m in _TOKEN_PATTERN.finditer(segment)
            ]

        for value in found:
            resolved = _existing_path(value, roots, cwd)
            if resolved is not None:
                written.add(resolved)

    return written


def edited_paths(
    event: dict[str, Any],
    root: Path,
    cwd: Path,
    extra_roots: tuple[Path, ...] = (),
) -> list[Path]:
    """Return the files an edit event refers to.

    `extra_roots` widens the search to sibling repositories the agent may
    also edit; without it only the project itself is considered.
    """
    paths: set[Path] = set()
    roots = (root, *extra_roots)
    tool_input = event.get('tool_input')

    if isinstance(tool_input, dict):
        file_path = tool_input.get('file_path')
        if isinstance(file_path, str):
            candidate = _existing_path(file_path, roots, cwd)
            if candidate is not None:
                paths.add(candidate)

    # Codex carries the patch as text, and its shape varies by tool: a bare
    # string, a list of command arguments, or a field of a structured call.
    for text in _strings(tool_input):
        unescaped = _ESCAPED_NEWLINE.sub('\n', text)

        for match in _PATH_PATTERN.finditer(unescaped):
            value = match.group('path') or match.group('move_path')
            candidate = _existing_path(value.strip(), roots, cwd)
            if candidate is not None:
                paths.add(candidate)

        paths.update(_shell_written(unescaped, roots, cwd))

    return sorted(paths)
