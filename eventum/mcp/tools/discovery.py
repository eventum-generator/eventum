"""Plugin discovery tools."""

from collections.abc import Callable
from typing import Any, Literal

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from eventum.mcp.context import AuthoringContext
from eventum.mcp.errors import ToolFailure, scrub_message
from eventum.mcp.observability import observe_failure
from eventum.plugins.exceptions import PluginLoadError, PluginNotFoundError
from eventum.plugins.loader import (
    get_event_plugin_names,
    get_input_plugin_names,
    get_output_plugin_names,
    load_event_plugin,
    load_input_plugin,
    load_output_plugin,
)
from eventum.plugins.registry import PluginInfo

Kind = Literal['input', 'event', 'output']

_NAMES: dict[str, Callable[[], list[str]]] = {
    'input': get_input_plugin_names,
    'event': get_event_plugin_names,
    'output': get_output_plugin_names,
}
_LOADERS: dict[str, Callable[[str], PluginInfo]] = {
    'input': load_input_plugin,
    'event': load_event_plugin,
    'output': load_output_plugin,
}


def list_plugins(
    context: AuthoringContext,  # noqa: ARG001 - DI seam, unused here
    kind: Kind | None = None,
) -> dict[str, list[str]]:
    """List available plugin names grouped by kind.

    Parameters
    ----------
    context : AuthoringContext
        Authoring context (DI seam; unused at this layer).

    kind : Kind | None
        If given, return only this plugin kind. If None, return all
        three kinds.

    Returns
    -------
    dict[str, list[str]]
        Mapping of plugin kind to sorted list of plugin names.

    """
    kinds: list[str] = [kind] if kind else ['input', 'event', 'output']
    return {k: sorted(_NAMES[k]()) for k in kinds}


def get_plugin_schema(
    context: AuthoringContext,
    kind: Kind,
    name: str,
) -> dict[str, Any] | ToolFailure:
    """Return the JSON schema of a plugin's config model.

    Parameters
    ----------
    context : AuthoringContext
        Authoring context supplying the generators directory, used to
        scrub paths from a plugin-load error reason.

    kind : Kind
        Plugin kind: 'input', 'event', or 'output'.

    name : str
        Plugin name.

    Returns
    -------
    dict[str, Any]
        JSON Schema dict for the plugin's config model.

    ToolFailure
        If the plugin name is not found or cannot be loaded.

    """
    try:
        info = _LOADERS[kind](name)
    except PluginNotFoundError as e:
        return ToolFailure(
            error=f'Plugin not found: {name}',
            details={
                'kind': kind,
                'name': name,
                'reason': scrub_message(str(e), context.generators_dir),
            },
        )
    except PluginLoadError as e:
        reason = str(e.context.get('reason') or e)
        return ToolFailure(
            error=f'Plugin failed to load: {name}',
            details={
                'kind': kind,
                'name': name,
                'reason': scrub_message(reason, context.generators_dir),
            },
        )

    config_cls = info.config_cls
    if not issubclass(config_cls, BaseModel):
        return ToolFailure(
            error=f'Plugin has no schema: {name}',
            details={'kind': kind, 'name': name},
        )

    return config_cls.model_json_schema()


def register(
    mcp: FastMCP,
    context: AuthoringContext,
    *,
    transport: str,
) -> None:
    """Register plugin-discovery tools on the server."""

    @mcp.tool(name='list_plugins')
    def _list_plugins_tool(
        kind: Kind | None = None,
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
        return observe_failure(
            list_plugins(context, kind=kind),
            mcp_tool='list_plugins',
            mcp_transport=transport,
        )

    @mcp.tool(name='get_plugin_schema')
    def _get_plugin_schema_tool(
        kind: Kind,
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
        return observe_failure(
            get_plugin_schema(context, kind=kind, name=name),
            mcp_tool='get_plugin_schema',
            mcp_transport=transport,
        )
