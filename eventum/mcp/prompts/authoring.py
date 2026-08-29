"""Authoring prompts for the Eventum MCP server."""

from mcp.server.fastmcp import FastMCP

_CREATE_GENERATOR = """\
Author a new Eventum generator end to end. A generator is an \
input -> event -> output pipeline. Build it in this loop.

1. Ground yourself. Read `eventum://schema/generator` for the \
top-level config structure and `eventum://examples/generators` for \
worked file sets. Call `list_plugins` to see the available input, \
event, and output plugins.
2. Choose the pipeline from the request, calling `get_plugin_schema` \
for each plugin you pick:
   - Input (timing): `cron`/`timer` for steady rates, `time_patterns` \
for realistic peaks, `linspace`/`timestamps` for a fixed or past \
range, `static` for a fixed batch at start time, `http` for \
request-driven ticks.
   - Event (content): pick the family. `template` renders Jinja - read \
`eventum://templating/reference` for the in-template API: `samples`, \
`module.<name>` (imports any installed Python package; \
`rand`/`faker`/`mimesis` are bundled), `subprocess`, \
`locals`/`shared`/`globals` state, and `dispatch`. `replay` re-emits \
lines from an existing log file. `script` runs an existing Python file \
and receives the same `globals` state in `params['globals']` - MCP \
file tools cannot write `.py`, so pick it only when the script is \
already on disk; otherwise prefer `template`.
   - Output (delivery): `stdout`/`file` for local sinks, \
`http`/`tcp`/`udp`/`kafka` to push to a pipeline, \
`clickhouse`/`opensearch` to index into a datastore; pick a formatter \
via `list_formatters` and `get_formatter_schema`. If the config \
references `${secrets.*}`, call `list_secret_names` for the names; use \
`${params.*}` for caller-supplied values and pass them as `params` \
when you validate, preview, or run.
3. For a `template` event plugin, match technique to intent: a picking \
mode (`all`/`chance`/`spin`/`chain`/`fsm`) for several variants or a \
stateful sequence, and `shared`/`locals` state for correlated or \
drifting values. Inspect any data files with `describe_sample` - it \
summarises a sample without pulling it into the conversation, and \
`read_generator_file` returns one window of a file at a time, so \
continue from its `next_offset` while `truncated` is true instead of \
expecting a whole file back.
4. Write the file set with `write_generator_file`, paths relative to \
the generator directory: `generator.yml`, plus `templates/` and \
`samples/` for a template generator. A `replay` generator just points \
at its log file; a `script` generator points at an existing Python \
file - `.py` is not writable over MCP. For a large CSV or JSON \
sample, do not pass it through `write_generator_file` (carrying big \
content this way is slow): over HTTP, once the generator exists, \
upload it with the server's REST file API (`POST \
/api/generator-configs/{name}/file/{filepath}`, multipart field \
`content`); running locally, write it straight into the generator's \
`samples/` directory. Then reference it from the config.
5. Validate with `validate_generator` and fix until it passes.
6. Preview before finishing: `preview_timestamps` for the timing \
shape, then `preview_events` for real rendered events. For a past \
range pass `skip_past=false`, or the preview is empty. Read the \
per-event `errors`, not just the events. Show the preview to the user \
and iterate on their feedback.
"""


def create_generator_text() -> str:
    """Return the create-generator guidance text."""
    return _CREATE_GENERATOR


def register(mcp: FastMCP) -> None:
    """Register the authoring prompts."""

    @mcp.prompt(
        name='create_generator',
        description='Guide authoring a new generator end to end.',
    )
    def create_generator() -> str:
        return create_generator_text()
