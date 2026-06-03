"""FastMCP server factory.

The only FastMCP-aware module besides the stdio CLI entry. Registers
tools bound to an injected context; later phases register live-only
tools when the context carries a generator manager.
"""

from typing import Any

from mcp.server.fastmcp import FastMCP

from eventum.mcp.context import AuthoringContext
from eventum.mcp.errors import ToolFailure
from eventum.mcp.tools import discovery

_INSTRUCTIONS = (
    'Eventum MCP server. Author and inspect synthetic data generators: '
    'discover plugins and their config schemas, and (in later tools) '
    'validate and preview generators before running them.'
)


def build_server(context: AuthoringContext) -> FastMCP:
    """Build a FastMCP server with tools bound to the given context.

    Parameters
    ----------
    context : AuthoringContext
        Authoring context injected into each tool at registration time.

    Returns
    -------
    FastMCP
        Configured server with discovery tools registered.

    """
    mcp = FastMCP('eventum', instructions=_INSTRUCTIONS)

    @mcp.tool()
    def list_plugins(
        kind: discovery.Kind | None = None,
    ) -> dict[str, list[str]]:
        """List registered plugin names grouped by kind.

        Parameters
        ----------
        kind : 'input' | 'event' | 'output', optional
            Restrict to one kind. Omit to get all three.

        Returns
        -------
        dict[str, list[str]]
            Maps each kind to a sorted list of plugin names.

        """
        return discovery.list_plugins(context, kind=kind)

    @mcp.tool()
    def get_plugin_schema(
        kind: discovery.Kind,
        name: str,
    ) -> dict[str, Any] | ToolFailure:
        """Return the JSON Schema of a plugin's config model.

        Use it to author a valid config block for the plugin.

        Parameters
        ----------
        kind : 'input' | 'event' | 'output'
            Plugin kind.

        name : str
            Plugin name, as returned by ``list_plugins``.

        Returns
        -------
        dict[str, Any] | ToolFailure
            The plugin config's JSON Schema, or a structured failure
            (error plus kind and name) if the plugin is unknown. Does
            not raise.

        """
        return discovery.get_plugin_schema(context, kind=kind, name=name)

    return mcp
