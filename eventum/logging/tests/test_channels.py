"""Tests for log channels."""

import logging
from collections.abc import Iterator
from pathlib import Path

import pytest
import structlog

import eventum
from eventum.logging.channels import (
    CHANNEL_ATTRIBUTE,
    CONTEXT_FOLLOWING_PACKAGES,
    INSTANCE_CHANNELS,
    LOGGER_CHANNELS,
    ChannelFilter,
    resolve_channel,
)


@pytest.fixture(autouse=True)
def clear_context() -> Iterator[None]:
    """Drop context variables bound by a test."""
    yield

    structlog.contextvars.clear_contextvars()


def make_record(name: str, **attributes: object) -> logging.LogRecord:
    """Build a log record of the named logger."""
    record = logging.LogRecord(
        name=name,
        level=logging.INFO,
        pathname='test.py',
        lineno=1,
        msg='Test message',
        args=(),
        exc_info=None,
    )

    for key, value in attributes.items():
        setattr(record, key, value)

    return record


def test_every_package_is_classified() -> None:
    """Every package of eventum is either mapped or context-following."""
    root = Path(eventum.__file__).parent
    packages = {
        entry.name
        for entry in root.iterdir()
        if entry.is_dir() and (entry / '__init__.py').exists()
    }
    mapped = {
        prefix.removeprefix('eventum.')
        for prefix in LOGGER_CHANNELS
        if prefix.startswith('eventum.')
    }

    assert packages == mapped | CONTEXT_FOLLOWING_PACKAGES


def test_every_mapped_channel_is_addressable() -> None:
    """Every mapped channel can be requested by name."""
    assert set(LOGGER_CHANNELS.values()) <= INSTANCE_CHANNELS


def test_mapped_package_goes_to_its_channel() -> None:
    """A mapped package reaches the channel it is mapped to."""
    assert resolve_channel(make_record('eventum.api.routers.auth')) == 'server'
    assert resolve_channel(make_record('eventum.mcp.tools.live')) == 'mcp'
    assert resolve_channel(make_record('eventum.app.main')) == 'main'


def test_longest_logger_prefix_wins() -> None:
    """The access logger keeps its channel next to the server one."""
    assert resolve_channel(make_record('uvicorn.access')) == 'server_access'
    assert resolve_channel(make_record('uvicorn.error')) == 'server'
    assert resolve_channel(make_record('uvicorn')) == 'server'


def test_prefix_matches_on_dotted_boundary() -> None:
    """A prefix matches a whole name part, not a substring of it."""
    assert resolve_channel(make_record('mcpx.client')) == 'main'


def test_generator_id_of_record_wins_over_prefix() -> None:
    """A record naming a generator goes to that generator channel."""
    record = make_record('eventum.api.routers.auth', generator_id='gen-1')

    assert resolve_channel(record) == 'generator_gen-1'


def test_generator_id_of_context_attributes_foreign_record() -> None:
    """A library logging in a generator context reaches its channel."""
    structlog.contextvars.bind_contextvars(generator_id='gen-1')

    assert resolve_channel(make_record('httpx')) == 'generator_gen-1'


def test_unmapped_package_follows_component() -> None:
    """An unmapped package goes to the channel of its caller."""
    structlog.contextvars.bind_contextvars(component='server')

    assert resolve_channel(make_record('eventum.core.generator')) == 'server'


def test_library_follows_component() -> None:
    """A library goes to the channel of the code that called it."""
    structlog.contextvars.bind_contextvars(component='mcp')

    assert resolve_channel(make_record('httpx')) == 'mcp'


def test_hard_mapping_wins_over_component() -> None:
    """A mapped logger keeps its channel in a foreign context."""
    structlog.contextvars.bind_contextvars(component='server')

    assert resolve_channel(make_record('uvicorn.access')) == 'server_access'


def test_unknown_component_falls_back_to_main() -> None:
    """A component that names no channel is ignored."""
    structlog.contextvars.bind_contextvars(component='unknown')

    assert resolve_channel(make_record('httpx')) == 'main'


def test_unattributed_record_falls_back_to_main() -> None:
    """A record with nothing to attribute it goes to the main channel."""
    assert resolve_channel(make_record('httpx')) == 'main'


def test_filter_sets_resolved_channel() -> None:
    """The filter passes every record, carrying its channel."""
    record = make_record('uvicorn.access')

    assert ChannelFilter().filter(record) is True
    assert getattr(record, CHANNEL_ATTRIBUTE) == 'server_access'
