"""Tests for tcp output plugin."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from eventum.plugins.output.exceptions import PluginOpenError, PluginWriteError
from eventum.plugins.output.plugins.tcp.config import TcpOutputPluginConfig
from eventum.plugins.output.plugins.tcp.plugin import TcpOutputPlugin

# --- Config tests ---


def test_minimal_config():
    config = TcpOutputPluginConfig(host='localhost', port=514)
    assert config.host == 'localhost'
    assert config.port == 514
    assert config.encoding == 'utf_8'
    assert config.connect_timeout == 10
    assert config.ssl is False
    assert config.verify is True


def test_all_fields():
    config = TcpOutputPluginConfig(
        host='10.0.0.1',
        port=6514,
        encoding='ascii',
        separator='\n',
        connect_timeout=30,
        ssl=True,
        verify=False,
    )
    assert config.host == '10.0.0.1'
    assert config.port == 6514
    assert config.encoding == 'ascii'
    assert config.separator == '\n'
    assert config.connect_timeout == 30
    assert config.ssl is True
    assert config.verify is False


def test_missing_host():
    with pytest.raises(ValidationError):
        TcpOutputPluginConfig(port=514)  # type: ignore[call-arg]


def test_missing_port():
    with pytest.raises(ValidationError):
        TcpOutputPluginConfig(host='localhost')  # type: ignore[call-arg]


def test_empty_host():
    with pytest.raises(ValidationError):
        TcpOutputPluginConfig(host='', port=514)


def test_port_too_low():
    with pytest.raises(ValidationError):
        TcpOutputPluginConfig(host='localhost', port=0)


def test_port_too_high():
    with pytest.raises(ValidationError):
        TcpOutputPluginConfig(host='localhost', port=65536)


def test_invalid_encoding():
    with pytest.raises(ValidationError):
        TcpOutputPluginConfig(
            host='localhost',
            port=514,
            encoding='invalid',  # type: ignore[arg-type]
        )


def test_connect_timeout_too_low():
    with pytest.raises(ValidationError):
        TcpOutputPluginConfig(
            host='localhost',
            port=514,
            connect_timeout=0,
        )


def test_client_cert_without_key():
    with pytest.raises(ValidationError):
        TcpOutputPluginConfig(
            host='localhost',
            port=514,
            ssl=True,
            client_cert='cert.pem',  # type: ignore
        )


def test_client_key_without_cert():
    with pytest.raises(ValidationError):
        TcpOutputPluginConfig(
            host='localhost',
            port=514,
            ssl=True,
            client_cert_key='key.pem',  # type: ignore
        )


def test_client_cert_with_key():
    config = TcpOutputPluginConfig(
        host='localhost',
        port=514,
        ssl=True,
        client_cert='cert.pem',  # type: ignore
        client_cert_key='key.pem',  # type: ignore
    )
    assert config.client_cert is not None
    assert config.client_cert_key is not None


def test_ca_cert_without_ssl():
    with pytest.raises(ValidationError, match='require ssl'):
        TcpOutputPluginConfig(
            host='localhost',
            port=514,
            ca_cert='ca.pem',  # type: ignore
        )


def test_client_cert_without_ssl():
    with pytest.raises(ValidationError, match='require ssl'):
        TcpOutputPluginConfig(
            host='localhost',
            port=514,
            client_cert='cert.pem',  # type: ignore
            client_cert_key='key.pem',  # type: ignore
        )


# --- Plugin tests ---


def _make_mock_writer(
    buffered: int = 0,
    high_water_mark: int = 65536,
) -> MagicMock:
    transport = MagicMock(spec=asyncio.Transport)
    transport.get_write_buffer_size = MagicMock(return_value=buffered)
    transport.get_write_buffer_limits = MagicMock(
        return_value=(high_water_mark // 4, high_water_mark),
    )
    transport.abort = MagicMock()

    writer = MagicMock(spec=asyncio.StreamWriter)
    writer.write = MagicMock()
    writer.drain = AsyncMock()
    writer.close = MagicMock()
    writer.wait_closed = AsyncMock()
    writer.is_closing = MagicMock(return_value=False)
    writer.transport = transport
    return writer


def _make_config(**overrides) -> TcpOutputPluginConfig:
    defaults = {'host': 'localhost', 'port': 514}
    return TcpOutputPluginConfig(**(defaults | overrides))


@pytest.mark.asyncio
@patch(
    'eventum.plugins.output.plugins.tcp.plugin.asyncio.open_connection',
)
async def test_plugin_write(mock_open_conn):
    writer = _make_mock_writer()
    mock_open_conn.return_value = (MagicMock(), writer)

    config = _make_config()
    plugin = TcpOutputPlugin(config=config, params={'id': 1})

    await plugin.open()

    written = await plugin.write(
        events=['event1', 'event2'],
    )
    assert written == 2

    writer.write.assert_called_once()
    writer.drain.assert_awaited()

    await plugin.close()
    writer.close.assert_called_once()
    writer.wait_closed.assert_awaited()


@pytest.mark.asyncio
@patch(
    'eventum.plugins.output.plugins.tcp.plugin.asyncio.open_connection',
)
async def test_plugin_custom_separator(mock_open_conn):
    writer = _make_mock_writer()
    mock_open_conn.return_value = (MagicMock(), writer)

    config = _make_config(separator='|')
    plugin = TcpOutputPlugin(config=config, params={'id': 1})

    await plugin.open()
    await plugin.write(events=['a', 'b'])

    call_args = writer.write.call_args[0][0]
    assert call_args == b'a|b|'

    await plugin.close()


@pytest.mark.asyncio
@patch(
    'eventum.plugins.output.plugins.tcp.plugin.asyncio.open_connection',
)
async def test_plugin_connection_refused(mock_open_conn):
    mock_open_conn.side_effect = OSError('Connection refused')

    config = _make_config()
    plugin = TcpOutputPlugin(config=config, params={'id': 1})

    with pytest.raises(PluginOpenError):
        await plugin.open()


@pytest.mark.asyncio
@patch(
    'eventum.plugins.output.plugins.tcp.plugin.asyncio.open_connection',
)
async def test_plugin_connection_timeout(mock_open_conn):
    async def slow_connect(*args, **kwargs):
        await asyncio.sleep(100)

    mock_open_conn.side_effect = slow_connect

    config = _make_config(connect_timeout=1)
    plugin = TcpOutputPlugin(config=config, params={'id': 1})

    with pytest.raises(PluginOpenError):
        await plugin.open()


@pytest.mark.asyncio
@patch(
    'eventum.plugins.output.plugins.tcp.plugin.asyncio.open_connection',
)
async def test_plugin_write_error(mock_open_conn):
    writer = _make_mock_writer()
    writer.drain.side_effect = OSError('Broken pipe')
    mock_open_conn.return_value = (MagicMock(), writer)

    config = _make_config()
    plugin = TcpOutputPlugin(config=config, params={'id': 1})

    await plugin.open()

    with pytest.raises(PluginWriteError):
        await plugin.write(events=['event1'])

    await plugin.close()


@pytest.mark.asyncio
@patch(
    'eventum.plugins.output.plugins.tcp.plugin.asyncio.open_connection',
)
async def test_plugin_encoding_error(mock_open_conn):
    writer = _make_mock_writer()
    mock_open_conn.return_value = (MagicMock(), writer)

    config = _make_config(encoding='ascii')
    plugin = TcpOutputPlugin(config=config, params={'id': 1})

    await plugin.open()

    with pytest.raises(PluginWriteError):
        await plugin.write(events=['\xe9\xe8\xea'])

    await plugin.close()


@pytest.mark.asyncio
@patch(
    'eventum.plugins.output.plugins.tcp.plugin.asyncio.open_connection',
)
async def test_plugin_close_broken_connection(mock_open_conn):
    writer = _make_mock_writer()
    writer.wait_closed.side_effect = ConnectionResetError(
        'Connection reset by peer',
    )
    mock_open_conn.return_value = (MagicMock(), writer)

    config = _make_config()
    plugin = TcpOutputPlugin(config=config, params={'id': 1})

    await plugin.open()
    await plugin.close()

    writer.close.assert_called_once()
    writer.wait_closed.assert_awaited()


@pytest.mark.asyncio
@patch(
    'eventum.plugins.output.plugins.tcp.plugin.asyncio.open_connection',
)
async def test_plugin_close_broken_pipe(mock_open_conn):
    writer = _make_mock_writer()
    writer.wait_closed.side_effect = BrokenPipeError('Broken pipe')
    mock_open_conn.return_value = (MagicMock(), writer)

    config = _make_config()
    plugin = TcpOutputPlugin(config=config, params={'id': 1})

    await plugin.open()
    await plugin.close()

    writer.close.assert_called_once()


@pytest.mark.asyncio
@patch(
    'eventum.plugins.output.plugins.tcp.plugin.asyncio.open_connection',
)
async def test_plugin_write_empty_events(mock_open_conn):
    writer = _make_mock_writer()
    mock_open_conn.return_value = (MagicMock(), writer)

    config = _make_config()
    plugin = TcpOutputPlugin(config=config, params={'id': 1})

    await plugin.open()

    written = await plugin.write(events=[])
    assert written == 0

    writer.write.assert_not_called()

    await plugin.close()


@pytest.mark.asyncio
async def test_plugin_write_before_open():
    config = _make_config()
    plugin = TcpOutputPlugin(config=config, params={'id': 1})

    with pytest.raises(PluginWriteError):
        await plugin.write(events=['event1'])


@pytest.mark.asyncio
@patch(
    'eventum.plugins.output.plugins.tcp.plugin.asyncio.open_connection',
)
async def test_plugin_reconnect_on_closed_writer(mock_open_conn):
    writer1 = _make_mock_writer()
    writer1.is_closing = MagicMock(return_value=False)
    writer2 = _make_mock_writer()
    writer2.is_closing = MagicMock(return_value=False)

    mock_open_conn.return_value = (MagicMock(), writer1)

    config = _make_config()
    plugin = TcpOutputPlugin(config=config, params={'id': 1})

    await plugin.open()
    await plugin.write(events=['before'])
    writer1.write.assert_called_once()

    # Simulate connection drop
    writer1.is_closing = MagicMock(return_value=True)
    mock_open_conn.return_value = (MagicMock(), writer2)

    await plugin.write(events=['after'])
    writer2.write.assert_called_once()

    await plugin.close()


@pytest.mark.asyncio
@patch(
    'eventum.plugins.output.plugins.tcp.plugin.asyncio.open_connection',
)
async def test_plugin_reconnect_failure(mock_open_conn):
    writer = _make_mock_writer()
    writer.is_closing = MagicMock(return_value=False)
    mock_open_conn.return_value = (MagicMock(), writer)

    config = _make_config()
    plugin = TcpOutputPlugin(config=config, params={'id': 1})

    await plugin.open()

    # Simulate connection drop + reconnect failure
    writer.is_closing = MagicMock(return_value=True)
    mock_open_conn.side_effect = OSError('Connection refused')

    with pytest.raises(PluginWriteError, match='reconnect'):
        await plugin.write(events=['event1'])


@pytest.mark.asyncio
@patch(
    'eventum.plugins.output.plugins.tcp.plugin.asyncio.open_connection',
)
async def test_plugin_refuses_to_write_into_backed_up_connection(
    mock_open_conn,
):
    """Events are failed rather than piled up on a target behind."""
    writer = _make_mock_writer(buffered=70000, high_water_mark=65536)
    mock_open_conn.return_value = (MagicMock(), writer)

    plugin = TcpOutputPlugin(config=_make_config(), params={'id': 1})
    await plugin.open()

    with pytest.raises(PluginWriteError, match='not accepting data'):
        await plugin.write(events=['event'])

    writer.write.assert_not_called()


@pytest.mark.asyncio
@patch(
    'eventum.plugins.output.plugins.tcp.plugin.asyncio.open_connection',
)
async def test_plugin_writes_into_connection_below_the_mark(mock_open_conn):
    """Data still buffered under the mark is no reason to refuse."""
    writer = _make_mock_writer(buffered=30000, high_water_mark=65536)
    mock_open_conn.return_value = (MagicMock(), writer)

    plugin = TcpOutputPlugin(config=_make_config(), params={'id': 1})
    await plugin.open()

    assert await plugin.write(events=['event']) == 1
    writer.write.assert_called_once()


@pytest.mark.asyncio
@patch(
    'eventum.plugins.output.plugins.tcp.plugin.asyncio.open_connection',
)
async def test_plugin_drops_connection_when_write_is_cancelled(
    mock_open_conn,
):
    """A write given up on takes its connection with it."""
    writer = _make_mock_writer()
    writer.drain = AsyncMock(side_effect=asyncio.CancelledError)
    mock_open_conn.return_value = (MagicMock(), writer)

    plugin = TcpOutputPlugin(config=_make_config(), params={'id': 1})
    await plugin.open()

    with pytest.raises(asyncio.CancelledError):
        await plugin.write(events=['event'])

    writer.transport.abort.assert_called_once()


@pytest.mark.asyncio
@patch('eventum.plugins.output.plugins.tcp.plugin._CLOSE_TIMEOUT', 0.05)
@patch(
    'eventum.plugins.output.plugins.tcp.plugin.asyncio.open_connection',
)
async def test_plugin_close_gives_up_on_undelivered_data(mock_open_conn):
    """Closing does not wait for a target that stopped reading."""
    async def never_closes() -> None:
        await asyncio.sleep(30)

    writer = _make_mock_writer(buffered=50000)
    writer.wait_closed = AsyncMock(side_effect=never_closes)
    mock_open_conn.return_value = (MagicMock(), writer)

    plugin = TcpOutputPlugin(config=_make_config(), params={'id': 1})
    await plugin.open()

    await asyncio.wait_for(plugin.close(), timeout=2)

    writer.transport.abort.assert_called_once()
