"""Tests for the MCP prompts."""

from eventum.mcp.prompts.authoring import (
    create_generator_text,
    historical_backfill_text,
    simulate_incident_text,
)
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
    ):
        assert token in text


def test_simulate_incident_interpolates_args() -> None:
    """The simulate-incident prompt interpolates its arguments."""
    text = simulate_incident_text(
        incident_type='ddos burst',
        generator='web-access-log',
    )
    assert 'ddos burst' in text
    assert 'web-access-log' in text
    assert 'preview_timestamps' in text


def test_historical_backfill_interpolates_args() -> None:
    """The backfill prompt interpolates the generator and range."""
    text = historical_backfill_text(
        generator='orders',
        start='2026-01-01',
        end='2026-02-01',
    )
    assert 'orders' in text
    assert '2026-01-01' in text
    assert '2026-02-01' in text
    assert 'preview_timestamps' in text


def test_live_ops_lists_the_workflow() -> None:
    """The live-ops prompt names the management tools."""
    text = live_ops_text()
    for token in (
        'register_generator',
        'start_generator',
        'get_generator_logs',
        'unregister_generator',
    ):
        assert token in text
