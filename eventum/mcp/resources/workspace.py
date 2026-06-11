"""``eventum://workspace/configs`` resource.

Lists the saved generators under the context's generators directory so
an agent sees existing work. Thin: delegates to the workspace file
tools.
"""

import json

from mcp.server.fastmcp import FastMCP

from eventum.mcp.context import AuthoringContext
from eventum.mcp.errors import ToolFailure
from eventum.mcp.tools import workspace_files as ws


def render_workspace_configs(context: AuthoringContext) -> str:
    """Render the saved-generators listing as JSON text."""
    generators: list[dict[str, object]] = []
    for name in ws.list_generators(context):
        listed = ws.list_generator_files(context, name)
        if isinstance(listed, ToolFailure):
            generators.append(
                {'name': name, 'files': [], 'error': listed.error}
            )
        else:
            generators.append({'name': name, 'files': listed})
    return json.dumps({'generators': generators}, indent=2)


def register(mcp: FastMCP, context: AuthoringContext) -> None:
    """Register the workspace-configs resource."""

    @mcp.resource(
        'eventum://workspace/configs',
        name='Saved generators',
        description=(
            "The generators saved under this server's generators "
            'directory, with their files.'
        ),
        mime_type='application/json',
    )
    def workspace_configs() -> str:
        return render_workspace_configs(context)
