"""Plugin discovery tools."""

from collections.abc import Callable
from typing import Any, Literal

from pydantic import BaseModel

from eventum.mcp.context import AuthoringContext
from eventum.mcp.errors import ToolFailure
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
    context: AuthoringContext,  # noqa: ARG001 - DI seam, used by Phase 2B tools
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
    context: AuthoringContext,  # noqa: ARG001 - DI seam, used by Phase 2B tools
    kind: Kind,
    name: str,
) -> dict[str, Any] | ToolFailure:
    """Return the JSON schema of a plugin's config model.

    Parameters
    ----------
    context : AuthoringContext
        Authoring context (DI seam; unused at this layer).

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
    except (PluginNotFoundError, PluginLoadError) as e:
        return ToolFailure(
            error=f'Plugin not found: {name}',
            details={'kind': kind, 'name': name, 'reason': str(e)},
        )

    config_cls = info.config_cls
    if not issubclass(config_cls, BaseModel):
        return ToolFailure(
            error=f'Plugin has no schema: {name}',
            details={'kind': kind, 'name': name},
        )

    return config_cls.model_json_schema()
