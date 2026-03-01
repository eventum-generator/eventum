"""Integration tests for the TCP output plugin.

End-to-end tests verifying data integrity, error recovery, edge cases,
and TCP-specific behavior using an in-process TCP server consumer.
"""

import asyncio
import json

import pytest
import pytest_asyncio

from tests.integration.event_factory import EventFactory, EventSize
from tests.integration.verification import EventVerifier

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _write_and_collect(plugin, consumer, events, *, expected=None):
    """Write events through the plugin and return consumed messages.

    Parameters
    ----------
    plugin:
        An opened ``TcpOutputPlugin`` instance.
    consumer:
        A ``TcpConsumer`` instance receiving events.
    events:
        List of ``VerifiableEvent`` objects to send.
    expected:
        Expected count to wait for. Defaults to ``len(events)``.

    Returns
    -------
    list[str]
        Raw consumed messages from the TCP consumer.
    """
    raw = [e.raw_json for e in events]
    await plugin.write(raw)

    count = expected if expected is not None else len(events)
    await consumer.wait_for_count(count, timeout=15.0)
    await asyncio.sleep(0.5)

    return await consumer.consume_all()


# ===================================================================
# Data Integrity (8 tests)
# ===================================================================


class TestDataIntegrity:
    """Verify that events survive the TCP roundtrip without corruption."""

    async def test_single_event_roundtrip(
        self, tcp_plugin, tcp_consumer, event_factory
    ):
        """A single MEDIUM event must arrive intact with matching hash."""
        events = [event_factory.create(EventSize.MEDIUM)]

        consumed = await _write_and_collect(tcp_plugin, tcp_consumer, events)

        verifier = EventVerifier(event_factory.batch_id, expected_count=1)
        result = verifier.verify(consumed)

        assert result.is_perfect, (
            f"Single event roundtrip failed:\n{result.summary()}"
        )

    async def test_batch_integrity(
        self, tcp_plugin, tcp_consumer, event_factory
    ):
        """1000 MEDIUM events must all arrive with correct content hashes."""
        events = event_factory.create_batch(1000, EventSize.MEDIUM)

        consumed = await _write_and_collect(tcp_plugin, tcp_consumer, events)

        verifier = EventVerifier(event_factory.batch_id, expected_count=1000)
        result = verifier.verify(consumed)

        assert result.is_perfect, (
            f"Batch integrity check failed:\n{result.summary()}"
        )

    async def test_no_duplicates(
        self, tcp_plugin, tcp_consumer, event_factory
    ):
        """500 events must produce exactly 500 unique sequence IDs."""
        events = event_factory.create_batch(500, EventSize.MEDIUM)

        consumed = await _write_and_collect(tcp_plugin, tcp_consumer, events)

        sequence_ids = []
        for raw in consumed:
            doc = json.loads(raw)
            test_meta = doc.get("_test")
            if test_meta and test_meta.get("batch_id") == event_factory.batch_id:
                sequence_ids.append(test_meta["sequence_id"])

        assert len(sequence_ids) == 500, (
            f"Expected 500 events, got {len(sequence_ids)}"
        )
        assert len(set(sequence_ids)) == 500, (
            f"Expected 500 unique sequence IDs, "
            f"got {len(set(sequence_ids))} unique out of {len(sequence_ids)}"
        )

    async def test_order_preservation(
        self, tcp_plugin, tcp_consumer, event_factory
    ):
        """TCP stream guarantees order; sequence IDs must be in order."""
        events = event_factory.create_batch(100, EventSize.MEDIUM)

        consumed = await _write_and_collect(tcp_plugin, tcp_consumer, events)

        verifier = EventVerifier(event_factory.batch_id, expected_count=100)
        result = verifier.verify(consumed, check_order=True)

        assert result.is_perfect, (
            f"Order preservation check failed:\n{result.summary()}"
        )
        assert result.out_of_order_count == 0, (
            f"Expected zero out-of-order events, "
            f"got {result.out_of_order_count}"
        )

    async def test_unicode_events(
        self, tcp_plugin, tcp_consumer, event_factory
    ):
        """Events with CJK, emoji, and RTL characters must roundtrip intact."""
        unicode_payloads = [
            {"unicode_field": "CJK: \u4f60\u597d\u4e16\u754c"},
            {"unicode_field": "Emoji: \U0001f389\U0001f680"},
            {"unicode_field": "RTL: \u0645\u0631\u062d\u0628\u0627"},
        ]

        events = [
            event_factory.create(
                EventSize.SMALL, extra_fields=payload
            )
            for payload in unicode_payloads
        ]

        consumed = await _write_and_collect(tcp_plugin, tcp_consumer, events)

        verifier = EventVerifier(event_factory.batch_id, expected_count=3)
        result = verifier.verify(consumed)

        assert result.is_perfect, (
            f"Unicode roundtrip failed:\n{result.summary()}"
        )

        # Verify the actual unicode content survived
        for raw in consumed:
            doc = json.loads(raw)
            test_meta = doc.get("_test")
            if test_meta and test_meta.get("batch_id") == event_factory.batch_id:
                assert "unicode_field" in doc, (
                    "unicode_field missing from consumed event"
                )

    async def test_json_special_chars(
        self, tcp_plugin, tcp_consumer, event_factory
    ):
        """Events with newlines in JSON string values must not confuse the separator."""
        special_payloads = [
            {"log_line": "line1\nline2\nline3"},
            {"log_line": "tab\there\nand\nnewlines"},
            {"log_line": 'quotes: "hello" and \\backslash'},
        ]

        events = [
            event_factory.create(
                EventSize.SMALL, extra_fields=payload
            )
            for payload in special_payloads
        ]

        consumed = await _write_and_collect(tcp_plugin, tcp_consumer, events)

        verifier = EventVerifier(event_factory.batch_id, expected_count=3)
        result = verifier.verify(consumed)

        assert result.is_perfect, (
            f"JSON special chars roundtrip failed:\n{result.summary()}"
        )

    async def test_large_event(
        self, tcp_plugin, tcp_consumer, event_factory
    ):
        """A single LARGE event (~50KB) must roundtrip intact."""
        events = [event_factory.create(EventSize.LARGE)]

        consumed = await _write_and_collect(tcp_plugin, tcp_consumer, events)

        verifier = EventVerifier(event_factory.batch_id, expected_count=1)
        result = verifier.verify(consumed)

        assert result.is_perfect, (
            f"Large event roundtrip failed:\n{result.summary()}"
        )

    async def test_mixed_event_sizes(
        self, tcp_plugin, tcp_consumer, event_factory
    ):
        """A batch of mixed SMALL, MEDIUM, and LARGE events must all arrive."""
        events = (
            event_factory.create_batch(10, EventSize.SMALL)
            + event_factory.create_batch(10, EventSize.MEDIUM)
            + event_factory.create_batch(5, EventSize.LARGE)
        )

        consumed = await _write_and_collect(tcp_plugin, tcp_consumer, events)

        verifier = EventVerifier(event_factory.batch_id, expected_count=25)
        result = verifier.verify(consumed)

        assert result.is_perfect, (
            f"Mixed event sizes check failed:\n{result.summary()}"
        )


# ===================================================================
# Error Recovery (4 tests)
# ===================================================================


class TestErrorRecovery:
    """Verify correct behavior under failure conditions."""

    async def test_open_failure_wrong_host(self):
        """Connecting to an unreachable host must raise PluginOpenError."""
        from eventum.plugins.output.exceptions import PluginOpenError
        from eventum.plugins.output.plugins.tcp.config import (
            TcpOutputPluginConfig,
        )
        from eventum.plugins.output.plugins.tcp.plugin import TcpOutputPlugin

        config = TcpOutputPluginConfig(
            host='192.0.2.1',
            port=1,
            connect_timeout=2,
        )
        plugin = TcpOutputPlugin(config=config, params={'id': 1})

        with pytest.raises(PluginOpenError):
            await plugin.open()

    async def test_write_before_open(self, event_factory):
        """Writing before open must raise PluginWriteError."""
        from eventum.plugins.output.exceptions import PluginWriteError
        from eventum.plugins.output.plugins.tcp.config import (
            TcpOutputPluginConfig,
        )
        from eventum.plugins.output.plugins.tcp.plugin import TcpOutputPlugin

        config = TcpOutputPluginConfig(
            host='127.0.0.1',
            port=9999,
        )
        plugin = TcpOutputPlugin(config=config, params={'id': 1})

        event = event_factory.create(EventSize.SMALL)

        with pytest.raises(PluginWriteError):
            await plugin.write([event.raw_json])

    async def test_reconnect_after_server_restart(self, event_factory):
        """A new plugin connecting to a restarted server must work."""
        from tests.integration.backends.tcp import TcpConsumer

        from eventum.plugins.output.plugins.tcp.config import (
            TcpOutputPluginConfig,
        )
        from eventum.plugins.output.plugins.tcp.plugin import TcpOutputPlugin

        # Phase 1: first server and plugin
        consumer1 = TcpConsumer(host='127.0.0.1', port=0)
        await consumer1.setup()

        config1 = TcpOutputPluginConfig(
            host=consumer1.host,
            port=consumer1.port,
        )
        plugin1 = TcpOutputPlugin(config=config1, params={'id': 1})
        await plugin1.open()

        events1 = event_factory.create_batch(50, EventSize.SMALL)
        await plugin1.write([e.raw_json for e in events1])
        await consumer1.wait_for_count(50, timeout=10.0)
        await asyncio.sleep(0.5)
        consumed1 = await consumer1.consume_all()

        assert len(consumed1) == 50, (
            f"Phase 1: expected 50 events, got {len(consumed1)}"
        )

        await plugin1.close()
        await consumer1.teardown()

        # Phase 2: new server and new plugin
        consumer2 = TcpConsumer(host='127.0.0.1', port=0)
        await consumer2.setup()

        config2 = TcpOutputPluginConfig(
            host=consumer2.host,
            port=consumer2.port,
        )
        plugin2 = TcpOutputPlugin(config=config2, params={'id': 2})
        await plugin2.open()

        events2 = event_factory.create_batch(50, EventSize.SMALL)
        await plugin2.write([e.raw_json for e in events2])
        await consumer2.wait_for_count(50, timeout=10.0)
        await asyncio.sleep(0.5)
        consumed2 = await consumer2.consume_all()

        assert len(consumed2) == 50, (
            f"Phase 2: expected 50 events, got {len(consumed2)}"
        )

        verifier = EventVerifier(event_factory.batch_id, expected_count=100)
        result = verifier.verify(consumed1 + consumed2)

        assert result.is_perfect, (
            f"Reconnect after server restart failed:\n{result.summary()}"
        )

        await plugin2.close()
        await consumer2.teardown()

    async def test_write_after_server_close(
        self, tcp_plugin, tcp_consumer, event_factory
    ):
        """Writing after the server closes must raise PluginWriteError."""
        from eventum.plugins.output.exceptions import PluginWriteError

        # Write initial events successfully
        events = event_factory.create_batch(10, EventSize.SMALL)
        await tcp_plugin.write([e.raw_json for e in events])
        await tcp_consumer.wait_for_count(10, timeout=10.0)
        await asyncio.sleep(0.5)

        # Tear down the server
        await tcp_consumer.teardown()

        # Allow the connection to detect the closure
        await asyncio.sleep(0.5)

        # Attempting to write should fail
        more_events = event_factory.create_batch(10, EventSize.SMALL)
        with pytest.raises((PluginWriteError, OSError)):
            # May need multiple writes for the broken pipe to surface
            for _ in range(5):
                await tcp_plugin.write([e.raw_json for e in more_events])
                await asyncio.sleep(0.1)


# ===================================================================
# Edge Cases (6 tests)
# ===================================================================


class TestEdgeCases:
    """Verify correct behavior for boundary and unusual conditions."""

    async def test_empty_event_list(self, tcp_plugin):
        """Writing an empty list must return 0 without errors."""
        written = await tcp_plugin.write([])

        assert written == 0, (
            f"Expected 0 written for empty list, got {written}"
        )

    async def test_rapid_open_close_cycles(self, tcp_consumer, event_factory):
        """20 create/open/write/close cycles must deliver all events."""
        from eventum.plugins.output.plugins.tcp.config import (
            TcpOutputPluginConfig,
        )
        from eventum.plugins.output.plugins.tcp.plugin import TcpOutputPlugin

        config = TcpOutputPluginConfig(
            host=tcp_consumer.host,
            port=tcp_consumer.port,
        )

        for _ in range(20):
            plugin = TcpOutputPlugin(config=config, params={'id': 1})
            await plugin.open()
            event = event_factory.create(EventSize.SMALL)
            await plugin.write([event.raw_json])
            await plugin.close()

        await tcp_consumer.wait_for_count(20, timeout=15.0)
        await asyncio.sleep(0.5)
        consumed = await tcp_consumer.consume_all()

        verifier = EventVerifier(event_factory.batch_id, expected_count=20)
        result = verifier.verify(consumed)

        assert result.is_perfect, (
            f"Rapid open/close cycles failed:\n{result.summary()}"
        )

    async def test_double_open_idempotent(
        self, tcp_consumer, event_factory
    ):
        """Opening a plugin twice must not break subsequent writes."""
        from eventum.plugins.output.plugins.tcp.config import (
            TcpOutputPluginConfig,
        )
        from eventum.plugins.output.plugins.tcp.plugin import TcpOutputPlugin

        config = TcpOutputPluginConfig(
            host=tcp_consumer.host,
            port=tcp_consumer.port,
        )
        plugin = TcpOutputPlugin(config=config, params={'id': 1})

        await plugin.open()
        await plugin.open()  # second open should be idempotent

        events = event_factory.create_batch(10, EventSize.SMALL)
        await plugin.write([e.raw_json for e in events])
        await tcp_consumer.wait_for_count(10, timeout=10.0)
        await asyncio.sleep(0.5)
        consumed = await tcp_consumer.consume_all()

        verifier = EventVerifier(event_factory.batch_id, expected_count=10)
        result = verifier.verify(consumed)

        assert result.is_perfect, (
            f"Double open test failed:\n{result.summary()}"
        )

        await plugin.close()

    async def test_double_close_safe(self, tcp_consumer):
        """Closing a plugin twice must not raise an exception."""
        from eventum.plugins.output.plugins.tcp.config import (
            TcpOutputPluginConfig,
        )
        from eventum.plugins.output.plugins.tcp.plugin import TcpOutputPlugin

        config = TcpOutputPluginConfig(
            host=tcp_consumer.host,
            port=tcp_consumer.port,
        )
        plugin = TcpOutputPlugin(config=config, params={'id': 1})

        await plugin.open()
        await plugin.close()
        await plugin.close()  # second close must not raise

    async def test_maximum_batch_size(
        self, tcp_plugin, tcp_consumer, event_factory
    ):
        """10000 SMALL events in a single write must all arrive."""
        events = event_factory.create_batch(10000, EventSize.SMALL)

        await tcp_plugin.write([e.raw_json for e in events])
        await tcp_consumer.wait_for_count(10000, timeout=30.0)
        await asyncio.sleep(0.5)
        consumed = await tcp_consumer.consume_all()

        verifier = EventVerifier(event_factory.batch_id, expected_count=10000)
        result = verifier.verify(consumed)

        assert result.is_perfect, (
            f"Maximum batch size check failed:\n{result.summary()}"
        )

    async def test_concurrent_writes(
        self, tcp_plugin, tcp_consumer, event_factory
    ):
        """10 concurrent writes of 100 events each must deliver all 1000."""
        batches = [
            event_factory.create_batch(100, EventSize.SMALL)
            for _ in range(10)
        ]

        async def write_batch(batch):
            await tcp_plugin.write([e.raw_json for e in batch])

        await asyncio.gather(*[write_batch(b) for b in batches])

        await tcp_consumer.wait_for_count(1000, timeout=15.0)
        await asyncio.sleep(0.5)
        consumed = await tcp_consumer.consume_all()

        verifier = EventVerifier(event_factory.batch_id, expected_count=1000)
        result = verifier.verify(consumed, check_order=False)

        assert result.is_perfect, (
            f"Concurrent writes check failed:\n{result.summary()}"
        )


# ===================================================================
# TCP-Specific (7 tests)
# ===================================================================


class TestTcpSpecific:
    """Verify TCP-specific configuration and behavior."""

    async def test_custom_separator(self, event_factory):
        """Events written with a custom separator must be split correctly."""
        from tests.integration.backends.tcp import TcpConsumer

        from eventum.plugins.output.plugins.tcp.config import (
            TcpOutputPluginConfig,
        )
        from eventum.plugins.output.plugins.tcp.plugin import TcpOutputPlugin

        consumer = TcpConsumer(
            host='127.0.0.1', port=0, separator='|||'
        )
        await consumer.setup()

        config = TcpOutputPluginConfig(
            host=consumer.host,
            port=consumer.port,
            separator='|||',
        )
        plugin = TcpOutputPlugin(config=config, params={'id': 1})
        await plugin.open()

        events = event_factory.create_batch(50, EventSize.SMALL)
        await plugin.write([e.raw_json for e in events])
        await consumer.wait_for_count(50, timeout=10.0)
        await asyncio.sleep(0.5)
        consumed = await consumer.consume_all()

        verifier = EventVerifier(event_factory.batch_id, expected_count=50)
        result = verifier.verify(consumed)

        assert result.is_perfect, (
            f"Custom separator test failed:\n{result.summary()}"
        )

        await plugin.close()
        await consumer.teardown()

    async def test_ascii_encoding(self, tcp_consumer, event_factory):
        """Events with ASCII-only content must survive ascii encoding."""
        from eventum.plugins.output.plugins.tcp.config import (
            TcpOutputPluginConfig,
        )
        from eventum.plugins.output.plugins.tcp.plugin import TcpOutputPlugin

        config = TcpOutputPluginConfig(
            host=tcp_consumer.host,
            port=tcp_consumer.port,
            encoding='ascii',
        )
        plugin = TcpOutputPlugin(config=config, params={'id': 1})
        await plugin.open()

        # EventFactory produces ASCII-safe events by default (ECS fields)
        events = event_factory.create_batch(20, EventSize.SMALL)
        await plugin.write([e.raw_json for e in events])
        await tcp_consumer.wait_for_count(20, timeout=10.0)
        await asyncio.sleep(0.5)
        consumed = await tcp_consumer.consume_all()

        verifier = EventVerifier(event_factory.batch_id, expected_count=20)
        result = verifier.verify(consumed)

        assert result.is_perfect, (
            f"ASCII encoding test failed:\n{result.summary()}"
        )

        await plugin.close()

    async def test_newline_separator_default(
        self, tcp_plugin, tcp_consumer, event_factory
    ):
        """Default separator is newline; events must be split correctly."""
        events = event_factory.create_batch(30, EventSize.SMALL)
        await tcp_plugin.write([e.raw_json for e in events])
        await tcp_consumer.wait_for_count(30, timeout=10.0)
        await asyncio.sleep(0.5)
        consumed = await tcp_consumer.consume_all()

        # Every consumed message should be valid JSON (no trailing newline)
        for i, raw in enumerate(consumed):
            try:
                json.loads(raw)
            except json.JSONDecodeError:
                pytest.fail(
                    f"Consumed message {i} is not valid JSON "
                    f"(separator split issue): {raw[:200]!r}"
                )

        verifier = EventVerifier(event_factory.batch_id, expected_count=30)
        result = verifier.verify(consumed)

        assert result.is_perfect, (
            f"Newline separator default test failed:\n{result.summary()}"
        )

    async def test_multiple_sequential_writes(
        self, tcp_plugin, tcp_consumer, event_factory
    ):
        """3 separate writes of 100 events must all arrive (total 300)."""
        all_events = []

        for _ in range(3):
            batch = event_factory.create_batch(100, EventSize.SMALL)
            all_events.extend(batch)
            await tcp_plugin.write([e.raw_json for e in batch])

        await tcp_consumer.wait_for_count(300, timeout=15.0)
        await asyncio.sleep(0.5)
        consumed = await tcp_consumer.consume_all()

        verifier = EventVerifier(event_factory.batch_id, expected_count=300)
        result = verifier.verify(consumed)

        assert result.is_perfect, (
            f"Multiple sequential writes failed:\n{result.summary()}"
        )

    async def test_event_content_preserved(
        self, tcp_plugin, tcp_consumer, event_factory
    ):
        """Consumed event must contain expected ECS fields."""
        event = event_factory.create(EventSize.MEDIUM)
        await tcp_plugin.write([event.raw_json])
        await tcp_consumer.wait_for_count(1, timeout=10.0)
        await asyncio.sleep(0.5)
        consumed = await tcp_consumer.consume_all()

        assert len(consumed) >= 1, "Expected at least 1 consumed event"

        doc = json.loads(consumed[0])

        assert "@timestamp" in doc, "Missing @timestamp field"
        assert "agent" in doc, "Missing agent field"
        assert "host" in doc, "Missing host field"
        assert "message" in doc, "Missing message field"
        assert "_test" in doc, "Missing _test metadata field"

        # Verify nested ECS structure
        assert "id" in doc["agent"], "Missing agent.id field"
        assert "type" in doc["agent"], "Missing agent.type field"
        assert "hostname" in doc["host"], "Missing host.hostname field"

        # Verify test metadata
        assert doc["_test"]["batch_id"] == event_factory.batch_id, (
            "batch_id mismatch in consumed event"
        )
        assert doc["_test"]["sequence_id"] == event.sequence_id, (
            "sequence_id mismatch in consumed event"
        )
        assert doc["_test"]["content_hash"] == event.content_hash, (
            "content_hash mismatch in consumed event"
        )

    async def test_stream_continuity(
        self, tcp_plugin, tcp_consumer, event_factory
    ):
        """Two writes on the same connection must deliver all 200 events."""
        batch1 = event_factory.create_batch(100, EventSize.SMALL)
        await tcp_plugin.write([e.raw_json for e in batch1])
        await tcp_consumer.wait_for_count(100, timeout=10.0)
        await asyncio.sleep(0.5)

        batch2 = event_factory.create_batch(100, EventSize.SMALL)
        await tcp_plugin.write([e.raw_json for e in batch2])
        await tcp_consumer.wait_for_count(200, timeout=10.0)
        await asyncio.sleep(0.5)

        consumed = await tcp_consumer.consume_all()

        verifier = EventVerifier(event_factory.batch_id, expected_count=200)
        result = verifier.verify(consumed)

        assert result.is_perfect, (
            f"Stream continuity check failed:\n{result.summary()}"
        )

    async def test_multiple_clients(self, tcp_consumer, event_factory):
        """Two plugins writing to the same consumer must deliver all events."""
        from eventum.plugins.output.plugins.tcp.config import (
            TcpOutputPluginConfig,
        )
        from eventum.plugins.output.plugins.tcp.plugin import TcpOutputPlugin

        config = TcpOutputPluginConfig(
            host=tcp_consumer.host,
            port=tcp_consumer.port,
        )

        plugin1 = TcpOutputPlugin(config=config, params={'id': 1})
        plugin2 = TcpOutputPlugin(config=config, params={'id': 2})

        await plugin1.open()
        await plugin2.open()

        batch1 = event_factory.create_batch(50, EventSize.SMALL)
        batch2 = event_factory.create_batch(50, EventSize.SMALL)

        await asyncio.gather(
            plugin1.write([e.raw_json for e in batch1]),
            plugin2.write([e.raw_json for e in batch2]),
        )

        await tcp_consumer.wait_for_count(100, timeout=15.0)
        await asyncio.sleep(0.5)
        consumed = await tcp_consumer.consume_all()

        verifier = EventVerifier(event_factory.batch_id, expected_count=100)
        result = verifier.verify(consumed, check_order=False)

        assert result.is_perfect, (
            f"Multiple clients test failed:\n{result.summary()}"
        )

        await plugin1.close()
        await plugin2.close()
