"""Tests for logging configuration."""

import json
import logging
from collections.abc import Iterator
from pathlib import Path
from threading import Thread

import pytest
import structlog

from eventum.logging.config import (
    CLAIMED_LOGGERS,
    LEVELED_LOGGERS,
    use_console_and_file,
    use_stderr,
)
from eventum.logging.file_paths import construct_channel_logfile_path

# 'file' spelled in Cyrillic
NON_ASCII_VALUE = 'файл'

MAX_BYTES = 1024 * 1024


@pytest.fixture
def isolated_logging() -> Iterator[None]:
    """Restore logger state and structlog defaults."""
    root = logging.getLogger()
    handlers = root.handlers[:]
    level = root.level
    root.handlers.clear()

    touched = [
        logging.getLogger(name)
        for name in {*LEVELED_LOGGERS, *CLAIMED_LOGGERS}
    ]
    state = [
        (logger, logger.handlers[:], logger.level, logger.propagate)
        for logger in touched
    ]

    yield

    for handler in root.handlers[:]:
        root.removeHandler(handler)
        handler.close()

    root.handlers.extend(handlers)
    root.setLevel(level)

    for logger, saved_handlers, saved_level, saved_propagate in state:
        logger.handlers.clear()
        logger.handlers.extend(saved_handlers)
        logger.setLevel(saved_level)
        logger.propagate = saved_propagate

    structlog.contextvars.clear_contextvars()
    structlog.reset_defaults()


def read_channel(
    logs_dir: Path,
    channel: str,
    format: str = 'plain',
) -> str:
    """Read content of a channel log file."""
    path = construct_channel_logfile_path(
        format=format,  # type: ignore[arg-type]
        logs_dir=logs_dir,
        channel=channel,
    )

    return path.read_text(encoding='utf-8') if path.exists() else ''


def configure_files(logs_dir: Path, **overrides: object) -> None:
    """Configure logging into the given directory."""
    parameters: dict = {
        'format': 'plain',
        'level': 'DEBUG',
        'logs_dir': logs_dir,
        'max_bytes': MAX_BYTES,
        'backup_count': 1,
    }
    parameters.update(overrides)

    use_console_and_file(**parameters)


def test_json_logs_keep_non_ascii_unescaped(
    tmp_path: Path,
    isolated_logging: None,  # noqa: ARG001
) -> None:
    """Non-ASCII fields are logged verbatim, not as escapes."""
    configure_files(tmp_path, format='json', level='INFO')

    structlog.get_logger().info('Test message', file_path=NON_ASCII_VALUE)

    content = read_channel(tmp_path, 'main', format='json')
    assert NON_ASCII_VALUE in content
    assert '\\u' not in content


def test_records_reach_the_file_of_their_channel(
    tmp_path: Path,
    isolated_logging: None,  # noqa: ARG001
) -> None:
    """Every channel collects its own records and nothing else."""
    configure_files(tmp_path)

    structlog.get_logger('eventum.app.main').info('App record')
    structlog.get_logger('eventum.api.routers.auth').info('API record')
    logging.getLogger('uvicorn.access').info('Access record')
    logging.getLogger('mcp.server.streamable_http').info('MCP record')

    main = read_channel(tmp_path, 'main')
    assert 'App record' in main
    assert 'API record' not in main
    assert 'Access record' not in main
    assert 'MCP record' not in main

    assert 'API record' in read_channel(tmp_path, 'server')
    assert 'Access record' in read_channel(tmp_path, 'server_access')
    assert 'MCP record' in read_channel(tmp_path, 'mcp')


def test_library_record_reaches_generator_channel(
    tmp_path: Path,
    isolated_logging: None,  # noqa: ARG001
) -> None:
    """A library logging in a generator thread reaches its channel."""
    configure_files(tmp_path)

    def emit() -> None:
        structlog.contextvars.bind_contextvars(generator_id='gen-1')
        logging.getLogger('httpx').warning('Transport record')

    thread = Thread(target=emit)
    thread.start()
    thread.join()

    assert 'Transport record' in read_channel(tmp_path, 'generator_gen-1')
    assert 'Transport record' not in read_channel(tmp_path, 'main')


def test_logger_configured_by_its_library_is_taken_over(
    tmp_path: Path,
    isolated_logging: None,  # noqa: ARG001
) -> None:
    """A logger a library configured for itself still reaches its file."""
    access = logging.getLogger('uvicorn.access')
    access.addHandler(logging.NullHandler())
    access.propagate = False
    access.setLevel(logging.ERROR)

    configure_files(tmp_path)

    access.info('Access record')

    assert 'Access record' in read_channel(tmp_path, 'server_access')


def test_own_and_foreign_records_carry_the_same_keys(
    tmp_path: Path,
    isolated_logging: None,  # noqa: ARG001
) -> None:
    """A record of a library is shaped like a record of the app."""
    configure_files(tmp_path, format='json')

    structlog.get_logger('eventum.app.main').info('Own record')
    logging.getLogger('eventum.app.main').info('Foreign record')

    content = read_channel(tmp_path, 'main', format='json')
    own, foreign = (json.loads(line) for line in content.splitlines())

    assert own.keys() == foreign.keys()
    assert own.keys() == {'event', 'level', 'logger', 'timestamp'}
    assert foreign['logger'] == 'eventum.app.main'
    assert foreign['level'] == 'info'
    assert foreign['timestamp'].endswith('Z')


def test_json_format_applies_to_every_channel(
    tmp_path: Path,
    isolated_logging: None,  # noqa: ARG001
) -> None:
    """The json format names every channel file after itself."""
    configure_files(tmp_path, format='json')

    logging.getLogger('uvicorn.access').info('Access record')

    assert (tmp_path / 'server_access.json').exists()
    assert not (tmp_path / 'server_access.log').exists()


def test_attribution_stays_out_of_channel_files(
    tmp_path: Path,
    isolated_logging: None,  # noqa: ARG001
) -> None:
    """A channel file does not repeat what its name already says."""
    configure_files(tmp_path, format='json')

    structlog.get_logger('eventum.core.generator').info(
        'Generator record',
        generator_id='gen-1',
    )

    record = json.loads(read_channel(tmp_path, 'generator_gen-1', 'json'))
    assert 'generator_id' not in record
    assert 'log_channel' not in record


def test_libraries_are_limited_to_their_own_level(
    tmp_path: Path,
    isolated_logging: None,  # noqa: ARG001
) -> None:
    """The level of libraries is independent of the app level."""
    configure_files(tmp_path, level='DEBUG', third_party_level='ERROR')

    assert not logging.getLogger('httpx').isEnabledFor(logging.WARNING)
    assert logging.getLogger('httpx').isEnabledFor(logging.ERROR)
    assert logging.getLogger('eventum.core.generator').isEnabledFor(
        logging.DEBUG,
    )


def test_libraries_default_to_warnings(
    tmp_path: Path,
    isolated_logging: None,  # noqa: ARG001
) -> None:
    """Libraries are limited to warnings unless configured otherwise."""
    configure_files(tmp_path, level='DEBUG')

    assert not logging.getLogger('httpx').isEnabledFor(logging.INFO)
    assert logging.getLogger('httpx').isEnabledFor(logging.WARNING)


def test_stderr_never_logs_libraries_above_the_app(
    isolated_logging: None,  # noqa: ARG001
) -> None:
    """On console libraries never log more than the app does."""
    use_stderr(level='CRITICAL')

    assert not logging.getLogger('httpx').isEnabledFor(logging.WARNING)
    assert logging.getLogger('eventum.cli').isEnabledFor(logging.CRITICAL)


def test_stderr_limits_libraries_to_warnings(
    isolated_logging: None,  # noqa: ARG001
) -> None:
    """On console a verbose app still keeps its libraries quiet."""
    use_stderr(level='DEBUG')

    assert not logging.getLogger('httpx').isEnabledFor(logging.INFO)
    assert logging.getLogger('eventum.cli').isEnabledFor(logging.DEBUG)
