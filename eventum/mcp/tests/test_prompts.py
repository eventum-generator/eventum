"""Tests for the authoring prompts."""

from eventum.mcp.prompts.authoring import (
    create_generator_text,
    simulate_incident_text,
)


def test_create_generator_mentions_the_loop() -> None:
    """The create-generator prompt walks the full authoring loop."""
    text = create_generator_text()
    for token in (
        'eventum://templating/reference',
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
        baseline_rate='10/min',
        peak_rate='800/min',
        error_ratio='0.4',
    )
    assert 'ddos burst' in text
    assert 'web-access-log' in text
    assert '800/min' in text
    assert 'preview_timestamps' in text
