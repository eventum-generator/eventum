"""Tests for the workspace-configs resource."""

import json
from pathlib import Path

from eventum.mcp.context import FileAuthoringContext
from eventum.mcp.resources.workspace import render_workspace_configs


def test_lists_saved_generators(tmp_path: Path) -> None:
    """The listing includes a saved generator and its files."""
    gen = tmp_path / 'demo'
    gen.mkdir()
    (gen / 'generator.yml').write_text('input: []\n', encoding='utf-8')
    ctx = FileAuthoringContext(generators_dir=tmp_path, read_only=True)

    payload = json.loads(render_workspace_configs(ctx))

    names = {g['name'] for g in payload['generators']}
    assert 'demo' in names
    demo = next(g for g in payload['generators'] if g['name'] == 'demo')
    assert 'generator.yml' in demo['files']
