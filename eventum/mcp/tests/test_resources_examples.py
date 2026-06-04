"""Tests for the example-generators resource."""

import json

from eventum.mcp.resources.examples import (
    BUNDLED,
    render_examples,
)


def test_bundled_manifest_matches_disk() -> None:
    """Every file listed in BUNDLED exists on disk and is non-empty."""
    # Drift guard.
    from importlib.resources import files

    root = files('eventum.mcp').joinpath('examples')
    for entry in BUNDLED:
        for rel in entry['files']:
            text = root.joinpath(entry['name'], rel).read_text(
                encoding='utf-8'
            )
            assert text.strip()


def test_render_includes_contents_and_pointers() -> None:
    """render_examples returns bundled file contents and external URLs."""
    payload = json.loads(render_examples())
    bundled = payload['bundled']
    assert bundled[0]['name'] == 'web-access-log'
    assert 'input:' in bundled[0]['files']['generator.yml']
    urls = {p['url'] for p in payload['external']}
    assert 'https://github.com/eventum-generator/content-packs' in urls
    assert any('eventum.run' in u for u in urls)
