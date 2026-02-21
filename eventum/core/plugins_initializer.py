"""Functions for loading, initialization and configuring plugins."""

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal, assert_never, overload
from zoneinfo import ZoneInfo

import structlog
from pydantic import ValidationError

from eventum.core.config import PluginConfig, PluginConfigFields
from eventum.core.parameters import GeneratorParameters
from eventum.exceptions import ContextualError
from eventum.plugins.event.base.plugin import EventPlugin, EventPluginParams
from eventum.plugins.exceptions import (
    PluginConfigurationError,
    PluginLoadError,
    PluginNotFoundError,
)
from eventum.plugins.input.base.plugin import InputPlugin, InputPluginParams
from eventum.plugins.loader import (
    load_event_plugin,
    load_input_plugin,
    load_output_plugin,
)
from eventum.plugins.output.base.plugin import OutputPlugin, OutputPluginParams
from eventum.utils.validation_prettier import prettify_validation_errors

logger = structlog.stdlib.get_logger()


class InitializationError(ContextualError):
    """Error during initialization."""


@dataclass(frozen=True)
class InitializedPlugins:
    """Initialized plugins.

    Attributes
    ----------
    input : list[InputPlugin]
        List of initialized input plugins.

    event : EventPlugin
        Initialized event plugin.

    output : list[OutputPlugin]
        List of initialized output plugins.

    """

    input: list[InputPlugin]
    event: EventPlugin
    output: list[OutputPlugin]


@overload
def init_plugin(
    name: str,
    type: Literal['input'],
    config: PluginConfigFields,
    params: InputPluginParams,
) -> InputPlugin: ...


@overload
def init_plugin(
    name: str,
    type: Literal['event'],
    config: PluginConfigFields,
    params: EventPluginParams,
) -> EventPlugin: ...


@overload
def init_plugin(
    name: str,
    type: Literal['output'],
    config: PluginConfigFields,
    params: OutputPluginParams,
) -> OutputPlugin: ...


def init_plugin(
    name: str,
    type: Literal['input', 'event', 'output'],
    config: PluginConfigFields,
    params: InputPluginParams | EventPluginParams | OutputPluginParams,
) -> InputPlugin | EventPlugin | OutputPlugin:
    """Initialize plugin.

    Parameters
    ----------
    name : str
        Name of plugin to use.

    type : Literal['input', 'event', 'output']
        Type of plugin.

    config : PluginConfigFields
        Config for plugin instance.

    params : InputPluginParams | EventPluginParams | OutputPluginParams
        Parameters for plugin instance.

    Returns
    -------
    InputPlugin | EventPlugin | OutputPlugin
        Initialized plugin.

    Raises
    ------
    InitializationError
        If any error occurs during initializing.

    """
    log = logger.bind(
        plugin_name=name,
        plugin_type=type,
        plugin_id=params['id'],
    )
    log.debug('Loading plugin')
    try:
        match type:
            case 'input':
                plugin_info = load_input_plugin(name=name)
            case 'event':
                plugin_info = load_event_plugin(name=name)
            case 'output':
                plugin_info = load_output_plugin(name=name)
            case t:
                assert_never(t)
    except PluginNotFoundError as e:
        msg = 'Plugin is not found'
        raise InitializationError(
            msg,
            context=(e.context | {'plugin_type': type}),
        ) from None
    except PluginLoadError as e:
        msg = 'Failed to load plugin'
        raise InitializationError(
            msg,
            context=(e.context | {'plugin_type': type}),
        ) from e

    PluginCls = plugin_info.cls  # noqa: N806
    ConfigCls = plugin_info.config_cls  # noqa: N806

    log.debug('Validating plugin config')
    try:
        plugin_config = ConfigCls.model_validate(  # type: ignore[attr-defined]
            config,
        )
    except ValidationError as e:
        msg = 'Invalid configuration for plugin'
        raise InitializationError(
            msg,
            context={
                'plugin_name': name,
                'plugin_type': type,
                'plugin_id': params['id'],
                'reason': prettify_validation_errors(e.errors()),
            },
        ) from None

    log.debug('Instantiating plugin')
    try:
        return PluginCls(config=plugin_config, params=params)
    except PluginConfigurationError as e:
        raise InitializationError(str(e), context=e.context) from None
    except Exception as e:
        msg = 'Unexpected error during plugin initialization'
        raise InitializationError(
            msg,
            context={
                'plugin_name': name,
                'plugin_type': type,
                'plugin_id': params['id'],
                'reason': str(e),
            },
        ) from e


def init_plugins(
    input: Iterable[PluginConfig],
    event: PluginConfig,
    output: Iterable[PluginConfig],
    params: GeneratorParameters,
) -> InitializedPlugins:
    """Initialize plugins.

    Parameters
    ----------
    input : Iterable[PluginConfig]
        Input plugin configurations.

    event : PluginConfig
        Event plugin configuration.

    output : Iterable[PluginConfig]
        Output plugin configurations.

    params : GeneratorParameters
        Generators parameters that can be needed for plugins
        initialization (plugin params, e.g. timezone).

    Returns
    -------
    InitializedPlugins
        Initialized plugins.

    Raises
    ------
    InitializationError
        If any error occurs during initializing.

    """
    plugins_base_path = params.path.parent

    logger.debug('Initializing input plugins')
    input_plugins: list[InputPlugin] = []
    for i, conf in enumerate(input, start=1):
        plugin_name, plugin_conf = next(iter(conf.items()))
        plugin_id = i
        logger.debug(
            'Initializing input plugin',
            plugin_name=plugin_name,
            plugin_id=plugin_id,
        )
        input_plugins.append(
            init_plugin(
                name=plugin_name,
                type='input',
                config=plugin_conf,
                params={
                    'id': plugin_id,
                    'timezone': ZoneInfo(params.timezone),
                    'base_path': plugins_base_path,
                },
            ),
        )

    logger.debug('Initializing event plugin')
    plugin_name, plugin_conf = next(iter(event.items()))
    plugin_id = 1
    logger.debug(
        'Initializing event plugin',
        plugin_name=plugin_name,
        plugin_id=plugin_id,
    )
    event_plugin = init_plugin(
        name=plugin_name,
        type='event',
        config=plugin_conf,
        params={'id': plugin_id, 'base_path': plugins_base_path},
    )

    logger.debug('Initializing output plugins')
    output_plugins: list[OutputPlugin] = []
    for i, conf in enumerate(output, start=1):
        plugin_name, plugin_conf = next(iter(conf.items()))
        plugin_id = i
        logger.debug(
            'Initializing output plugin',
            plugin_name=plugin_name,
            plugin_id=plugin_id,
        )
        output_plugins.append(
            init_plugin(
                name=plugin_name,
                type='output',
                config=plugin_conf,
                params={'id': plugin_id, 'base_path': plugins_base_path},
            ),
        )

    return InitializedPlugins(
        input=input_plugins,
        event=event_plugin,
        output=output_plugins,
    )
