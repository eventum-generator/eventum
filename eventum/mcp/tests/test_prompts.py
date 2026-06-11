"""Tests for the MCP prompts."""

from eventum.mcp.prompts.authoring import create_generator_text
from eventum.mcp.prompts.operations import live_ops_text


def test_create_generator_mentions_the_loop() -> None:
    """The create-generator prompt walks the full authoring loop."""
    text = create_generator_text()
    for token in (
        'eventum://templating/reference',
        'eventum://schema/generator',
        'get_plugin_schema',
        'write_generator_file',
        'validate_generator',
        'preview_events',
        'replay',
        'script',
        'skip_past',
        'static',
        'http',
        'list_secret_names',
        '${params.*}',
    ):
        assert token in text


def test_live_ops_lists_the_workflow() -> None:
    """The live-ops prompt names the management tools."""
    text = live_ops_text()
    for token in (
        'register_generator',
        'start_generator',
        'get_generator_logs',
        'unregister_generator',
        'get_generator_stats',
        'list_startup_generators',
    ):
        assert token in text
