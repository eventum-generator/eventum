"""Tests for logging configuration."""

import logging
from collections.abc import Iterator
from pathlib import Path

import pytest
import structlog

from eventum.logging.config import use_console_and_file
from eventum.logging.file_paths import construct_main_logfile_path

# 'file' spelled in Cyrillic
NON_ASCII_VALUE = 'файл'


@pytest.fixture
def isolated_logging() -> Iterator[None]:
    """Restore root logger handlers and structlog defaults."""
    root = logging.getLogger()
    handlers = root.handlers[:]
    level = root.level
    root.handlers.clear()

    yield

    for handler in root.handlers[:]:
        root.removeHandler(handler)
        handler.close()

    root.handlers.extend(handlers)
    root.setLevel(level)
    structlog.reset_defaults()


def test_json_logs_keep_non_ascii_unescaped(
    tmp_path: Path,
    isolated_logging: None,  # noqa: ARG001
) -> None:
    """Non-ASCII fields are logged verbatim, not as escapes."""
    use_console_and_file(
        format='json',
        level='INFO',
        logs_dir=tmp_path,
        max_bytes=1024 * 1024,
        backup_count=1,
    )

    structlog.get_logger().info('Test message', file_path=NON_ASCII_VALUE)

    log_path = construct_main_logfile_path(format='json', logs_dir=tmp_path)
    content = log_path.read_text(encoding='utf-8')
    assert NON_ASCII_VALUE in content
    assert '\\u' not in content
