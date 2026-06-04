"""FastMCP server factory.

The only FastMCP-aware module besides the transport roots. Wires the
tool registrations onto one server bound to an injected context.
"""

from mcp.server.fastmcp import FastMCP

from eventum import __version__ as _eventum_version
from eventum.mcp.context import AuthoringContext
from eventum.mcp.resources import examples as examples_resource
from eventum.mcp.resources import templating as templating_resource
from eventum.mcp.resources import workspace as workspace_resource
from eventum.mcp.tools import discovery
from eventum.mcp.tools import formatters as fmt_tools
from eventum.mcp.tools import preview as preview_tools
from eventum.mcp.tools import samples as sample_tools
from eventum.mcp.tools import workspace_files as ws_tools

_INSTRUCTIONS = (
    'Eventum MCP server. Author and inspect synthetic data generators: '
    'discover plugins and their config schemas, and validate and '
    'preview generators before running them.'
)


def build_server(
    context: AuthoringContext,
    *,
    transport: str = 'stdio',
) -> FastMCP:
    """Build a FastMCP server bound to the given context.

    Parameters
    ----------
    context : AuthoringContext
        Authoring context injected into each tool.

    transport : str, default 'stdio'
        Transport label, forwarded to tool failure logging.

    Returns
    -------
    FastMCP
        Server with discovery, formatter, sample, workspace,
        validate/preview tools, and templating reference resource
        registered.

    """
    mcp = FastMCP('eventum', instructions=_INSTRUCTIONS)
    mcp._mcp_server.version = _eventum_version  # noqa: SLF001

    discovery.register(mcp, context, transport=transport)
    fmt_tools.register(mcp, context, transport=transport)
    sample_tools.register(mcp, context, transport=transport)
    ws_tools.register(mcp, context, transport=transport)
    preview_tools.register(mcp, context, transport=transport)

    templating_resource.register(mcp)
    examples_resource.register(mcp)
    workspace_resource.register(mcp, context)

    return mcp
