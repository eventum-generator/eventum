"""Log channels and the policy that attributes records to them."""

import logging
from collections.abc import Mapping
from typing import Any, Literal, get_args, override

import structlog

CHANNEL_ATTRIBUTE = 'log_channel'
"""Name of the log record attribute holding the resolved channel."""

type LogContext = Mapping[str, Any]
"""Fields bound to a context that attribute the records logged in it."""

type Component = Literal['main', 'server', 'mcp']
"""Part of the application a record originates from.

A component name doubles as the name of the channel it feeds.
"""

COMPONENTS: frozenset[str] = frozenset(get_args(Component.__value__))

type InstanceChannel = Literal['main', 'server', 'server_access', 'mcp']
"""Channel of the instance itself, as opposed to a generator channel.

Unlike generator channels, these are known upfront, which makes them
addressable by name.
"""

INSTANCE_CHANNELS: frozenset[str] = frozenset(
    get_args(InstanceChannel.__value__),
)

CHANNEL_MAIN: InstanceChannel = 'main'
CHANNEL_SERVER: InstanceChannel = 'server'
CHANNEL_SERVER_ACCESS: InstanceChannel = 'server_access'
CHANNEL_MCP: InstanceChannel = 'mcp'

LOGGER_CHANNELS: dict[str, InstanceChannel] = {
    'eventum.api': CHANNEL_SERVER,
    'eventum.server': CHANNEL_SERVER,
    'eventum.mcp': CHANNEL_MCP,
    'eventum.app': CHANNEL_MAIN,
    'eventum.cli': CHANNEL_MAIN,
    'uvicorn': CHANNEL_SERVER,
    'uvicorn.access': CHANNEL_SERVER_ACCESS,
    'mcp': CHANNEL_MCP,
}
"""Channels of logger name prefixes, the longest prefix wins."""

CONTEXT_FOLLOWING_PACKAGES: frozenset[str] = frozenset(
    {
        'core',
        'logging',
        'plugins',
        'security',
        'utils',
    },
)
"""Packages of `eventum` deliberately left out of `LOGGER_CHANNELS`.

Their records belong to whoever called them: a configuration load
served by a preview request belongs next to that request, while the
same load inside a generator belongs to the generator channel.
"""


def generator_channel(generator_id: str) -> str:
    """Return the channel of a generator.

    Parameters
    ----------
    generator_id : str
        ID of the generator.

    Returns
    -------
    str
        Channel name.

    """
    return f'generator_{generator_id}'


def bind_component(component: Component) -> None:
    """Bind the component to the context of the current thread or task.

    Parameters
    ----------
    component : Component
        Component that owns the context.

    Notes
    -----
    Contexts are not inherited by new threads, so every thread that
    logs on behalf of a component binds it at its entry point.

    """
    structlog.contextvars.bind_contextvars(component=component)


def capture_log_context() -> LogContext:
    """Capture the log context of the current thread or task.

    Returns
    -------
    LogContext
        Bound context, to be carried into a thread or a request that
        logs on behalf of the same origin.

    """
    return structlog.contextvars.get_contextvars()


def bind_log_context(context: LogContext) -> None:
    """Bind a captured log context in the current thread or task.

    Parameters
    ----------
    context : LogContext
        Context captured by `capture_log_context`.

    """
    structlog.contextvars.bind_contextvars(**context)


def resolve_channel(record: logging.LogRecord) -> str:
    """Resolve the channel of a log record.

    Parameters
    ----------
    record : logging.LogRecord
        Record to attribute.

    Returns
    -------
    str
        Channel name.

    Notes
    -----
    Four rules apply in order: the generator the record names, the
    channel mapped to its logger name, the component of the context it
    was emitted in, and the main channel as the fallback.

    """
    context = structlog.contextvars.get_contextvars()

    generator_id = _resolve_field(record, context, 'generator_id')
    if generator_id is not None:
        return generator_channel(generator_id)

    channel = _match_logger_channel(record.name)
    if channel is not None:
        return channel

    component = _resolve_field(record, context, 'component')
    if component in COMPONENTS:
        return component

    return CHANNEL_MAIN


def _resolve_field(
    record: logging.LogRecord,
    context: LogContext,
    field: str,
) -> str | None:
    """Get a field from the record, falling back to the context."""
    value = getattr(record, field, None) or context.get(field)

    return value if isinstance(value, str) and value else None


def _match_logger_channel(logger_name: str) -> str | None:
    """Get the channel mapped to the longest prefix of a logger name."""
    parts = logger_name.split('.')

    for length in range(len(parts), 0, -1):
        channel = LOGGER_CHANNELS.get('.'.join(parts[:length]))
        if channel is not None:
            return channel

    return None


class ChannelFilter(logging.Filter):
    """Filter that attributes every passing record to a channel.

    Notes
    -----
    Attach it to the handler that routes, not to a logger: filters of a
    logger never run for the records it receives by propagation, so a
    filter on the root logger would see nothing emitted by a
    third-party library.

    """

    @override
    def filter(self, record: logging.LogRecord) -> bool:
        setattr(record, CHANNEL_ATTRIBUTE, resolve_channel(record))

        return True
