"""``eventum://schema/generator`` resource.

Serves the JSON Schema of the top-level ``generator.yml`` document - the
input/event/output envelope that ties plugin configs together. Gives an
agent a deterministic structural reference alongside the worked
examples. No business logic here - it reads the config model's schema.
"""

import json

from mcp.server.fastmcp import FastMCP

from eventum.core.config import GeneratorConfig


def render_generator_schema() -> str:
    """Render the generator.yml JSON Schema as JSON text."""
    return json.dumps(GeneratorConfig.model_json_schema(), indent=2)


def register(mcp: FastMCP) -> None:
    """Register the generator-schema resource."""

    @mcp.resource(
        'eventum://schema/generator',
        name='Generator config schema',
        description=(
            'JSON Schema of the top-level generator.yml document: the '
            'input/event/output envelope that ties plugin configs '
            'together. Read it to structure a generator before filling '
            'in the per-plugin schemas from get_plugin_schema.'
        ),
        mime_type='application/json',
    )
    def generator_schema() -> str:
        return render_generator_schema()
