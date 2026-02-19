"""Configuration for logging system."""

import logging
import logging.config
import logging.handlers
from pathlib import Path
from typing import TYPE_CHECKING, Literal, assert_never

import structlog

from eventum.logging.file_paths import (
    construct_generator_logfile_path,
    construct_main_logfile_path,
    construct_server_logfile_path,
)
from eventum.logging.handlers import RoutingHandler
from eventum.logging.processors import derive_extras, remove_keys_processor

if TYPE_CHECKING:
    from structlog.typing import Processor


type LogLevel = Literal['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']


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

    """
    uvicorn_logger = logging.getLogger('uvicorn')
    uvicorn_logger.handlers.clear()
    uvicorn_logger.propagate = False

    logging.config.dictConfig(
        {
            'version': 1,
            'formatters': {
                'stderr-formatter': {
                    '()': structlog.stdlib.ProcessorFormatter,
                    'processor': structlog.dev.ConsoleRenderer(colors=True),
                },
                'stderr-access-formatter': {
                    'format': (
                        '%(asctime)s [%(levelname)s] %(message)s [%(name)s]'
                    ),
                },
            },
            'handlers': {
                'stderr': {
                    'level': level,
                    'formatter': 'stderr-formatter',
                    'class': 'logging.StreamHandler',
                    'stream': 'ext://sys.stderr',
                },
                'stderr-access': {
                    'level': level,
                    'formatter': 'stderr-access-formatter',
                    'class': 'logging.StreamHandler',
                    'stream': 'ext://sys.stderr',
                },
            },
            'loggers': {
                '': {
                    'handlers': ['stderr'],
                    'level': 'DEBUG',
                    'propagate': True,
                },
                'uvicorn.access': {
                    'handlers': ['stderr-access'],
                    'level': 'DEBUG',
                    'propagate': True,
                },
            },
        },
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def use_console_and_file(
    format: Literal['plain', 'json'],
    level: LogLevel,
    logs_dir: Path,
    max_bytes: int,
    backup_count: int,
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

    """
    match format:
        case 'json':
            renderer: Processor = structlog.processors.JSONRenderer()
        case 'plain':
            renderer = structlog.dev.ConsoleRenderer(
                colors=False,
            )
        case f:
            assert_never(f)

    if not logs_dir.exists():
        logs_dir.mkdir(parents=True)

    console_formatter = structlog.stdlib.ProcessorFormatter(
        processor=renderer,
    )
    file_formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            remove_keys_processor(['generator_id']),
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    # Console handler
    stderr_handler = logging.StreamHandler()
    stderr_handler.setLevel(logging.DEBUG)
    stderr_handler.setFormatter(console_formatter)

    # Default routing handler
    default_routing_handler = logging.handlers.RotatingFileHandler(
        filename=construct_main_logfile_path(format=format, logs_dir=logs_dir),
        maxBytes=max_bytes,
        backupCount=backup_count,
    )
    default_routing_handler.setLevel(logging.DEBUG)
    default_routing_handler.setFormatter(file_formatter)

    # Routing handler
    routing_handler = RoutingHandler(
        attribute='generator_id',
        handler_factory=lambda attr: logging.handlers.RotatingFileHandler(
            filename=construct_generator_logfile_path(
                format=format,
                logs_dir=logs_dir,
                generator_id=str(attr),
            ),
            maxBytes=max_bytes,
            backupCount=backup_count,
        ),
        default_handler=default_routing_handler,
        formatter=file_formatter,
    )
    routing_handler.setLevel(logging.DEBUG)
    routing_handler.setFormatter(file_formatter)

    logger = logging.getLogger()
    logger.addHandler(stderr_handler)
    logger.addHandler(routing_handler)
    logger.setLevel(level)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt='iso', utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            derive_extras(['generator_id'])(
                structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
            ),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    _configure_uvicorn_logger(
        level=level,
        logs_dir=logs_dir,
        max_bytes=max_bytes,
        backup_count=backup_count,
    )


def _configure_uvicorn_logger(
    level: LogLevel,
    logs_dir: Path,
    max_bytes: int,
    backup_count: int,
) -> None:
    """Configure uvicorn loggers for writing to console and file.

    Parameters
    ----------
    level : LogLevel
        Log level.

    logs_dir : Path
        Directory for log files.

    max_bytes : int
        Max bytes for log file before triggering rollover.

    backup_count : int
        Number of rolled over log files to keep.

    """
    stderr_handler = logging.StreamHandler()
    stderr_handler.setLevel(logging.DEBUG)
    stderr_handler.setFormatter(
        logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s [%(name)s]',
        ),
    )

    for log_type in ('error', 'access'):
        file_handler = logging.handlers.RotatingFileHandler(
            filename=construct_server_logfile_path(
                logs_dir=logs_dir,
                log_type=log_type,
            ),
            maxBytes=max_bytes,
            backupCount=backup_count,
        )
        file_handler.setFormatter(
            logging.Formatter(
                '%(asctime)s [%(levelname)s] %(message)s',
            ),
        )

        uvicorn_logger = logging.getLogger(f'uvicorn.{log_type}')
        uvicorn_logger.handlers.clear()
        uvicorn_logger.propagate = False
        uvicorn_logger.addHandler(stderr_handler)
        uvicorn_logger.addHandler(file_handler)
        uvicorn_logger.setLevel(level)
