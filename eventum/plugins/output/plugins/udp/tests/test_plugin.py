"""Tests for udp output plugin."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from eventum.plugins.output.exceptions import PluginOpenError, PluginWriteError
from eventum.plugins.output.plugins.udp.config import UdpOutputPluginConfig
from eventum.plugins.output.plugins.udp.plugin import UdpOutputPlugin

# --- Config tests ---


def test_minimal_config():
    config = UdpOutputPluginConfig(host='localhost', port=514)
    assert config.host == 'localhost'
    assert config.port == 514
    assert config.encoding == 'utf_8'
    assert config.separator == '\n'


def test_all_fields():
    config = UdpOutputPluginConfig(
        host='10.0.0.1',
        port=9000,
        encoding='ascii',
        separator='|',
    )
    assert config.host == '10.0.0.1'
    assert config.port == 9000
    assert config.encoding == 'ascii'
    assert config.separator == '|'


def test_missing_host():
    with pytest.raises(ValidationError):
        UdpOutputPluginConfig(port=514)  # type: ignore[call-arg]


def test_missing_port():
    with pytest.raises(ValidationError):
        UdpOutputPluginConfig(host='localhost')  # type: ignore[call-arg]


def test_empty_host():
    with pytest.raises(ValidationError):
        UdpOutputPluginConfig(host='', port=514)


def test_port_too_low():
    with pytest.raises(ValidationError):
        UdpOutputPluginConfig(host='localhost', port=0)


def test_port_too_high():
    with pytest.raises(ValidationError):
        UdpOutputPluginConfig(host='localhost', port=65536)


def test_invalid_encoding():
    with pytest.raises(ValidationError):
        UdpOutputPluginConfig(
            host='localhost',
            port=514,
            encoding='invalid',  # type: ignore[arg-type]
        )


# --- Plugin tests ---


def _make_mock_transport() -> MagicMock:
    transport = MagicMock(spec=asyncio.DatagramTransport)
    transport.sendto = MagicMock()
    transport.close = MagicMock()
    return transport


def _make_config(**overrides) -> UdpOutputPluginConfig:
    defaults = {'host': 'localhost', 'port': 514}
    return UdpOutputPluginConfig(**(defaults | overrides))


@pytest.fixture
def mock_endpoint():
    """Patch create_datagram_endpoint on the real event loop."""
    transport = _make_mock_transport()

    async def _create_endpoint(protocol_factory, **kwargs):
        protocol = protocol_factory()
        return transport, protocol

    with patch.object(
        asyncio.get_event_loop_policy(),
        '_local',
        create=True,
    ):
        yield transport, _create_endpoint


@pytest.mark.asyncio
async def test_plugin_write():
    transport = _make_mock_transport()
    loop = asyncio.get_running_loop()

    with patch.object(
        loop,
        'create_datagram_endpoint',
        new=AsyncMock(return_value=(transport, MagicMock())),
    ):
        config = _make_config()
        plugin = UdpOutputPlugin(config=config, params={'id': 1})

        await plugin.open()

        written = await plugin.write(events=['event1', 'event2'])
        assert written == 2

        assert transport.sendto.call_count == 2
        transport.sendto.assert_any_call(b'event1\n')
        transport.sendto.assert_any_call(b'event2\n')

        await plugin.close()
        transport.close.assert_called_once()


@pytest.mark.asyncio
async def test_plugin_custom_separator():
    transport = _make_mock_transport()
    loop = asyncio.get_running_loop()

    with patch.object(
        loop,
        'create_datagram_endpoint',
        new=AsyncMock(return_value=(transport, MagicMock())),
    ):
        config = _make_config(separator='|')
        plugin = UdpOutputPlugin(config=config, params={'id': 1})

        await plugin.open()
        await plugin.write(events=['a', 'b'])

        transport.sendto.assert_any_call(b'a|')
        transport.sendto.assert_any_call(b'b|')

        await plugin.close()


@pytest.mark.asyncio
async def test_plugin_open_error():
    loop = asyncio.get_running_loop()

    with patch.object(
        loop,
        'create_datagram_endpoint',
        new=AsyncMock(side_effect=OSError('Address not available')),
    ):
        config = _make_config()
        plugin = UdpOutputPlugin(config=config, params={'id': 1})

        with pytest.raises(PluginOpenError):
            await plugin.open()


@pytest.mark.asyncio
async def test_plugin_send_error():
    transport = _make_mock_transport()
    transport.sendto.side_effect = OSError('Network unreachable')
    loop = asyncio.get_running_loop()

    with patch.object(
        loop,
        'create_datagram_endpoint',
        new=AsyncMock(return_value=(transport, MagicMock())),
    ):
        config = _make_config()
        plugin = UdpOutputPlugin(config=config, params={'id': 1})

        await plugin.open()

        with pytest.raises(PluginWriteError):
            await plugin.write(events=['event1'])

        await plugin.close()


@pytest.mark.asyncio
async def test_plugin_encoding_error():
    transport = _make_mock_transport()
    loop = asyncio.get_running_loop()

    with patch.object(
        loop,
        'create_datagram_endpoint',
        new=AsyncMock(return_value=(transport, MagicMock())),
    ):
        config = _make_config(encoding='ascii')
        plugin = UdpOutputPlugin(config=config, params={'id': 1})

        await plugin.open()

        written = await plugin.write(events=['\xe9\xe8\xea'])
        assert written == 0

        transport.sendto.assert_not_called()

        await plugin.close()


@pytest.mark.asyncio
async def test_plugin_partial_encoding_error():
    transport = _make_mock_transport()
    loop = asyncio.get_running_loop()

    with patch.object(
        loop,
        'create_datagram_endpoint',
        new=AsyncMock(return_value=(transport, MagicMock())),
    ):
        config = _make_config(encoding='ascii')
        plugin = UdpOutputPlugin(config=config, params={'id': 1})

        await plugin.open()

        written = await plugin.write(events=['good', '\xe9bad', 'also_good'])
        assert written == 2

        assert transport.sendto.call_count == 2
        transport.sendto.assert_any_call(b'good\n')
        transport.sendto.assert_any_call(b'also_good\n')

        await plugin.close()


@pytest.mark.asyncio
async def test_plugin_write_empty_events():
    transport = _make_mock_transport()
    loop = asyncio.get_running_loop()

    with patch.object(
        loop,
        'create_datagram_endpoint',
        new=AsyncMock(return_value=(transport, MagicMock())),
    ):
        config = _make_config()
        plugin = UdpOutputPlugin(config=config, params={'id': 1})

        await plugin.open()

        written = await plugin.write(events=[])
        assert written == 0

        transport.sendto.assert_not_called()

        await plugin.close()


@pytest.mark.asyncio
async def test_plugin_write_before_open():
    config = _make_config()
    plugin = UdpOutputPlugin(config=config, params={'id': 1})

    with pytest.raises(PluginWriteError):
        await plugin.write(events=['event1'])
