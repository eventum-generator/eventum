"""Functions for plugins loading.

Plugins loading is performed using registry (see `registry` module), so
plugin can be loaded only if it is presented in registry.

It is expected that plugins register themselves using class hooks.
Therefore during loading specific plugins, module with plugin is
imported to execute that hook if that plugin is not currently presented
in registry. This is so called "plugin invocation".

Plugin invocation is serialized across threads, see `_import_lock`.
"""

import importlib
from functools import cache
from threading import RLock
from types import ModuleType

import structlog

import eventum.plugins.event.plugins as event_plugins
import eventum.plugins.input.plugins as input_plugins
import eventum.plugins.output.plugins as output_plugins
from eventum.plugins.exceptions import PluginLoadError, PluginNotFoundError
from eventum.plugins.registry import PluginInfo, PluginsRegistry
from eventum.utils.package_utils import get_subpackage_names

logger = structlog.stdlib.get_logger()

# Importing a plugin module builds its config classes, and building a
# Pydantic model mutates class attributes shared with the models of
# other plugins. Without the GIL two threads doing it at once can see
# a class dictionary change under them, so plugin modules are imported
# one at a time. Import lock of the interpreter does not cover this: it
# serializes imports of one module, not of two modules sharing a base.
# The lock is reentrant for a plugin module that loads another plugin
# at import time.
_import_lock = RLock()


def _construct_plugin_module_name(package: ModuleType, name: str) -> str:
    """Construct absolute name of module with plugin class definition.

    Parameters
    ----------
    package : ModuleType
        Common package with plugins of specific type.

    name : str
        Name of the plugin.

    Returns
    -------
    str
        Absolute name of module with plugin class definition.

    """
    return f'{package.__name__}.{name}.plugin'


def _extract_plugins_type_name(package: ModuleType) -> str:
    """Extract plugins type name from package with plugins of specific
    type.

    Parameters
    ----------
    package : ModuleType
        Common package with plugins of specific type.

    Returns
    -------
    str
        Plugins type name.

    """
    parts = package.__name__.split('.')
    return parts[-2]


def _invoke_plugin(package: ModuleType, name: str) -> None:
    """Invoke plugin to trigger registration.

    Parameters
    ----------
    package : ModuleType
        Common package with plugins of specific type.

    name : str
        Name of the plugin.

    Raises
    ------
    PluginNotFoundError
        If specified plugin is not found.

    PluginLoadError
        If specified plugin is found but cannot be imported.

    """
    log = logger.bind(
        package_name=package.__name__,
        plugin_name=name,
    )

    log.debug('Constructing plugin module name')
    module_name = _construct_plugin_module_name(package, name)

    log.debug('Importing module', module_name=module_name)
    try:
        with _import_lock:
            importlib.import_module(module_name)
    except ModuleNotFoundError:
        msg = 'Plugin not found'
        raise PluginNotFoundError(
            msg,
            context={'plugin_name': name},
        ) from None
    except ImportError as e:
        msg = 'Error during importing plugin module'
        raise PluginLoadError(
            msg,
            context={'reason': str(e), 'plugin_name': name},
        ) from e


def _load_plugin(package: ModuleType, name: str) -> PluginInfo:
    """Load specified plugin by importing plugin module, that in turn
    triggers registration of plugin in the registry. If plugin is
    presented in the registry, then importing is skipped.

    Parameters
    ----------
    package : ModuleType
        Common package with plugins of specific type.

    name : str
        Name of the plugin.

    Returns
    -------
    PluginInfo
        Information of loaded plugin.

    Raises
    ------
    PluginNotFoundError
        If specified plugin is not found.

    PluginLoadError
        If specified plugin is found but cannot be loaded.

    """
    log = logger.bind(plugin_name=name)

    log.debug('Defining plugin type')
    type = _extract_plugins_type_name(package)

    log = log.bind(plugin_type=type)

    log.debug('Checking if plugin is registered')
    if not PluginsRegistry.is_registered(type, name):
        logger.debug('Invoking plugin for registration')
        _invoke_plugin(package, name)

    try:
        log.debug('Getting plugin info from registry')
        return PluginsRegistry.get_plugin_info(type, name)
    except ValueError:
        msg = 'Plugin was imported but was not found in registry'
        raise PluginLoadError(
            msg,
            context={'plugin_name': name},
        ) from None


@cache
def load_input_plugin(name: str) -> PluginInfo:
    """Load specified input plugin and return information about it.

    Parameters
    ----------
    name : str
        Name of the plugin.

    Returns
    -------
    PluginInfo
        Information about plugin.

    Raises
    ------
    PluginNotFoundError
        If specified plugin is not found.

    PluginLoadError
        If plugin is found but cannot be loaded.

    """
    return _load_plugin(input_plugins, name)


@cache
def load_event_plugin(name: str) -> PluginInfo:
    """Load specified event plugin and return information about it.

    Parameters
    ----------
    name : str
        Name of the plugin.

    Returns
    -------
    PluginInfo
        Information about plugin.

    Raises
    ------
    PluginNotFoundError
        If specified plugin is not found.

    PluginLoadError
        If plugin is found but cannot be loaded.

    """
    return _load_plugin(event_plugins, name)


@cache
def load_output_plugin(name: str) -> PluginInfo:
    """Load specified output plugin and return information about it.

    Parameters
    ----------
    name : str
        Name of the plugin.

    Returns
    -------
    PluginInfo
        Information about plugin.

    Raises
    ------
    PluginNotFoundError
        If specified plugin is not found.

    PluginLoadError
        If plugin is found but cannot be loaded.

    """
    return _load_plugin(output_plugins, name)


def get_input_plugin_names() -> list[str]:
    """Get names list of existing input plugins.

    Returns
    -------
    list[str]
        Names of existing input plugins.

    """
    return get_subpackage_names(input_plugins)


def get_event_plugin_names() -> list[str]:
    """Get names list of existing event plugins.

    Returns
    -------
    list[str]
        Names of existing event plugins.

    """
    return get_subpackage_names(event_plugins)


def get_output_plugin_names() -> list[str]:
    """Get names list of existing output plugins.

    Returns
    -------
    list[str]
        Names of existing output plugins.

    """
    return get_subpackage_names(output_plugins)


def clear_cache() -> None:
    """Clear cache of functions that load plugins."""
    load_input_plugin.cache_clear()
    load_event_plugin.cache_clear()
    load_output_plugin.cache_clear()
