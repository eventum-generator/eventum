"""Authoring prompts for the Eventum MCP server."""

from mcp.server.fastmcp import FastMCP

_CREATE_GENERATOR = """\
Author a new Eventum generator end to end. Work in this loop:

1. Read the resource `eventum://templating/reference` for the helpers \
available inside templates, and `eventum://examples/generators` for a \
worked file set.
2. Choose plugins: call `list_plugins`, then `get_plugin_schema` for \
each input/event/output plugin you will use. For output formatting, \
call `list_formatters` and `get_formatter_schema`.
3. Write the file set with `write_generator_file`: the template files \
under `templates/`, any sample files under `samples/` (inspect columns \
with `describe_sample`), then `generator.yml` referencing them by \
relative path.
4. Validate: `validate_generator` initialises every plugin and returns \
field-level errors. Fix and repeat until it passes.
5. Preview: `preview_timestamps` to confirm the timing shape, then \
`preview_events` to see real rendered events. Fix and repeat.

Keep template/sample paths relative to the generator directory.
"""


def create_generator_text() -> str:
    """Return the create-generator guidance text."""
    return _CREATE_GENERATOR


_SIMULATE_INCIDENT = """\
Compose an Eventum generator that simulates an incident: {incident}.

Target generator: {generator}
Baseline rate: {baseline}   Peak rate: {peak}   Error ratio: {ratio}

Approach:

1. Shape the timing on the INPUT side. Use a `time_patterns` plugin \
(or layered `cron`) so the rate rises from the baseline to the peak \
across the incident window and returns to baseline. Confirm the shape \
with `preview_timestamps` before touching events.
2. Shape the error mix on the EVENT side. In a `template` event plugin \
(mode `chance`), weight an "error" template against a "normal" one so \
roughly the error ratio of events are errors during the peak. Use \
`module.rand.*` and samples for field values.
3. Validate and preview: `validate_generator`, then `preview_events`, \
and iterate.

This is one worked pattern, not an exhaustive catalogue - adapt the \
plugins and weights to the incident you need.
"""


def simulate_incident_text(
    *,
    incident_type: str,
    generator: str,
    baseline_rate: str,
    peak_rate: str,
    error_ratio: str,
) -> str:
    """Return the simulate-incident guidance text."""
    return _SIMULATE_INCIDENT.format(
        incident=incident_type,
        generator=generator or '(name the generator to build)',
        baseline=baseline_rate,
        peak=peak_rate,
        ratio=error_ratio,
    )


def register(mcp: FastMCP) -> None:
    """Register the authoring prompts."""

    @mcp.prompt(
        name='create_generator',
        description='Guide authoring a new generator end to end.',
    )
    def create_generator() -> str:
        return create_generator_text()

    @mcp.prompt(
        name='simulate_incident',
        description=(
            'Compose a generator that simulates a traffic incident '
            '(one worked pattern).'
        ),
    )
    def simulate_incident(
        incident_type: str = 'traffic burst',
        generator: str = '',
        baseline_rate: str = '10/min',
        peak_rate: str = '500/min',
        error_ratio: str = '0.3',
    ) -> str:
        return simulate_incident_text(
            incident_type=incident_type,
            generator=generator,
            baseline_rate=baseline_rate,
            peak_rate=peak_rate,
            error_ratio=error_ratio,
        )
