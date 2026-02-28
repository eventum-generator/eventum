"""Tests for kafka output plugin."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from eventum.plugins.exceptions import PluginConfigurationError
from eventum.plugins.output.exceptions import PluginOpenError
from eventum.plugins.output.plugins.kafka.config import (
    KafkaOutputPluginConfig,
)
from eventum.plugins.output.plugins.kafka.plugin import KafkaOutputPlugin

EVENT_1 = '{"type": "login", "user": "alice"}'
EVENT_2 = '{"type": "logout", "user": "bob"}'
EVENT_3 = '{"type": "click", "user": "carol"}'


def _make_config(**overrides) -> KafkaOutputPluginConfig:
    defaults = {
        'bootstrap_servers': ['localhost:9092'],
        'topic': 'events',
    }
    return KafkaOutputPluginConfig(**(defaults | overrides))


def _make_delivery_future(*, exception=None):
    """Create a future simulating Kafka delivery result."""
    future = asyncio.Future()
    if exception is not None:
        future.set_exception(exception)
    else:
        future.set_result(None)
    return future


def _make_producer(**overrides):
    """Create a mock AIOKafkaProducer with successful send."""
    producer = MagicMock()
    producer.start = AsyncMock()
    producer.stop = AsyncMock()
    producer.send = AsyncMock(
        side_effect=lambda *a, **kw: _make_delivery_future(),
    )
    for key, value in overrides.items():
        setattr(producer, key, value)
    return producer


@pytest.mark.asyncio
@patch(
    'eventum.plugins.output.plugins.kafka.plugin.AIOKafkaProducer',
)
async def test_plugin_write(mock_producer_cls):
    producer = _make_producer()
    mock_producer_cls.return_value = producer

    config = _make_config()
    plugin = KafkaOutputPlugin(config=config, params={'id': 1})

    await plugin.open()

    written = await plugin.write(events=[EVENT_1, EVENT_2])
    assert written == 2

    assert producer.send.call_count == 2

    await plugin.close()
    producer.stop.assert_awaited_once()


@pytest.mark.asyncio
@patch(
    'eventum.plugins.output.plugins.kafka.plugin.AIOKafkaProducer',
)
async def test_plugin_write_with_key(mock_producer_cls):
    producer = _make_producer()
    mock_producer_cls.return_value = producer

    config = _make_config(key='my-key')
    plugin = KafkaOutputPlugin(config=config, params={'id': 1})

    await plugin.open()
    await plugin.write(events=[EVENT_1])

    producer.send.assert_called_once_with(
        'events',
        value=EVENT_1.encode(),
        key=b'my-key',
    )

    await plugin.close()


@pytest.mark.asyncio
@patch(
    'eventum.plugins.output.plugins.kafka.plugin.AIOKafkaProducer',
)
async def test_plugin_write_send_failure(mock_producer_cls):
    """Test when send() itself fails (buffer rejection)."""
    call_count = 0

    def send_side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise Exception('Buffer full')
        return _make_delivery_future()

    producer = _make_producer(
        send=AsyncMock(side_effect=send_side_effect),
    )
    mock_producer_cls.return_value = producer

    config = _make_config()
    plugin = KafkaOutputPlugin(config=config, params={'id': 1})

    await plugin.open()

    written = await plugin.write(events=[EVENT_1, EVENT_2, EVENT_3])
    assert written == 2

    await plugin.close()


@pytest.mark.asyncio
@patch(
    'eventum.plugins.output.plugins.kafka.plugin.AIOKafkaProducer',
)
async def test_plugin_write_delivery_failure(mock_producer_cls):
    """Test when send() succeeds but broker delivery fails."""
    call_count = 0

    def send_side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            return _make_delivery_future(
                exception=Exception('Broker rejected'),
            )
        return _make_delivery_future()

    producer = _make_producer(
        send=AsyncMock(side_effect=send_side_effect),
    )
    mock_producer_cls.return_value = producer

    config = _make_config()
    plugin = KafkaOutputPlugin(config=config, params={'id': 1})

    await plugin.open()

    written = await plugin.write(events=[EVENT_1, EVENT_2, EVENT_3])
    assert written == 2

    await plugin.close()


@pytest.mark.asyncio
@patch(
    'eventum.plugins.output.plugins.kafka.plugin.AIOKafkaProducer',
)
async def test_plugin_open_failure(mock_producer_cls):
    producer = _make_producer(
        start=AsyncMock(side_effect=Exception('Connection refused')),
    )
    mock_producer_cls.return_value = producer

    config = _make_config()
    plugin = KafkaOutputPlugin(config=config, params={'id': 1})

    with pytest.raises(PluginOpenError):
        await plugin.open()


@pytest.mark.asyncio
@patch(
    'eventum.plugins.output.plugins.kafka.plugin.AIOKafkaProducer',
)
async def test_plugin_acks_minus_one_mapped_to_all(mock_producer_cls):
    producer = _make_producer()
    mock_producer_cls.return_value = producer

    config = _make_config(acks=-1)
    plugin = KafkaOutputPlugin(config=config, params={'id': 1})

    await plugin.open()

    call_kwargs = mock_producer_cls.call_args[1]
    assert call_kwargs['acks'] == 'all'

    await plugin.close()


@pytest.mark.asyncio
@patch(
    'eventum.plugins.output.plugins.kafka.plugin.AIOKafkaProducer',
)
async def test_plugin_acks_zero_and_one_unchanged(mock_producer_cls):
    producer = _make_producer()
    mock_producer_cls.return_value = producer

    for acks_value in (0, 1):
        config = _make_config(acks=acks_value)
        plugin = KafkaOutputPlugin(config=config, params={'id': 1})

        await plugin.open()

        call_kwargs = mock_producer_cls.call_args[1]
        assert call_kwargs['acks'] == acks_value

        await plugin.close()


def test_plugin_ssl_context_error():
    config = _make_config(
        security_protocol='SSL',
        ssl_cafile='/nonexistent/ca.pem',
    )
    with pytest.raises(PluginConfigurationError):
        KafkaOutputPlugin(config=config, params={'id': 1})
