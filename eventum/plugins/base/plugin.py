"""Definition of base plugin."""

import inspect
from abc import ABC
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import (
    Any,
    Generic,
    NotRequired,
    Required,
    TypedDict,
    TypeVar,
    get_args,
)
from uuid import uuid4

import structlog
from pydantic import RootModel

from eventum.plugins.base.config import PluginConfig
from eventum.plugins.exceptions import (
    PluginConfigurationError,
    PluginRegistrationError,
)
from eventum.plugins.registry import PluginInfo, PluginsRegistry

logger = structlog.stdlib.get_logger()


@dataclass(frozen=True)
class _PluginRegistrationInfo:
    """Information about plugin for registration.

    Attributes
    ----------
    name : str
        Name of the plugin.

    type : str
        Type of the plugin (e.g. input, event, ...).

    module : ModuleType
        Module of plugin class definition

    """

    name: str
    type: str
    module: ModuleType


def _inspect_plugin(plugin_cls: type) -> _PluginRegistrationInfo:
    """Inspect plugin to get registration info.

    Parameters
    ----------
    plugin_cls : type
        Class of the plugin to inspect.

    Returns
    -------
    _PluginRegistrationInfo
        Information for plugin registration.

    Raises
    ------
    ValueError
        If provided class cannot be inspected.

    """
    class_module = inspect.getmodule(plugin_cls)
    if class_module is None:
        msg = 'Cannot found the module of plugin class definition'
        raise ValueError(msg)

    if class_module.__name__ == '__main__':
        msg = 'Plugin can be used only as external module'
        raise ValueError(msg)

    try:
        # expected structure for extraction:
        # eventum.plugins.<plugin_type>.plugins.<plugin_name>.plugin
        module_parts = class_module.__name__.split('.')
        plugin_name = module_parts[-2]
        plugin_type = module_parts[-4]
    except IndexError:
        msg = (
            'Plugin is defined in unexpected location: '
            f'"{class_module.__name__}", expecting following location: '
            '"eventum.plugins.<plugin_type>.plugins.<plugin_name>.plugin"'
        )
        raise ValueError(msg) from None

    return _PluginRegistrationInfo(
        name=plugin_name,
        type=plugin_type,
        module=class_module,
    )


class PluginParams(TypedDict):
    """Parameters for plugin.

    Attributes
    ----------
    id : int
        Numeric plugin identifier.

    ephemeral_name : str
        Ephemeral name of plugin, might be helpful when plugin is not
        registered but it needs representable name to moment of
        initialization.

    ephemeral_type : str
        Ephemeral type of plugin, might be helpful when plugin is not
        registered but it needs representable type to moment of
        initialization.

    base_path : NotRequired[Path]
        Base path for all relative paths used in plugin configurations,
        if it is not provided then current working directory is used.

    """

    id: Required[int]
    ephemeral_name: NotRequired[str]
    ephemeral_type: NotRequired[str]
    base_path: NotRequired[Path]


ConfigT = TypeVar('ConfigT', bound=(PluginConfig | RootModel))
ParamsT = TypeVar('ParamsT', bound=PluginParams)


class Plugin(ABC, Generic[ConfigT, ParamsT]):
    """Base class for all plugins.

    Other Parameters
    ----------------
    register : bool, default=True
        Whether to register plugin in registry.

    """

    def __init__(self, config: ConfigT, params: ParamsT) -> None:
        """Initialize plugin.

        Parameters
        ----------
        config : ConfigT
            Configuration for the plugin.

        params : ParamsT
            Parameters for plugin (see `PluginParams`).

        """
        self._config = config

        if 'ephemeral_name' in params:
            self._plugin_name = params['ephemeral_name']
        if 'ephemeral_type' in params:
            self._plugin_type = params['ephemeral_type']

        with self._required_params():
            self._id = params['id']

        self._guid = str(uuid4())

        self._base_path: Path = params.get('base_path', Path.cwd())  # type: ignore[assignment]

        self._logger = self.logger.bind(
            plugin_name=self.name,
            plugin_type=self.type,
            plugin_id=self.id,
        )

    @contextmanager
    def _required_params(self) -> Iterator:
        """Context manager for handling missing keys in plugin parameters.

        Raises
        ------
        PluginConfigurationError
            If `KeyError` is raised.

        """
        try:
            yield
        except KeyError as e:
            if str(e) == 'id':
                context: dict[str, Any] = {
                    'plugin_name': self.name,
                    'plugin_type': self.type,
                }
            else:
                context = {
                    'plugin_name': self.name,
                    'plugin_type': self.type,
                    'plugin_id': self.id,
                }

            msg = 'Missing required parameter'
            raise PluginConfigurationError(
                msg,
                context=dict(context, reason=str(e)),
            ) from None

    def __str__(self) -> str:
        return f'<{self.name} {self.type} plugin [{self.id}]>'

    def __init_subclass__(
        cls,
        *,
        register: bool = True,
        **kwargs: Any,
    ) -> None:
        super().__init_subclass__(**kwargs)

        context = {'plugin_class': cls.__name__}
        log = logger.bind(**context)

        try:
            registration_info = _inspect_plugin(cls)
        except ValueError as e:
            msg = 'Unable to inspect plugin'
            raise PluginRegistrationError(
                msg,
                context=dict(context, reason=str(e)),
            ) from e

        logger_name = registration_info.module.__name__
        cls._logger = structlog.stdlib.get_logger(logger_name)  # type: ignore[attr-defined]

        if not register:
            cls._plugin_name = '[unregistered]'  # type: ignore[attr-defined]
            cls._plugin_type = '[unregistered]'  # type: ignore[attr-defined]
            return

        log.debug('Preparing info for plugin registration')
        plugin_name = registration_info.name
        plugin_type = registration_info.type
        cls._plugin_name = plugin_name  # type: ignore[attr-defined]
        cls._plugin_type = plugin_type  # type: ignore[attr-defined]

        try:
            (config_cls, *_) = get_args(
                cls.__orig_bases__[0],  # type: ignore[attr-defined]
            )
        except ValueError:
            msg = (
                'Generic parameters must be specified for plugin registration'
            )
            raise PluginRegistrationError(
                msg,
                context=context,
            ) from None
        except Exception as e:
            msg = 'Unable to determine plugin config class'
            raise PluginRegistrationError(
                msg,
                context=dict(context, reason=str(e)),
            ) from e

        if isinstance(config_cls, TypeVar):
            msg = (
                'Concrete classes must be specified as generic parameters '
                'for plugin registration'
            )
            raise PluginRegistrationError(msg, context=context)

        log.debug('Passing information about plugin to registry')
        PluginsRegistry.register_plugin(
            PluginInfo(
                name=registration_info.name,
                cls=cls,
                config_cls=config_cls,
                type=plugin_type,
            ),
        )

        log.debug(
            'Plugin initialization completed',
            plugin_type=registration_info.type,
            plugin_name=registration_info.name,
            plugin_config_class=config_cls.__name__,
        )

    def resolve_path(self, path: Path) -> Path:
        """Resolve path using plugin base path.

        Parameters
        ----------
        path : Path
            Path to resolve.

        Returns
        -------
        Path
            Resolved path.

        Notes
        -----
        If path is already absolute it is returned as is.

        """
        if path.is_absolute():
            return path

        return self._base_path / path

    @property
    def id(self) -> int:
        """ID of the plugin."""
        return self._id

    @property
    def guid(self) -> str:
        """GUID of the plugin."""
        return self._guid

    @property
    def name(self) -> str:
        """Canonical name of the plugin."""
        return self._plugin_name

    @property
    def type(self) -> str:
        """Type of the plugin."""
        return self._plugin_type

    @property
    def config(self) -> ConfigT:
        """Plugin config."""
        return self._config

    @property
    def logger(self) -> structlog.stdlib.BoundLogger:
        """Plugin logger."""
        return self._logger  # type: ignore[attr-defined]

    @property
    def base_path(self) -> Path:
        """Base path of plugin."""
        # TODO(rnv812): https://github.com/python/mypy/issues/18804
        return self._base_path  # type: ignore[return-value]
