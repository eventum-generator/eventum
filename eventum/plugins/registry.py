"""Common registry for plugins registration.

This module should be used only by plugin modules to register
themselves and `loader` module to load registered plugins.

User should use `loader` module to access existing plugins and avoid
direct usage of registry.
"""

from dataclasses import asdict, dataclass
from typing import ClassVar

import structlog

logger = structlog.stdlib.get_logger()


@dataclass(frozen=True)
class PluginInfo:
    """Plugin information for a registration.

    Attributes
    ----------
    name : str
        Plugin name.

    cls : type
        Plugin class.

    config_cls : type
        Class of config used to configure plugin.

    type : str
        Plugin type.

    """

    name: str
    cls: type
    config_cls: type
    type: str


class PluginsRegistry:
    """Common registry of plugins. All plugins should be
    registered using this class to be accessible via loader.
    """

    _registry: ClassVar[dict[str, dict[str, PluginInfo]]] = {}

    @classmethod
    def register_plugin(cls, plugin_info: PluginInfo) -> None:
        """Register plugin in registry.

        Parameters
        ----------
        plugin_info : PluginInfo
            Information about plugin.

        """
        logger.debug('Registering plugin', parameters=asdict(plugin_info))

        # Single step: checking the type before inserting it can drop a
        # registration made by another thread in between.
        plugins = cls._registry.setdefault(plugin_info.type, {})
        plugins[plugin_info.name] = plugin_info

    @classmethod
    def get_plugin_info(cls, type: str, name: str) -> PluginInfo:
        """Get information about plugin from registry.

        Parameters
        ----------
        type : str
            Plugin type.

        name : str
            Plugin name.

        Returns
        -------
        PluginInfo
            Information about plugin.

        Raises
        ------
        ValueError
            If specified plugin is not found in registry.

        """
        try:
            return cls._registry[type][name]
        except KeyError:
            msg = 'Plugin is not registered'
            raise ValueError(msg) from None

    @classmethod
    def is_registered(cls, type: str, name: str) -> bool:
        """Check whether specified plugin is registered.

        Parameters
        ----------
        type : str
            Plugin type.

        name : str
            Plugin name.

        Returns
        -------
        bool
            `True` if plugin is registered else `False`.

        """
        return type in cls._registry and name in cls._registry[type]

    @classmethod
    def clear(cls) -> None:
        """Clear registry by removing all registered plugins from it."""
        cls._registry.clear()
