"""Tests for clickhouse output plugin."""

from unittest.mock import patch

from eventum.plugins.output.plugins.clickhouse.config import (
    ClickhouseOutputPluginConfig,
)
from eventum.plugins.output.plugins.clickhouse.plugin import (
    ClickhouseOutputPlugin,
)


def _make_plugin(**config_overrides: object) -> ClickhouseOutputPlugin:
    config = ClickhouseOutputPluginConfig(
        host='localhost',
        table='events',
        **config_overrides,  # type: ignore[arg-type]
    )
    return ClickhouseOutputPlugin(config=config, params={'id': 1})


def test_create_pool_manager_default_maxsize() -> None:
    """Default `pool_maxsize=32` is forwarded to the pool manager."""
    plugin = _make_plugin()
    with patch(
        'eventum.plugins.output.plugins.clickhouse.plugin.get_pool_manager'
    ) as mock_pool:
        plugin._create_pool_manager()  # noqa: SLF001

    options = mock_pool.call_args.kwargs
    assert options['maxsize'] == 32  # noqa: S101, PLR2004
    assert options['verify'] is True  # noqa: S101
    assert 'ca_cert' not in options  # noqa: S101
    assert 'client_cert' not in options  # noqa: S101
    assert 'http_proxy' not in options  # noqa: S101
    assert 'https_proxy' not in options  # noqa: S101


def test_create_pool_manager_custom_maxsize() -> None:
    """Custom `pool_maxsize` overrides the default."""
    plugin = _make_plugin(pool_maxsize=256)
    with patch(
        'eventum.plugins.output.plugins.clickhouse.plugin.get_pool_manager'
    ) as mock_pool:
        plugin._create_pool_manager()  # noqa: SLF001

    assert mock_pool.call_args.kwargs['maxsize'] == 256  # noqa: S101, PLR2004


def test_create_pool_manager_https_proxy_routed_by_protocol() -> None:
    """`proxy_url` is routed to `https_proxy` when protocol is HTTPS."""
    plugin = _make_plugin(
        protocol='https',
        proxy_url='https://proxy.example.com',
    )
    with patch(
        'eventum.plugins.output.plugins.clickhouse.plugin.get_pool_manager'
    ) as mock_pool:
        plugin._create_pool_manager()  # noqa: SLF001

    options = mock_pool.call_args.kwargs
    assert options['https_proxy'] == 'https://proxy.example.com/'  # noqa: S101
    assert 'http_proxy' not in options  # noqa: S101


def test_create_pool_manager_http_proxy_routed_by_protocol() -> None:
    """`proxy_url` is routed to `http_proxy` when protocol is HTTP."""
    plugin = _make_plugin(proxy_url='http://proxy.example.com')
    with patch(
        'eventum.plugins.output.plugins.clickhouse.plugin.get_pool_manager'
    ) as mock_pool:
        plugin._create_pool_manager()  # noqa: SLF001

    options = mock_pool.call_args.kwargs
    assert options['http_proxy'] == 'http://proxy.example.com/'  # noqa: S101
    assert 'https_proxy' not in options  # noqa: S101


def test_create_pool_manager_server_host_name_with_verify() -> None:
    """`server_host_name` sets both `assert_hostname` and `server_hostname`
    when verify is enabled.
    """
    plugin = _make_plugin(verify=True, server_host_name='ch.internal')
    with patch(
        'eventum.plugins.output.plugins.clickhouse.plugin.get_pool_manager'
    ) as mock_pool:
        plugin._create_pool_manager()  # noqa: SLF001

    options = mock_pool.call_args.kwargs
    assert options['assert_hostname'] == 'ch.internal'  # noqa: S101
    assert options['server_hostname'] == 'ch.internal'  # noqa: S101


def test_create_pool_manager_server_host_name_without_verify() -> None:
    """`server_host_name` skips `assert_hostname` when verify is disabled."""
    plugin = _make_plugin(verify=False, server_host_name='ch.internal')
    with patch(
        'eventum.plugins.output.plugins.clickhouse.plugin.get_pool_manager'
    ) as mock_pool:
        plugin._create_pool_manager()  # noqa: SLF001

    options = mock_pool.call_args.kwargs
    assert 'assert_hostname' not in options  # noqa: S101
    assert options['server_hostname'] == 'ch.internal'  # noqa: S101
