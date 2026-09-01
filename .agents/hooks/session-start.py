#!/usr/bin/env python3
"""Check the shared agent layout and hand the rules to agents that need them.

Claude Code discovers `.claude/rules/**` on its own; Codex does not, so
it gets an index of them here and the matching bodies before each edit.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

_SKILLS_DIR = Path('.claude/skills')
_RULES_DIR = Path('.claude/rules')
_HOOKS_DIR = Path('.agents/hooks')
_LINK_SIZE_LIMIT = 512

_RULES_HEADER = (
    'Project rules live in `.claude/rules/` and are binding for this '
    'repository, alongside AGENTS.md. The ones covering a file are handed '
    'to you before you edit it; read any other listed here when its area '
    'is relevant.'
)


def _project_root(cwd: Path) -> Path | None:
    """Return the Git root for the active agent session."""
    try:
        result = subprocess.run(  # noqa: S603
            [shutil.which('git') or 'git', 'rev-parse', '--show-toplevel'],
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


def _is_unmaterialised_link(entry: Path) -> bool:
    """Tell an unresolved symlink apart from an unrelated loose file."""
    try:
        if entry.stat().st_size > _LINK_SIZE_LIMIT:
            return False

        content = entry.read_text(encoding='utf-8')
    except OSError:
        return False
    except ValueError:
        return False

    return '\n' not in content.strip() and _HOOKS_DIR.parts[0] in content


def _broken_links(root: Path) -> list[str]:
    """Return layout entries a checkout failed to materialise.

    A checkout without symlink support turns every link into a text file
    holding its target path, which silently disables skills and hooks.
    """
    broken: list[str] = []

    skills_dir = root / _SKILLS_DIR
    try:
        entries = sorted(skills_dir.iterdir()) if skills_dir.is_dir() else []
    except OSError:
        entries = []

    for entry in entries:
        if entry.is_dir():
            if not (entry / 'SKILL.md').is_file():
                broken.append(str(entry.relative_to(root)))
        elif _is_unmaterialised_link(entry):
            broken.append(str(entry.relative_to(root)))

    if not (root / _HOOKS_DIR).is_dir():
        broken.append(str(_HOOKS_DIR))

    return broken


def _rules(root: Path) -> str:
    """Return an index of the project rules and what each one covers."""
    entries: list[str] = []

    for path in sorted((root / _RULES_DIR).rglob('*.md')):
        try:
            lines = path.read_text(encoding='utf-8').splitlines()
        except OSError:
            continue
        except ValueError:
            continue

        title = next(
            (
                line.lstrip('# ').strip()
                for line in lines
                if line.startswith('# ')
            ),
            path.stem,
        )
        entries.append(f'- {path.relative_to(root)} - {title}')

    if not entries:
        return ''

    return '\n'.join([_RULES_HEADER, '', *entries])


def main(argv: list[str]) -> int:
    """Emit rules and layout warnings as SessionStart hook output."""
    try:
        event = json.load(sys.stdin)
    except ValueError:
        event = {}

    if not isinstance(event, dict):
        event = {}

    cwd = Path(event.get('cwd') or Path.cwd()).resolve()
    root = _project_root(cwd)
    if root is None:
        return 0

    output: dict[str, object] = {}

    if '--inject-rules' in argv:
        rules = _rules(root)
        if rules:
            output['hookSpecificOutput'] = {
                'hookEventName': 'SessionStart',
                'additionalContext': rules,
            }

    broken = _broken_links(root)
    if broken:
        output['systemMessage'] = (
            'Agent layout is not usable in this checkout: '
            + ', '.join(broken)
            + '. If this checkout has no symlink support, the links were '
            'stored as plain files - enable it (git config core.symlinks '
            'true) and reset the working tree.'
        )

    if output:
        json.dump(output, sys.stdout)

    return 0


if __name__ == '__main__':
    try:
        _code = main(sys.argv[1:])
    except Exception as error:  # noqa: BLE001 - a hook must never block the agent
        sys.stderr.write(f'session-start.py: {error}\n')
        _code = 0

    raise SystemExit(_code)
