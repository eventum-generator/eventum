"""Dependencies."""

import asyncio
from datetime import timedelta
from typing import Annotated, cast

from fastapi import Body, Depends, HTTPException, Path, Query, status
from pytz import BaseTzInfo, UnknownTimeZoneError
from pytz import timezone as to_timezone

from eventum.api.dependencies.app import SettingsDep
from eventum.api.routers.generator_configs.dependencies import (
    CheckConfigurationExistsDep,
    CheckDirectoryIsAllowedDep,
    check_configuration_exists,
    check_directory_is_allowed,
)
from eventum.api.routers.generator_configs.runtime_types import (
    EventPluginNamedConfig,
    InputPluginNamedConfig,
    PluginNamedConfig,
)
from eventum.api.routers.preview.plugins_storage import EVENT_PLUGINS
from eventum.api.utils.response_description import (
    merge_responses,
    set_responses,
)
from eventum.core.plugins_initializer import InitializationError, init_plugin
from eventum.plugins.event.base.plugin import EventPlugin
from eventum.plugins.event.plugins.template.plugin import TemplateEventPlugin
from eventum.plugins.event.plugins.template.state import (
    MultiThreadState,
    SingleThreadState,
)
from eventum.plugins.input.base.plugin import InputPlugin
from eventum.plugins.input.utils.relative_time import parse_relative_time


@set_responses(
    responses={
        400: {
            'description': 'Timezone is invalid',
        },
    },
)
async def get_timezone(
    timezone: Annotated[
        str,
        Query(
            description='Timezone that is used for generated timestamps',
        ),
    ] = 'UTC',
) -> BaseTzInfo:
    """Get timezone.

    Parameters
    ----------
    timezone : str
        Timezone string to parse.

    Returns
    -------
    BaseTzInfo
        Parsed timezone.

    Raises
    ------
    HTTPException
        Timezone is invalid.

    """
    try:
        return to_timezone(timezone)
    except UnknownTimeZoneError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Timezone is invalid',
        ) from None


TimezoneDep = Annotated[BaseTzInfo, Depends(get_timezone)]


@set_responses(
    responses={
        400: {
            'description': 'Span expression is invalid',
        },
    },
)
async def get_span(
    span: Annotated[
        str | None,
        Query(
            description=(
                'Span expression for timestamps aggregation, '
                'can be omitted to use auto span'
            ),
            examples=['1s', '5m', '30m', '1h', '7d'],
        ),
    ] = None,
) -> timedelta | None:
    """Get timedelta span by parsing span expression.

    Parameters
    ----------
    span : str | None
        Span expression (e.g. `5m`, `30m`, `1h` etc) or `None`.

    Returns
    -------
    timedelta
        Parsed span expression or `None` if span expression is `None`
        that indicates that auto span should be used.

    Raises
    ------
    HTTPException
        Span expression is invalid.

    """
    if span is None:
        return None

    try:
        return await asyncio.to_thread(
            lambda: parse_relative_time(expression=span),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Span expression is invalid: {e}',
        ) from None


SpanDep = Annotated[timedelta | None, Depends(get_span)]


@set_responses(
    responses=merge_responses(
        check_directory_is_allowed.responses,
        check_configuration_exists.responses,
        get_timezone.responses,
        {
            500: {
                'description': (
                    'Some of the input plugins cannot be initialized'
                ),
            },
        },
    ),
)
async def load_input_plugins(
    name: Annotated[
        str,
        CheckDirectoryIsAllowedDep,
        CheckConfigurationExistsDep,
    ],
    plugin_configs: Annotated[
        list[InputPluginNamedConfig],
        Body(description='List of input plugin configs'),
    ],
    settings: SettingsDep,
    timezone: TimezoneDep,
) -> list[InputPlugin]:
    """Load input plugins using provided input plugin configurations.

    Parameters
    ----------
    name : str
        Name of the generator directory.

    plugin_configs : list[InputPluginNamedConfig]
        Plugin configurations.

    settings : SettingsDep
        Application settings dependency.

    timezone : TimezoneDep, default=UTC
        Timezone dependency.

    Returns
    -------
    list[InputPlugin]
        Loaded input plugins.

    Raises
    ------
    HTTPException
        If some of the plugins cannot be initialized or some of the
        dependency fails to load.

    """
    path = (settings.path.generators_dir / name).resolve()

    plugins: list[InputPlugin] = []
    for i, plugin_config in enumerate(plugin_configs, start=1):
        plugin_config = cast('PluginNamedConfig', plugin_config)

        try:
            plugin = await asyncio.to_thread(
                lambda i=i,  # type: ignore[misc]
                plugin_config=plugin_config: (
                    init_plugin(
                        name=plugin_config.get_name(),
                        type='input',
                        config=plugin_config.get_config().model_dump(),
                        params={
                            'id': i,
                            'timezone': timezone,
                            'base_path': path,
                        },
                    )
                ),
            )
        except InitializationError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    'message': str(e),
                    'context': e.context,
                },
            ) from None

        plugins.append(plugin)

    return plugins


InputPluginsDep = Annotated[list[InputPlugin], Depends(load_input_plugins)]


@set_responses(
    responses=merge_responses(
        check_directory_is_allowed.responses,
        check_configuration_exists.responses,
        {500: {'description': 'Event plugin cannot be initialized'}},
    ),
)
async def load_event_plugin(
    name: Annotated[
        str,
        CheckDirectoryIsAllowedDep,
        CheckConfigurationExistsDep,
    ],
    plugin_config: Annotated[
        EventPluginNamedConfig,
        Body(description='Event plugin config'),
    ],
    settings: SettingsDep,
) -> EventPlugin:
    """Load event plugin using provided event plugin configuration.

    Parameters
    ----------
    name : str
        Name of the generator directory.

    plugin_config : EventPluginNamedConfig
        Plugin configuration.

    settings : SettingsDep
        Application settings dependency.

    Returns
    -------
    EventPlugin
        Loaded event plugin.

    Raises
    ------
    HTTPException
        If plugin cannot be initialized or some of the dependency fails
        to load.

    """
    path = (settings.path.generators_dir / name).resolve()

    plugin_named_config = cast('PluginNamedConfig', plugin_config)

    try:
        return await asyncio.to_thread(
            lambda: (
                init_plugin(
                    name=plugin_named_config.get_name(),
                    type='event',
                    config=plugin_named_config.get_config().model_dump(),
                    params={
                        'id': 1,
                        'base_path': path,
                    },
                )
            ),
        )
    except InitializationError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                'message': str(e),
                'context': e.context,
            },
        ) from None


EventPluginDep = Annotated[EventPlugin, Depends(load_event_plugin)]


@set_responses(
    responses=merge_responses(
        check_directory_is_allowed.responses,
        check_configuration_exists.responses,
        {400: {'description': 'Event plugin was not previously initialized'}},
    ),
)
async def get_event_plugin_from_storage(
    name: Annotated[
        str,
        CheckDirectoryIsAllowedDep,
        CheckConfigurationExistsDep,
    ],
    settings: SettingsDep,
) -> EventPlugin:
    """Get previously initialized event plugin from storage.

    Parameters
    ----------
    name : str
        Name of the generator directory.

    settings : SettingsDep
        Application settings dependency.

    Returns
    -------
    EventPlugin
        Event plugin.

    Raises
    ------
    HTTPException
        If event plugin was not previously initialized or some of the
        dependency fails to load.

    """
    path = (settings.path.generators_dir / name).resolve()

    if not EVENT_PLUGINS.is_set(path=path):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Event plugin was not previously initialized',
        )

    return EVENT_PLUGINS.get(path)


EventPluginFromStorageDep = Annotated[
    EventPlugin,
    Depends(get_event_plugin_from_storage),
]


@set_responses(
    responses={
        400: {
            'description': (
                'Currently used plugin is inappropriate for this operation'
            ),
        },
    },
)
async def check_event_plugin_is_template(plugin: EventPlugin) -> EventPlugin:
    """Check that provided event plugin is `template` event plugin.

    Parameters
    ----------
    plugin : EventPlugin
        Event plugin to check.

    Returns
    -------
    TemplateEventPlugin
        Original event plugin.

    Raises
    ------
    HTTPException
        If currently used plugin is inappropriate for this operation.

    """
    if not isinstance(plugin, TemplateEventPlugin):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Currently used plugin is inappropriate for this operation',
        )

    return plugin


CheckEventPluginIsTemplateDep = Annotated[
    TemplateEventPlugin,
    Depends(check_event_plugin_is_template),
]


@set_responses(
    responses=merge_responses(
        get_event_plugin_from_storage.responses,
        check_event_plugin_is_template.responses,
        {
            404: {
                'description': (
                    'State with provided template alias is not found'
                ),
            },
        },
    ),
)
async def get_template_event_plugin_local_state(
    plugin: Annotated[
        EventPluginFromStorageDep,
        CheckEventPluginIsTemplateDep,
    ],
    alias: Annotated[
        str,
        Path(description='Alias of template to get state of'),
    ],
) -> SingleThreadState:
    """Get local state of provided template by its alias of template event
    plugin.

    Parameters
    ----------
    plugin : EventPluginFromStorageDep
        Template event plugin from storage dependency.

    alias : str
        Alias of template to get state of.

    Returns
    -------
    SingleThreadState
        Local state of template.

    Raises
    ------
    HTTPException
        If state with provided template alias is not found or some of
        the dependency fails to load.

    """
    plugin = cast('TemplateEventPlugin', plugin)

    try:
        return plugin.local_states[alias]
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='State with provided template alias is not found',
        ) from None


TemplateEventPluginLocalStateDep = Annotated[
    SingleThreadState,
    Depends(get_template_event_plugin_local_state),
]


@set_responses(
    responses=merge_responses(
        get_event_plugin_from_storage.responses,
        check_event_plugin_is_template.responses,
    ),
)
async def get_template_event_plugin_shared_state(
    plugin: Annotated[
        EventPluginFromStorageDep,
        CheckEventPluginIsTemplateDep,
    ],
) -> SingleThreadState:
    """Get shared state of template event plugin.

    Parameters
    ----------
    plugin : EventPluginFromStorageDep
        Template event plugin from storage dependency.

    Returns
    -------
    SingleThreadState
        Shared state.

    Raises
    ------
    HTTPException
        If some of the dependency fails to load.

    """
    plugin = cast('TemplateEventPlugin', plugin)
    return plugin.shared_state


TemplateEventPluginSharedStateDep = Annotated[
    SingleThreadState,
    Depends(get_template_event_plugin_shared_state),
]


@set_responses(
    responses=merge_responses(
        get_event_plugin_from_storage.responses,
        check_event_plugin_is_template.responses,
    ),
)
async def get_template_event_plugin_global_state(
    plugin: Annotated[
        EventPluginFromStorageDep,
        CheckEventPluginIsTemplateDep,
    ],
) -> MultiThreadState:
    """Get global state of template event plugin.

    Parameters
    ----------
    plugin : EventPluginFromStorageDep
        Template event plugin from storage dependency.

    Returns
    -------
    MultiThreadState
        Global state.

    Raises
    ------
    HTTPException
        If some of the dependency fails to load.

    """
    plugin = cast('TemplateEventPlugin', plugin)
    return plugin.global_state


TemplateEventPluginGlobalStateDep = Annotated[
    SingleThreadState,
    Depends(get_template_event_plugin_global_state),
]
