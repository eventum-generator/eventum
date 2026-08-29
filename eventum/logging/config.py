"""Configuration for logging system."""

import logging
import logging.handlers
from collections.abc import Hashable
from pathlib import Path
from typing import TYPE_CHECKING, Literal, assert_never

import structlog

from eventum.logging.channels import (
    CHANNEL_ATTRIBUTE,
    CHANNEL_MAIN,
    ChannelFilter,
)
from eventum.logging.file_paths import construct_channel_logfile_path
from eventum.logging.handlers import RoutingHandler
from eventum.logging.processors import derive_extras, remove_keys_processor

if TYPE_CHECKING:
    from structlog.typing import Processor

type LogLevel = Literal['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']

DEFAULT_THIRD_PARTY_LEVEL: LogLevel = 'WARNING'
"""Level of third-party libraries when none is configured."""

ATTRIBUTION_KEYS = ('generator_id', 'component')
"""Keys that attribute a record to a channel."""

LEVELED_LOGGERS = ('eventum', 'uvicorn', 'mcp')
"""Loggers that carry the configured log level.

Every other logger inherits the level of the root logger, which is the
level of third-party libraries.
"""

CLAIMED_LOGGERS = ('uvicorn', 'uvicorn.access', 'uvicorn.error')
"""Loggers a library configures for itself.

Their own handlers and levels are dropped, so their records reach the
handlers of the root logger like every other record does.
"""


def disable() -> None:
    """Disable all logging system."""
    logging.disable()
    structlog.configure(
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def clear() -> None:
    """Clear logging configuration."""
    loggers = [
        logging.getLogger(name) for name in logging.root.manager.loggerDict
    ]
    loggers.append(logging.getLogger())

    for logger in loggers:
        handlers = logger.handlers[:]

        for handler in handlers:
            logger.removeHandler(handler)
            handler.close()

        logger.setLevel(logging.NOTSET)
        logger.propagate = True

    structlog.reset_defaults()


def use_stderr(level: LogLevel) -> None:
    """Configure logging for writing to console.

    Parameters
    ----------
    level : LogLevel
        Log level.

    Notes
    -----
    Third-party libraries are limited to warnings, or to `level` when
    it is stricter, so they never log more than the application does.

    """
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            processor=structlog.dev.ConsoleRenderer(colors=True),
            foreign_pre_chain=_build_foreign_pre_chain(),
        ),
    )

    logging.getLogger().addHandler(handler)

    _claim_library_loggers()
    _configure_levels(
        level=level,
        third_party_level=_stricter(level, DEFAULT_THIRD_PARTY_LEVEL),
    )
    _configure_structlog()


def use_console_and_file(  # noqa: PLR0913 - log settings are six knobs
    format: Literal['plain', 'json'],
    level: LogLevel,
    logs_dir: Path,
    max_bytes: int,
    backup_count: int,
    third_party_level: LogLevel = DEFAULT_THIRD_PARTY_LEVEL,
) -> None:
    """Configure logging for writing to console and file.

    Parameters
    ----------
    format : Literal['plain', 'json']
        Log format.

    level : LogLevel
        Log level.

    logs_dir : Path
        Directory for log files.

    max_bytes : int
        Max bytes for log file before triggering rollover.

    backup_count : int
        Number of rolled over log files to keep.

    third_party_level : LogLevel, default='WARNING'
        Log level of third-party libraries.

    Notes
    -----
    Every record goes to the file of exactly one channel, while the
    console receives all of them, so it stays the combined view.

    """
    match format:
        case 'json':
            renderer: Processor = structlog.processors.JSONRenderer(
                ensure_ascii=False,
            )
        case 'plain':
            renderer = structlog.dev.ConsoleRenderer(
                colors=False,
            )
        case f:
            assert_never(f)

    if not logs_dir.exists():
        logs_dir.mkdir(parents=True)

    file_formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            remove_keys_processor(ATTRIBUTION_KEYS),
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
        foreign_pre_chain=_build_foreign_pre_chain(),
    )

    def build_channel_handler(channel: Hashable) -> logging.Handler:
        """Build rotating file handler of a channel."""
        handler = logging.handlers.RotatingFileHandler(
            filename=construct_channel_logfile_path(
                format=format,
                logs_dir=logs_dir,
                channel=str(channel),
            ),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8',
        )
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(file_formatter)

        return handler

    # Console handler
    stderr_handler = logging.StreamHandler()
    stderr_handler.setLevel(logging.DEBUG)
    stderr_handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            processor=renderer,
            foreign_pre_chain=_build_foreign_pre_chain(),
        ),
    )

    # Routing handler; the main channel is served by the default
    # handler, so a single handler owns each log file
    routing_handler = RoutingHandler(
        attribute=CHANNEL_ATTRIBUTE,
        handler_factory=build_channel_handler,
        default_handler=build_channel_handler(CHANNEL_MAIN),
        default_value=CHANNEL_MAIN,
    )
    routing_handler.setLevel(logging.DEBUG)
    routing_handler.addFilter(ChannelFilter())

    logger = logging.getLogger()
    logger.addHandler(stderr_handler)
    logger.addHandler(routing_handler)

    _claim_library_loggers()
    _configure_levels(level=level, third_party_level=third_party_level)
    _configure_structlog()


def _configure_structlog() -> None:
    """Configure structlog to render through the stdlib handlers."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt='iso', utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            derive_extras(ATTRIBUTION_KEYS)(
                structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
            ),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def _build_foreign_pre_chain() -> list[Processor]:
    """Build processor chain that shapes records of other libraries.

    Returns
    -------
    list[Processor]
        Chain that gives a record emitted through stdlib logging the
        same keys a record of the application carries.

    """
    return [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt='iso', utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]


def _claim_library_loggers() -> None:
    """Reset loggers that a library configured for itself."""
    for name in CLAIMED_LOGGERS:
        logger = logging.getLogger(name)

        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        logger.setLevel(logging.NOTSET)
        logger.propagate = True


def _configure_levels(level: LogLevel, third_party_level: LogLevel) -> None:
    """Set levels of the root logger and of the leveled loggers.

    Parameters
    ----------
    level : LogLevel
        Log level of the application.

    third_party_level : LogLevel
        Log level of third-party libraries.

    Notes
    -----
    Levels are set on loggers rather than on handlers, so a muted
    library is cut off before its record is built.

    """
    logging.getLogger().setLevel(third_party_level)

    for name in LEVELED_LOGGERS:
        logging.getLogger(name).setLevel(level)


def _stricter(first: LogLevel, second: LogLevel) -> LogLevel:
    """Return the stricter of two levels."""
    levels = logging.getLevelNamesMapping()

    return first if levels[first] >= levels[second] else second
