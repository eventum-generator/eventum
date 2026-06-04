"""Tests for the templating reference resource."""

from eventum.mcp.resources.templating import (
    render_templating_reference,
)


def test_reference_markdown_lists_rand_and_samples() -> None:
    """Rendered Markdown covers rand, samples, and dispatch."""
    text = render_templating_reference()
    assert '# Eventum template context reference' in text
    assert '## `module.rand.network`' in text
    assert 'module.rand.network.mac' in text
    assert '## `samples.<name>`' in text
    assert 'samples.<name>.where' in text
    assert '## `dispatch`' in text
