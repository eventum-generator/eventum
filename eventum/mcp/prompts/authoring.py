"""Authoring prompts for the Eventum MCP server."""

from mcp.server.fastmcp import FastMCP

_CREATE_GENERATOR = """\
Author a new Eventum generator end to end. Work in this loop:

1. Read the resource `eventum://templating/reference` for the helpers \
available inside templates, `eventum://schema/generator` for the \
top-level config structure, and `eventum://examples/generators` for \
worked file sets.
2. Choose plugins: call `list_plugins`, then `get_plugin_schema` for \
each input/event/output plugin you will use. For output formatting, \
call `list_formatters` and `get_formatter_schema`. If the config will \
reference `${secrets.*}`, call `list_secrets` for the available names.
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
Author or extend an Eventum generator that simulates an incident or \
anomaly in a data stream: {incident}.

Target generator: {generator}

An incident has two independent dimensions - shape each one:

1. TIMING (input side). Match the input plugin to the temporal profile:
   - burst / spike: a `time_patterns` plugin (or layered `cron`) that \
ramps the rate up across the window and back down;
   - gradual ramp: a rising `linspace` distribution;
   - outage / gap: a schedule with a quiet interval;
   - steady background: a constant `cron` or `timer`.
   Confirm the profile with `preview_timestamps` before touching events.

2. CONTENT (event side). Shape what events say during the incident with \
a `template` event plugin - mode `chance` weights an "anomalous" \
template against a "normal" one. Use `module.rand.*` and samples for \
field values.

Then `validate_generator`, `preview_events`, and iterate. This is \
guidance, not a fixed recipe - adapt the plugins and weights to the \
incident described.
"""


def simulate_incident_text(*, incident_type: str, generator: str) -> str:
    """Return the simulate-incident guidance text."""
    return _SIMULATE_INCIDENT.format(
        incident=incident_type,
        generator=generator or '(name the generator to build)',
    )


_HISTORICAL_BACKFILL = """\
Author an Eventum generator that backfills historical data over a fixed \
past time range - for example to seed a dashboard or test a detector.

Target generator: {generator}
Time range: {start} to {end}

1. Bound the input to the range. Use a `timestamps` input plugin with \
explicit moments, or a `cron` / `time_patterns` plugin limited to the \
window, so every event falls inside it. Confirm coverage with \
`preview_timestamps` - pass `skip_past=false`, since a past range is \
skipped by default.
2. Build the event with a `template` plugin and an output formatter \
that matches your sink. Use `module.rand.*` and samples for realistic \
field values.
3. `validate_generator`, then `preview_events` (again `skip_past=false`), \
and iterate.

The goal is a finite, replayable batch inside the requested range, not \
a live stream.
"""


def historical_backfill_text(
    *,
    generator: str,
    start: str,
    end: str,
) -> str:
    """Return the historical-backfill guidance text."""
    return _HISTORICAL_BACKFILL.format(
        generator=generator or '(name the generator to build)',
        start=start,
        end=end,
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
            'Compose a generator that simulates an incident or anomaly '
            'in a data stream.'
        ),
    )
    def simulate_incident(
        incident_type: str = 'a traffic burst with elevated errors',
        generator: str = '',
    ) -> str:
        return simulate_incident_text(
            incident_type=incident_type,
            generator=generator,
        )

    @mcp.prompt(
        name='historical_backfill',
        description=(
            'Compose a generator that backfills historical data over a '
            'past time range.'
        ),
    )
    def historical_backfill(
        generator: str = '',
        start: str = '7 days ago',
        end: str = 'now',
    ) -> str:
        return historical_backfill_text(
            generator=generator,
            start=start,
            end=end,
        )
