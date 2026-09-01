#!/usr/bin/env python3
"""Hand an agent the project rules covering the file it is about to edit.

Claude Code loads `.claude/rules/**` for itself. Codex does not, so it
receives the matching rules here, once per session and only for the
areas it actually touches.
"""

from __future__ import annotations

import contextlib
import json
import sys
import tempfile
from pathlib import Path

from _payload import edited_paths, project_root

_RULES_DIR = Path('.claude/rules')

# Which rules cover which part of the tree, as (prefix, suffixes, rules).
# A path may match several entries; every match is delivered.
_SCOPES: tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...] = (
    ('eventum/', ('.py',), ('backend/exceptions.md', 'backend/logging.md')),
    ('eventum/api/', ('.py',), ('backend/api.md',)),
    ('eventum/app/', ('.py',), ('backend/app.md',)),
    ('eventum/core/', ('.py',), ('backend/core.md',)),
    ('eventum/mcp/', ('.py',), ('backend/mcp.md',)),
    ('eventum/server/', ('.py',), ('backend/server.md',)),
    ('eventum/plugins/', ('.py',), ('backend/plugins.md',)),
    ('eventum/plugins/input/', ('.py',), ('backend/plugins/input.md',)),
    ('eventum/plugins/event/', ('.py',), ('backend/plugins/event.md',)),
    ('eventum/plugins/output/', ('.py',), ('backend/plugins/output.md',)),
    ('eventum/ui/src/', ('.ts', '.tsx', '.css'), ('frontend/ui.md',)),
    ('CHANGELOG.md', (), ('changelog.md',)),
    ('../docs/content/docs/', ('.mdx', '.json'), ('docs/mdx.md',)),
    ('../docs/content/blog/', ('.mdx',), ('docs/blog.md',)),
    ('../docs/lib/hub-data/', ('.ts',), ('docs/hub.md',)),
    ('../content-packs/generators/', (), ('content/generators.md',)),
    (
        '../content-packs/generators/',
        ('.jinja', '.yml'),
        ('content/templates.md',),
    ),
)

# The rules also cover the sibling repositories of this workspace, which
# the agent edits through its extra writable roots.
_SIBLINGS = ('docs', 'content-packs')

_HEADER = (
    'Project rules covering the files you are about to edit. They are '
    'binding for this repository, alongside AGENTS.md.'
)


def _state_file(session_id: str) -> Path:
    """Return the file tracking what this session already received."""
    directory = Path(tempfile.gettempdir()) / 'eventum-agent-rules'
    directory.mkdir(parents=True, exist_ok=True)
    safe = ''.join(c for c in session_id if c.isalnum() or c in '-_')
    return directory / f'{safe or "default"}.json'


def _already_sent(state: Path) -> set[str]:
    """Return the rules this session has already been given."""
    try:
        loaded = json.loads(state.read_text(encoding='utf-8'))
    except OSError:
        return set()
    except ValueError:
        return set()

    return set(loaded) if isinstance(loaded, list) else set()


def _remember(state: Path, sent: set[str]) -> None:
    """Record the rules delivered so far in this session."""
    with contextlib.suppress(OSError):
        state.write_text(json.dumps(sorted(sent)), encoding='utf-8')


def _workspace_key(path: Path, root: Path) -> str | None:
    """Return the path as named by a scope, or None when out of scope."""
    if path.is_relative_to(root):
        return path.relative_to(root).as_posix()

    for sibling in _SIBLINGS:
        base = root.parent / sibling
        if path.is_relative_to(base):
            return f'../{sibling}/{path.relative_to(base).as_posix()}'

    return None


def _matching_rules(paths: list[Path], root: Path) -> list[str]:
    """Return the rules covering the given project files, in order."""
    matched: list[str] = []

    for path in paths:
        relative = _workspace_key(path, root)
        if relative is None:
            continue
        for prefix, suffixes, rules in _SCOPES:
            covered = relative.startswith(prefix) and (
                not suffixes or relative.endswith(suffixes)
            )
            if covered:
                matched.extend(r for r in rules if r not in matched)

    return matched


def _render(rules: list[str], root: Path) -> tuple[str, set[str]]:
    """Return the rule bodies to deliver and the names they cover."""
    sections: list[str] = []
    delivered: set[str] = set()

    for rule in rules:
        path = root / _RULES_DIR / rule
        try:
            body = path.read_text(encoding='utf-8')
        except OSError:
            continue
        except ValueError:
            continue

        sections.append(f'--- {_RULES_DIR / rule} ---\n{body}')
        delivered.add(rule)

    if not sections:
        return '', delivered

    return '\n\n'.join([_HEADER, *sections]), delivered


def main() -> int:
    """Emit the rules for the edit target as PreToolUse context."""
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0

    if not isinstance(event, dict):
        return 0

    cwd = Path(event.get('cwd') or Path.cwd()).resolve()
    root = project_root(cwd)
    if root is None:
        return 0

    state = _state_file(str(event.get('session_id') or ''))
    sent = _already_sent(state)

    siblings = tuple(root.parent / name for name in _SIBLINGS)
    paths = edited_paths(event, root, cwd, extra_roots=siblings)
    pending = [r for r in _matching_rules(paths, root) if r not in sent]
    if not pending:
        return 0

    context, delivered = _render(pending, root)
    if not context:
        return 0

    _remember(state, sent | delivered)
    json.dump(
        {
            'hookSpecificOutput': {
                'hookEventName': 'PreToolUse',
                'additionalContext': context,
            },
        },
        sys.stdout,
    )

    return 0


if __name__ == '__main__':
    try:
        _code = main()
    except Exception as error:  # noqa: BLE001 - a hook must never block the agent
        sys.stderr.write(f'pre-edit.py: {error}\n')
        _code = 0

    raise SystemExit(_code)
