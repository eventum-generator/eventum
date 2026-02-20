"""Tests for clickhouse output plugin config."""

import pytest
from pydantic import ValidationError

from eventum.plugins.output.plugins.clickhouse.config import (
    ClickhouseOutputPluginConfig,
)


def test_minimal_valid():
    config = ClickhouseOutputPluginConfig(host='localhost', table='events')
    assert config.host == 'localhost'
    assert config.table == 'events'
    assert config.port == 8123
    assert config.database == 'default'
    assert config.protocol == 'http'


def test_missing_host():
    with pytest.raises(ValidationError):
        ClickhouseOutputPluginConfig(table='events')


def test_missing_table():
    with pytest.raises(ValidationError):
        ClickhouseOutputPluginConfig(host='localhost')


def test_port_boundary():
    config = ClickhouseOutputPluginConfig(
        host='localhost', table='events', port=65535
    )
    assert config.port == 65535

    with pytest.raises(ValidationError):
        ClickhouseOutputPluginConfig(
            host='localhost', table='events', port=0
        )


def test_custom_database_and_protocol():
    config = ClickhouseOutputPluginConfig(
        host='db.example.com',
        table='logs',
        database='analytics',
        protocol='https',
    )
    assert config.database == 'analytics'
    assert config.protocol == 'https'


def test_empty_host_raises():
    with pytest.raises(ValidationError):
        ClickhouseOutputPluginConfig(host='', table='events')


def test_empty_table_raises():
    with pytest.raises(ValidationError):
        ClickhouseOutputPluginConfig(host='localhost', table='')
