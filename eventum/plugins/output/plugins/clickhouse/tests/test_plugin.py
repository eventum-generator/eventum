"""Tests for clickhouse output plugin."""

import os
import subprocess
import sys
import sysconfig
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from eventum.plugins.output.exceptions import PluginOpenError
from eventum.plugins.output.plugins.clickhouse.config import (
    ClickhouseOutputPluginConfig,
)
from eventum.plugins.output.plugins.clickhouse.plugin import (
    ClickhouseOutputPlugin,
)

_BASE_PATH = Path('/generators/demo')
_CLIENT_FACTORY = (
    'eventum.plugins.output.plugins.clickhouse.plugin.get_async_client'
)

# Variables that hide a re-enabled GIL: the first one overrides the
# interpreter decision, the second one skips loading C extensions
_GIL_MASKING_VARS = ('PYTHON_GIL', 'CLICKHOUSE_CONNECT_USE_C')


def _make_plugin(**config_overrides: object) -> ClickhouseOutputPlugin:
    config = ClickhouseOutputPluginConfig(
        host='localhost',
        table='events',
        **config_overrides,  # type: ignore[arg-type]
    )
    return ClickhouseOutputPlugin(
        config=config,
        params={'id': 1, 'base_path': _BASE_PATH},
    )


async def _open_plugin(plugin: ClickhouseOutputPlugin) -> dict:
    """Open plugin with mocked client factory and return its options."""
    with patch(_CLIENT_FACTORY, new_callable=AsyncMock) as factory:
        await plugin.open()

    return dict(factory.call_args.kwargs)


async def test_open_default_connection_options() -> None:
    """Default config is forwarded to the async client."""
    options = await _open_plugin(_make_plugin())

    assert options['host'] == 'localhost'
    assert options['port'] == 8123  # noqa: PLR2004
    assert options['interface'] == 'http'
    assert options['database'] == 'default'
    assert options['verify'] is True
    assert options['ca_cert'] is None
    assert options['client_cert'] is None
    assert options['client_cert_key'] is None
    assert options['server_host_name'] is None
    assert options['tls_mode'] is None
    assert options['http_proxy'] is None
    assert options['https_proxy'] is None


async def test_open_default_pool_maxsize() -> None:
    """Default `pool_maxsize=32` caps the connector limits."""
    options = await _open_plugin(_make_plugin())

    assert options['connector_limit'] == 32  # noqa: PLR2004
    assert options['connector_limit_per_host'] == 32  # noqa: PLR2004


async def test_open_custom_pool_maxsize() -> None:
    """Custom `pool_maxsize` overrides the default."""
    options = await _open_plugin(_make_plugin(pool_maxsize=256))

    assert options['connector_limit'] == 256  # noqa: PLR2004
    assert options['connector_limit_per_host'] == 256  # noqa: PLR2004


async def test_open_https_proxy_routed_by_protocol() -> None:
    """`proxy_url` is routed to `https_proxy` when protocol is HTTPS."""
    options = await _open_plugin(
        _make_plugin(protocol='https', proxy_url='https://proxy.example.com'),
    )

    assert options['https_proxy'] == 'https://proxy.example.com/'
    assert options['http_proxy'] is None


async def test_open_http_proxy_routed_by_protocol() -> None:
    """`proxy_url` is routed to `http_proxy` when protocol is HTTP."""
    options = await _open_plugin(
        _make_plugin(proxy_url='http://proxy.example.com'),
    )

    assert options['http_proxy'] == 'http://proxy.example.com/'
    assert options['https_proxy'] is None


async def test_open_tls_options_forwarded() -> None:
    """TLS options are forwarded with certificate paths resolved."""
    options = await _open_plugin(
        _make_plugin(
            protocol='https',
            port=8443,
            verify=True,
            server_host_name='ch.internal',
            tls_mode='mutual',
            ca_cert='certs/ca.pem',
            client_cert='certs/client.pem',
            client_cert_key='certs/client.key',
        ),
    )

    assert options['server_host_name'] == 'ch.internal'
    assert options['tls_mode'] == 'mutual'
    assert options['ca_cert'] == str(_BASE_PATH / 'certs/ca.pem')
    assert options['client_cert'] == str(_BASE_PATH / 'certs/client.pem')
    assert options['client_cert_key'] == str(_BASE_PATH / 'certs/client.key')


async def test_open_timeouts_forwarded() -> None:
    """Timeouts are forwarded under the client parameter names."""
    options = await _open_plugin(
        _make_plugin(connect_timeout=5, request_timeout=60),
    )

    assert options['connect_timeout'] == 5  # noqa: PLR2004
    assert options['send_receive_timeout'] == 60  # noqa: PLR2004


async def test_open_failure_is_wrapped() -> None:
    """Failed client initialization raises `PluginOpenError`."""
    plugin = _make_plugin()
    factory = AsyncMock(side_effect=ValueError('cannot connect'))

    with patch(_CLIENT_FACTORY, factory), pytest.raises(PluginOpenError):
        await plugin.open()


async def test_close_closes_client() -> None:
    """Closing the plugin closes the async client."""
    plugin = _make_plugin()
    client = AsyncMock()

    with patch(_CLIENT_FACTORY, AsyncMock(return_value=client)):
        await plugin.open()

    await plugin.close()

    client.close.assert_awaited_once()


async def test_write_returns_written_rows() -> None:
    """Number of written rows is taken from the insert result."""
    plugin = _make_plugin()
    client = AsyncMock()
    client.raw_insert.return_value.written_rows = 2

    with patch(_CLIENT_FACTORY, AsyncMock(return_value=client)):
        await plugin.open()

    written = await plugin.write(['{"a": 1}', '{"a": 2}'])

    assert written == 2  # noqa: PLR2004


@pytest.mark.skipif(
    not sysconfig.get_config_var('Py_GIL_DISABLED'),
    reason='GIL is always enabled on a non free-threaded interpreter',
)
def test_import_keeps_gil_disabled() -> None:
    """Importing the plugin does not re-enable the GIL."""
    env = {
        name: value
        for name, value in os.environ.items()
        if name not in _GIL_MASKING_VARS
    }

    result = subprocess.run(  # noqa: S603
        [
            sys.executable,
            '-c',
            'import sys;'
            'import eventum.plugins.output.plugins.clickhouse.plugin;'
            'print(f"gil_enabled={sys._is_gil_enabled()}")',
        ],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert 'gil_enabled=False' in result.stdout, result.stderr
