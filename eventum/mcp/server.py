"""FastMCP server factory.

The only FastMCP-aware module besides the transport roots. Wires the
tool, resource, and prompt registrations onto one server bound to an
injected context.
"""

from mcp.server.fastmcp import FastMCP

from eventum import __version__ as _eventum_version
from eventum.mcp.context import AuthoringContext
from eventum.mcp.prompts import authoring as authoring_prompts
from eventum.mcp.resources import examples as examples_resource
from eventum.mcp.resources import schema as schema_resource
from eventum.mcp.resources import templating as templating_resource
from eventum.mcp.resources import workspace as workspace_resource
from eventum.mcp.tools import discovery
from eventum.mcp.tools import formatters as fmt_tools
from eventum.mcp.tools import preview as preview_tools
from eventum.mcp.tools import samples as sample_tools
from eventum.mcp.tools import secrets as secrets_tools
from eventum.mcp.tools import workspace_files as ws_tools

_INSTRUCTIONS = (
    'Eventum MCP server. Author and inspect synthetic data generators: '
    'discover plugins and their config schemas, read the template '
    'context reference and worked examples, then validate and preview '
    'generators before running them.'
)


def build_server(
    context: AuthoringContext,
    *,
    transport: str = 'stdio',
    live: bool = False,
) -> FastMCP:
    """Build a FastMCP server bound to the given context.

    Parameters
    ----------
    context : AuthoringContext
        Authoring context injected into each tool. When ``live`` is
        True it must also be a ``LiveContext``.

    transport : str, default 'stdio'
        Transport label, forwarded to tool failure logging.

    live : bool, default False
        Whether to also register live generator-management tools.
        Requires ``context`` to be a ``LiveContext``.

    Returns
    -------
    FastMCP
        Server with discovery, formatter, sample, workspace, and
        validate/preview tools; the templating-reference, examples, and
        workspace-configs resources; the authoring prompts; and, when
        ``live`` is set, the live generator-management tools.

    """
    mcp = FastMCP('eventum', instructions=_INSTRUCTIONS)
    mcp._mcp_server.version = _eventum_version  # noqa: SLF001

    discovery.register(mcp, context, transport=transport)
    fmt_tools.register(mcp, context, transport=transport)
    sample_tools.register(mcp, context, transport=transport)
    secrets_tools.register(mcp, context, transport=transport)
    ws_tools.register(mcp, context, transport=transport)
    preview_tools.register(mcp, context, transport=transport)

    templating_resource.register(mcp)
    schema_resource.register(mcp)
    examples_resource.register(mcp)
    workspace_resource.register(mcp, context)

    authoring_prompts.register(mcp)

    if live:
        from eventum.mcp.context import LiveContext
        from eventum.mcp.prompts import operations as operations_prompts
        from eventum.mcp.tools import live as live_tools

        if not isinstance(context, LiveContext):
            msg = 'live mode requires a LiveContext'
            raise TypeError(msg)
        live_tools.register(mcp, context, transport=transport)
        operations_prompts.register(mcp)

    return mcp
