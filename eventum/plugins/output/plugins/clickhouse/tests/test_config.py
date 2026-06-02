"""Tests for clickhouse output plugin config."""

import pytest
from pydantic import ValidationError

from eventum.plugins.output.plugins.clickhouse.config import (
    ClickhouseOutputPluginConfig,
)


def test_minimal_valid() -> None:
    """Defaults are applied when only required fields are set."""
    config = ClickhouseOutputPluginConfig(host='localhost', table='events')
    assert config.host == 'localhost'  # noqa: S101
    assert config.table == 'events'  # noqa: S101
    assert config.port == 8123  # noqa: S101, PLR2004
    assert config.database == 'default'  # noqa: S101
    assert config.protocol == 'http'  # noqa: S101
    assert config.pool_maxsize == 32  # noqa: S101, PLR2004


def test_pool_maxsize_custom() -> None:
    """Custom `pool_maxsize` value is propagated."""
    config = ClickhouseOutputPluginConfig(
        host='localhost', table='events', pool_maxsize=100
    )
    assert config.pool_maxsize == 100  # noqa: S101, PLR2004


def test_pool_maxsize_must_be_positive() -> None:
    """`pool_maxsize` below 1 is rejected."""
    with pytest.raises(ValidationError):
        ClickhouseOutputPluginConfig(
            host='localhost', table='events', pool_maxsize=0
        )


def test_missing_host() -> None:
    """Omitting required `host` triggers validation error."""
    with pytest.raises(ValidationError):
        ClickhouseOutputPluginConfig(table='events')  # type: ignore[call-arg]


def test_missing_table() -> None:
    """Omitting required `table` triggers validation error."""
    with pytest.raises(ValidationError):
        ClickhouseOutputPluginConfig(host='localhost')  # type: ignore[call-arg]


def test_port_boundary() -> None:
    """Port accepts max value and rejects 0."""
    config = ClickhouseOutputPluginConfig(
        host='localhost', table='events', port=65535
    )
    assert config.port == 65535  # noqa: S101, PLR2004

    with pytest.raises(ValidationError):
        ClickhouseOutputPluginConfig(host='localhost', table='events', port=0)


def test_custom_database_and_protocol() -> None:
    """Custom database name and HTTPS protocol are propagated."""
    config = ClickhouseOutputPluginConfig(
        host='db.example.com',
        table='logs',
        database='analytics',
        protocol='https',
    )
    assert config.database == 'analytics'  # noqa: S101
    assert config.protocol == 'https'  # noqa: S101


def test_empty_host_raises() -> None:
    """Empty `host` string is rejected."""
    with pytest.raises(ValidationError):
        ClickhouseOutputPluginConfig(host='', table='events')


def test_empty_table_raises() -> None:
    """Empty `table` string is rejected."""
    with pytest.raises(ValidationError):
        ClickhouseOutputPluginConfig(host='localhost', table='')
