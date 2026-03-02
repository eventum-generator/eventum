"""Integration tests for the Kafka output plugin.

Validates data integrity, error recovery, edge cases, and Kafka-specific
behavior through end-to-end roundtrip testing against a real Kafka broker.
"""

import asyncio
import json

import pytest
from aiokafka import AIOKafkaConsumer as AIOConsumer

from tests.integration.conftest import KAFKA_BOOTSTRAP
from tests.integration.event_factory import EventFactory, EventSize
from tests.integration.verification import EventVerifier

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _write_and_verify(
    plugin,
    kafka_consumer,
    events,
    event_factory,
    *,
    check_order: bool = False,
    timeout: float = 15,
):
    """Write events through the plugin and verify roundtrip integrity.

    Returns the VerificationResult for additional assertions by the caller.
    """
    raw = [e.raw_json for e in events]
    written = await plugin.write(raw)
    assert written == len(events), (
        f"Expected {len(events)} written, got {written}"
    )

    await kafka_consumer.wait_for_count(len(events), timeout=timeout)
    consumed = await kafka_consumer.consume_all()

    verifier = EventVerifier(
        expected_batch_id=event_factory.batch_id,
        expected_count=len(events),
    )
    result = verifier.verify(consumed, check_order=check_order)
    return result


# =========================================================================
# Data Integrity
# =========================================================================


class TestDataIntegrity:
    """Verify that events survive the Kafka roundtrip without corruption."""

    async def test_single_event_roundtrip(
        self,
        kafka_plugin,
        kafka_consumer,
        event_factory,
    ):
        """A single MEDIUM event should survive the roundtrip intact."""
        events = [event_factory.create(EventSize.MEDIUM)]

        result = await _write_and_verify(
            kafka_plugin, kafka_consumer, events, event_factory,
        )
        assert result.is_perfect, (
            f"Single event roundtrip failed:\n{result.summary()}"
        )

    async def test_batch_integrity(
        self,
        kafka_plugin,
        kafka_consumer,
        event_factory,
    ):
        """1000 MEDIUM events should all arrive with correct hashes."""
        events = event_factory.create_batch(1000, EventSize.MEDIUM)

        result = await _write_and_verify(
            kafka_plugin, kafka_consumer, events, event_factory,
            timeout=30,
        )
        assert result.is_perfect, (
            f"Batch integrity check failed:\n{result.summary()}"
        )

    async def test_no_duplicates(
        self,
        kafka_plugin,
        kafka_consumer,
        event_factory,
    ):
        """500 events should produce exactly 500 unique sequence_ids."""
        events = event_factory.create_batch(500, EventSize.MEDIUM)

        result = await _write_and_verify(
            kafka_plugin, kafka_consumer, events, event_factory,
        )
        assert result.duplicates == 0, (
            f"Found {result.duplicates} duplicate events: "
            f"duplicate_sequence_ids={result.duplicate_sequence_ids}"
        )
        assert result.total_received == 500, (
            f"Expected 500 unique events, received {result.total_received}"
        )

    async def test_order_preservation(
        self,
        kafka_plugin,
        kafka_consumer,
        event_factory,
    ):
        """100 events should arrive in order (single partition guarantee)."""
        events = event_factory.create_batch(100, EventSize.MEDIUM)

        result = await _write_and_verify(
            kafka_plugin, kafka_consumer, events, event_factory,
            check_order=True,
        )
        assert result.out_of_order_count == 0, (
            f"Order violated: {result.out_of_order_count} out-of-order "
            f"transitions detected"
        )

    async def test_unicode_events(
        self,
        kafka_plugin,
        kafka_consumer,
        event_factory,
    ):
        """Events with CJK, emoji, and RTL characters should roundtrip."""
        unicode_payloads = [
            {"unicode_cjk": "\u4f60\u597d\u4e16\u754c"},
            {"unicode_emoji": "\U0001f389\U0001f680"},
            {"unicode_rtl": "\u0645\u0631\u062d\u0628\u0627"},
        ]

        events = [
            event_factory.create(
                EventSize.SMALL,
                extra_fields=payload,
            )
            for payload in unicode_payloads
        ]

        result = await _write_and_verify(
            kafka_plugin, kafka_consumer, events, event_factory,
        )
        assert result.is_perfect, (
            f"Unicode roundtrip failed:\n{result.summary()}"
        )

        # Also verify the raw content survived (parse JSON first since
        # json.dumps uses \uXXXX escapes by default for non-ASCII)
        consumed = await kafka_consumer.consume_all()
        consumed_parsed = [json.loads(raw) for raw in consumed]
        consumed_text = json.dumps(consumed_parsed, ensure_ascii=False)
        assert "\u4f60\u597d\u4e16\u754c" in consumed_text, (
            "CJK characters not found in consumed events"
        )
        assert "\U0001f389" in consumed_text, (
            "Emoji characters not found in consumed events"
        )
        assert "\u0645\u0631\u062d\u0628\u0627" in consumed_text, (
            "RTL characters not found in consumed events"
        )

    async def test_json_special_chars(
        self,
        kafka_plugin,
        kafka_consumer,
        event_factory,
    ):
        """Events with newlines, tabs, and backslashes in values should roundtrip."""
        special_fields = {
            "special_newline": "line1\nline2\nline3",
            "special_tab": "col1\tcol2\tcol3",
            "special_backslash": "path\\to\\file",
            "special_quotes": 'he said "hello"',
        }

        events = [
            event_factory.create(
                EventSize.SMALL,
                extra_fields=special_fields,
            ),
        ]

        result = await _write_and_verify(
            kafka_plugin, kafka_consumer, events, event_factory,
        )
        assert result.is_perfect, (
            f"Special chars roundtrip failed:\n{result.summary()}"
        )

    async def test_large_event(
        self,
        kafka_plugin,
        kafka_consumer,
        event_factory,
    ):
        """A single HUGE event (~1MB) should survive the roundtrip."""
        events = [event_factory.create(EventSize.HUGE)]

        result = await _write_and_verify(
            kafka_plugin, kafka_consumer, events, event_factory,
            timeout=20,
        )
        assert result.is_perfect, (
            f"Large event roundtrip failed:\n{result.summary()}"
        )

    async def test_mixed_event_sizes(
        self,
        kafka_plugin,
        kafka_consumer,
        event_factory,
    ):
        """A batch of mixed SMALL/MEDIUM/LARGE events should all arrive intact."""
        events = (
            event_factory.create_batch(10, EventSize.SMALL)
            + event_factory.create_batch(10, EventSize.MEDIUM)
            + event_factory.create_batch(5, EventSize.LARGE)
        )

        result = await _write_and_verify(
            kafka_plugin, kafka_consumer, events, event_factory,
            timeout=20,
        )
        assert result.is_perfect, (
            f"Mixed sizes roundtrip failed:\n{result.summary()}"
        )


# =========================================================================
# Error Recovery
# =========================================================================


class TestErrorRecovery:
    """Verify graceful handling of failures and edge conditions."""

    async def test_open_failure_wrong_bootstrap(self, kafka_consumer):
        """Opening with an unreachable bootstrap server should raise PluginOpenError."""
        from eventum.plugins.output.exceptions import PluginOpenError
        from eventum.plugins.output.plugins.kafka.config import (
            KafkaOutputPluginConfig,
        )
        from eventum.plugins.output.plugins.kafka.plugin import (
            KafkaOutputPlugin,
        )

        config = KafkaOutputPluginConfig(
            bootstrap_servers=['nonexistent:9999'],
            topic=kafka_consumer.topic,
            request_timeout_ms=5000,
        )
        plugin = KafkaOutputPlugin(config=config, params={'id': 1})

        with pytest.raises(PluginOpenError):
            await asyncio.wait_for(plugin.open(), timeout=30)

    async def test_write_before_open(self, kafka_consumer):
        """Writing to an unopened plugin should raise PluginWriteError."""
        from eventum.plugins.output.exceptions import PluginWriteError
        from eventum.plugins.output.plugins.kafka.config import (
            KafkaOutputPluginConfig,
        )
        from eventum.plugins.output.plugins.kafka.plugin import (
            KafkaOutputPlugin,
        )

        config = KafkaOutputPluginConfig(
            bootstrap_servers=[KAFKA_BOOTSTRAP],
            topic=kafka_consumer.topic,
        )
        plugin = KafkaOutputPlugin(config=config, params={'id': 1})

        factory = EventFactory()
        event = factory.create(EventSize.SMALL)

        with pytest.raises(PluginWriteError):
            await plugin.write([event.raw_json])

    async def test_producer_delivery_confirmation(
        self,
        kafka_plugin,
        kafka_consumer,
        event_factory,
    ):
        """Events written with default acks=1 should all be confirmed delivered."""
        events = event_factory.create_batch(100, EventSize.MEDIUM)
        raw = [e.raw_json for e in events]

        written = await kafka_plugin.write(raw)
        assert written == 100, (
            f"Expected 100 delivery confirmations, got {written}"
        )

        await kafka_consumer.wait_for_count(100, timeout=15)
        consumed = await kafka_consumer.consume_all()
        assert len(consumed) == 100, (
            f"Expected 100 consumed events, got {len(consumed)}"
        )

    async def test_large_batch_delivery(
        self,
        kafka_consumer,
        event_factory,
    ):
        """5000 events in a single write should all be delivered."""
        from eventum.plugins.output.plugins.kafka.config import (
            KafkaOutputPluginConfig,
        )
        from eventum.plugins.output.plugins.kafka.plugin import (
            KafkaOutputPlugin,
        )

        config = KafkaOutputPluginConfig(
            bootstrap_servers=[KAFKA_BOOTSTRAP],
            topic=kafka_consumer.topic,
            linger_ms=50,
            max_batch_size=262144,
        )
        plugin = KafkaOutputPlugin(config=config, params={'id': 1})
        await plugin.open()

        try:
            events = event_factory.create_batch(5000, EventSize.SMALL)

            result = await _write_and_verify(
                plugin, kafka_consumer, events, event_factory,
                timeout=60,
            )
            assert result.is_perfect, (
                f"Large batch delivery failed:\n{result.summary()}"
            )
        finally:
            await plugin.close()


# =========================================================================
# Edge Cases
# =========================================================================


class TestEdgeCases:
    """Verify correct behavior at boundary conditions."""

    async def test_empty_event_list(self, kafka_plugin):
        """Writing an empty list should return 0 without error."""
        written = await kafka_plugin.write([])
        assert written == 0, (
            f"Expected 0 for empty write, got {written}"
        )

    async def test_rapid_open_close_cycles(
        self,
        kafka_consumer,
        event_factory,
    ):
        """10 open/write/close cycles should each deliver events correctly."""
        from eventum.plugins.output.plugins.kafka.config import (
            KafkaOutputPluginConfig,
        )
        from eventum.plugins.output.plugins.kafka.plugin import (
            KafkaOutputPlugin,
        )

        config = KafkaOutputPluginConfig(
            bootstrap_servers=[KAFKA_BOOTSTRAP],
            topic=kafka_consumer.topic,
        )

        total_events = 0

        for _ in range(10):
            plugin = KafkaOutputPlugin(config=config, params={'id': 1})
            await plugin.open()

            events = event_factory.create_batch(10, EventSize.SMALL)
            raw = [e.raw_json for e in events]
            written = await plugin.write(raw)
            assert written == 10, (
                f"Expected 10 written per cycle, got {written}"
            )
            total_events += 10

            await plugin.close()

        await kafka_consumer.wait_for_count(total_events, timeout=30)
        consumed = await kafka_consumer.consume_all()
        assert len(consumed) == total_events, (
            f"Expected {total_events} total events after 10 cycles, "
            f"got {len(consumed)}"
        )

    async def test_double_open_idempotent(
        self,
        kafka_consumer,
        event_factory,
    ):
        """Opening a plugin twice should be idempotent and still work."""
        from eventum.plugins.output.plugins.kafka.config import (
            KafkaOutputPluginConfig,
        )
        from eventum.plugins.output.plugins.kafka.plugin import (
            KafkaOutputPlugin,
        )

        config = KafkaOutputPluginConfig(
            bootstrap_servers=[KAFKA_BOOTSTRAP],
            topic=kafka_consumer.topic,
        )
        plugin = KafkaOutputPlugin(config=config, params={'id': 1})

        await plugin.open()
        await plugin.open()  # second open should be idempotent

        events = event_factory.create_batch(10, EventSize.SMALL)
        raw = [e.raw_json for e in events]
        written = await plugin.write(raw)
        assert written == 10, (
            f"Expected 10 written after double open, got {written}"
        )

        await kafka_consumer.wait_for_count(10, timeout=15)
        consumed = await kafka_consumer.consume_all()
        assert len(consumed) == 10, (
            f"Expected 10 events after double open, got {len(consumed)}"
        )

        await plugin.close()

    async def test_double_close_safe(self, kafka_consumer):
        """Closing a plugin twice should not raise an exception."""
        from eventum.plugins.output.plugins.kafka.config import (
            KafkaOutputPluginConfig,
        )
        from eventum.plugins.output.plugins.kafka.plugin import (
            KafkaOutputPlugin,
        )

        config = KafkaOutputPluginConfig(
            bootstrap_servers=[KAFKA_BOOTSTRAP],
            topic=kafka_consumer.topic,
        )
        plugin = KafkaOutputPlugin(config=config, params={'id': 1})

        await plugin.open()
        await plugin.close()
        await plugin.close()  # second close should be safe

    async def test_maximum_batch_size(
        self,
        kafka_consumer,
        event_factory,
    ):
        """10000 SMALL events in a single write should all arrive."""
        from eventum.plugins.output.plugins.kafka.config import (
            KafkaOutputPluginConfig,
        )
        from eventum.plugins.output.plugins.kafka.plugin import (
            KafkaOutputPlugin,
        )

        config = KafkaOutputPluginConfig(
            bootstrap_servers=[KAFKA_BOOTSTRAP],
            topic=kafka_consumer.topic,
            linger_ms=50,
            max_batch_size=262144,
        )
        plugin = KafkaOutputPlugin(config=config, params={'id': 1})
        await plugin.open()

        try:
            events = event_factory.create_batch(10_000, EventSize.SMALL)

            result = await _write_and_verify(
                plugin, kafka_consumer, events, event_factory,
                timeout=90,
            )
            assert result.is_perfect, (
                f"Maximum batch delivery failed:\n{result.summary()}"
            )
        finally:
            await plugin.close()

    async def test_concurrent_writes(
        self,
        kafka_plugin,
        kafka_consumer,
        event_factory,
    ):
        """10 concurrent writes of 100 events should deliver all 1000."""
        batches = [
            event_factory.create_batch(100, EventSize.SMALL)
            for _ in range(10)
        ]

        write_tasks = [
            kafka_plugin.write([e.raw_json for e in batch])
            for batch in batches
        ]
        results = await asyncio.gather(*write_tasks)
        total_written = sum(results)
        assert total_written == 1000, (
            f"Expected 1000 total written, got {total_written}"
        )

        await kafka_consumer.wait_for_count(1000, timeout=30)
        consumed = await kafka_consumer.consume_all()

        all_events = [e for batch in batches for e in batch]
        verifier = EventVerifier(
            expected_batch_id=event_factory.batch_id,
            expected_count=1000,
        )
        result = verifier.verify(consumed, check_order=False)
        assert result.is_perfect, (
            f"Concurrent writes verification failed:\n{result.summary()}"
        )


# =========================================================================
# Kafka-Specific
# =========================================================================


class TestKafkaSpecific:
    """Verify Kafka-specific configuration and behavior."""

    async def test_message_key(
        self,
        kafka_consumer,
        event_factory,
    ):
        """Events produced with a message key should carry that key."""
        from eventum.plugins.output.plugins.kafka.config import (
            KafkaOutputPluginConfig,
        )
        from eventum.plugins.output.plugins.kafka.plugin import (
            KafkaOutputPlugin,
        )

        config = KafkaOutputPluginConfig(
            bootstrap_servers=[KAFKA_BOOTSTRAP],
            topic=kafka_consumer.topic,
            key='test-key',
        )
        plugin = KafkaOutputPlugin(config=config, params={'id': 1})
        await plugin.open()

        events = event_factory.create_batch(5, EventSize.SMALL)
        raw = [e.raw_json for e in events]
        await plugin.write(raw)
        await plugin.close()

        await kafka_consumer.wait_for_count(5, timeout=15)

        # Read records directly to inspect message keys
        consumer = AIOConsumer(
            kafka_consumer.topic,
            bootstrap_servers=KAFKA_BOOTSTRAP,
            auto_offset_reset='earliest',
            group_id=None,
        )
        await consumer.start()

        try:
            records = await consumer.getmany(timeout_ms=10_000)
            all_records = [
                record
                for tp_records in records.values()
                for record in tp_records
            ]
        finally:
            await consumer.stop()

        assert len(all_records) == 5, (
            f"Expected 5 records, got {len(all_records)}"
        )
        for record in all_records:
            assert record.key is not None, "Message key should not be None"
            assert record.key.decode('utf-8') == 'test-key', (
                f"Expected key 'test-key', got '{record.key.decode('utf-8')}'"
            )

    async def test_topic_isolation(
        self,
        kafka_bootstrap,
        event_factory,
    ):
        """Two plugins targeting different topics should not cross-contaminate."""
        from tests.integration.backends.kafka import KafkaConsumer

        from eventum.plugins.output.plugins.kafka.config import (
            KafkaOutputPluginConfig,
        )
        from eventum.plugins.output.plugins.kafka.plugin import (
            KafkaOutputPlugin,
        )

        consumer_a = KafkaConsumer(bootstrap_servers=kafka_bootstrap)
        consumer_b = KafkaConsumer(bootstrap_servers=kafka_bootstrap)
        await consumer_a.setup()
        await consumer_b.setup()

        try:
            config_a = KafkaOutputPluginConfig(
                bootstrap_servers=[KAFKA_BOOTSTRAP],
                topic=consumer_a.topic,
            )
            config_b = KafkaOutputPluginConfig(
                bootstrap_servers=[KAFKA_BOOTSTRAP],
                topic=consumer_b.topic,
            )

            plugin_a = KafkaOutputPlugin(config=config_a, params={'id': 1})
            plugin_b = KafkaOutputPlugin(config=config_b, params={'id': 2})

            await plugin_a.open()
            await plugin_b.open()

            factory_a = EventFactory()
            factory_b = EventFactory()

            events_a = factory_a.create_batch(50, EventSize.SMALL)
            events_b = factory_b.create_batch(30, EventSize.SMALL)

            await plugin_a.write([e.raw_json for e in events_a])
            await plugin_b.write([e.raw_json for e in events_b])

            await plugin_a.close()
            await plugin_b.close()

            await consumer_a.wait_for_count(50, timeout=15)
            await consumer_b.wait_for_count(30, timeout=15)

            consumed_a = await consumer_a.consume_all()
            consumed_b = await consumer_b.consume_all()

            assert len(consumed_a) == 50, (
                f"Topic A: expected 50 events, got {len(consumed_a)}"
            )
            assert len(consumed_b) == 30, (
                f"Topic B: expected 30 events, got {len(consumed_b)}"
            )

            # Verify no cross-contamination by checking batch_ids
            verifier_a = EventVerifier(
                expected_batch_id=factory_a.batch_id,
                expected_count=50,
            )
            verifier_b = EventVerifier(
                expected_batch_id=factory_b.batch_id,
                expected_count=30,
            )

            result_a = verifier_a.verify(consumed_a)
            result_b = verifier_b.verify(consumed_b)

            assert result_a.is_perfect, (
                f"Topic A contaminated:\n{result_a.summary()}"
            )
            assert result_b.is_perfect, (
                f"Topic B contaminated:\n{result_b.summary()}"
            )
        finally:
            await consumer_a.teardown()
            await consumer_b.teardown()

    async def test_multiple_sequential_writes(
        self,
        kafka_plugin,
        kafka_consumer,
        event_factory,
    ):
        """3 separate writes of 100 events should total 300."""
        all_events = []

        for _ in range(3):
            batch = event_factory.create_batch(100, EventSize.SMALL)
            all_events.extend(batch)
            raw = [e.raw_json for e in batch]
            written = await kafka_plugin.write(raw)
            assert written == 100, (
                f"Expected 100 per write, got {written}"
            )

        await kafka_consumer.wait_for_count(300, timeout=30)
        consumed = await kafka_consumer.consume_all()

        verifier = EventVerifier(
            expected_batch_id=event_factory.batch_id,
            expected_count=300,
        )
        result = verifier.verify(consumed)
        assert result.is_perfect, (
            f"Sequential writes verification failed:\n{result.summary()}"
        )

    async def test_compression_gzip(
        self,
        kafka_consumer,
        event_factory,
    ):
        """Events written with gzip compression should arrive intact."""
        from eventum.plugins.output.plugins.kafka.config import (
            KafkaOutputPluginConfig,
        )
        from eventum.plugins.output.plugins.kafka.plugin import (
            KafkaOutputPlugin,
        )

        config = KafkaOutputPluginConfig(
            bootstrap_servers=[KAFKA_BOOTSTRAP],
            topic=kafka_consumer.topic,
            compression_type='gzip',
        )
        plugin = KafkaOutputPlugin(config=config, params={'id': 1})
        await plugin.open()

        events = event_factory.create_batch(100, EventSize.MEDIUM)
        raw = [e.raw_json for e in events]
        written = await plugin.write(raw)
        assert written == 100, (
            f"Expected 100 written with gzip, got {written}"
        )
        await plugin.close()

        await kafka_consumer.wait_for_count(100, timeout=15)
        consumed = await kafka_consumer.consume_all()

        verifier = EventVerifier(
            expected_batch_id=event_factory.batch_id,
            expected_count=100,
        )
        result = verifier.verify(consumed)
        assert result.is_perfect, (
            f"Gzip compression roundtrip failed:\n{result.summary()}"
        )

    async def test_events_as_utf8(
        self,
        kafka_plugin,
        kafka_consumer,
        event_factory,
    ):
        """Events written with utf-8 encoding should decode correctly."""
        events = event_factory.create_batch(10, EventSize.MEDIUM)
        raw = [e.raw_json for e in events]

        written = await kafka_plugin.write(raw)
        assert written == 10, (
            f"Expected 10 written, got {written}"
        )

        await kafka_consumer.wait_for_count(10, timeout=15)
        consumed = await kafka_consumer.consume_all()

        assert len(consumed) == 10, (
            f"Expected 10 consumed, got {len(consumed)}"
        )

        # Verify each consumed event is valid JSON (proper UTF-8 decoding)
        for i, raw_event in enumerate(consumed):
            try:
                parsed = json.loads(raw_event)
            except json.JSONDecodeError as exc:
                pytest.fail(
                    f"Event {i} is not valid JSON after UTF-8 decode: {exc}"
                )
            assert isinstance(parsed, dict), (
                f"Event {i} parsed as {type(parsed).__name__}, expected dict"
            )

    async def test_acks_all(
        self,
        kafka_consumer,
        event_factory,
    ):
        """Events written with acks=-1 (all replicas) should be delivered."""
        from eventum.plugins.output.plugins.kafka.config import (
            KafkaOutputPluginConfig,
        )
        from eventum.plugins.output.plugins.kafka.plugin import (
            KafkaOutputPlugin,
        )

        config = KafkaOutputPluginConfig(
            bootstrap_servers=[KAFKA_BOOTSTRAP],
            topic=kafka_consumer.topic,
            acks=-1,
        )
        plugin = KafkaOutputPlugin(config=config, params={'id': 1})
        await plugin.open()

        events = event_factory.create_batch(50, EventSize.SMALL)
        raw = [e.raw_json for e in events]
        written = await plugin.write(raw)
        assert written == 50, (
            f"Expected 50 written with acks=all, got {written}"
        )
        await plugin.close()

        await kafka_consumer.wait_for_count(50, timeout=15)
        consumed = await kafka_consumer.consume_all()

        verifier = EventVerifier(
            expected_batch_id=event_factory.batch_id,
            expected_count=50,
        )
        result = verifier.verify(consumed)
        assert result.is_perfect, (
            f"acks=all delivery verification failed:\n{result.summary()}"
        )

    async def test_event_content_preserved(
        self,
        kafka_plugin,
        kafka_consumer,
        event_factory,
    ):
        """A single event's ECS fields should be preserved after roundtrip."""
        events = [event_factory.create(EventSize.MEDIUM)]
        raw = [events[0].raw_json]

        await kafka_plugin.write(raw)
        await kafka_consumer.wait_for_count(1, timeout=15)
        consumed = await kafka_consumer.consume_all()

        assert len(consumed) == 1, (
            f"Expected 1 consumed event, got {len(consumed)}"
        )

        parsed = json.loads(consumed[0])

        # Verify core ECS fields exist
        assert "@timestamp" in parsed, (
            "ECS field '@timestamp' missing from consumed event"
        )
        assert "agent" in parsed, (
            "ECS field 'agent' missing from consumed event"
        )
        assert isinstance(parsed["agent"], dict), (
            "ECS field 'agent' should be a dict"
        )
        assert "host" in parsed, (
            "ECS field 'host' missing from consumed event"
        )
        assert isinstance(parsed["host"], dict), (
            "ECS field 'host' should be a dict"
        )
        assert "message" in parsed, (
            "ECS field 'message' missing from consumed event"
        )
        assert "_test" in parsed, (
            "Test metadata field '_test' missing from consumed event"
        )

        # Verify test metadata roundtrip
        test_meta = parsed["_test"]
        assert test_meta["batch_id"] == event_factory.batch_id, (
            f"batch_id mismatch: expected {event_factory.batch_id}, "
            f"got {test_meta['batch_id']}"
        )
        assert test_meta["sequence_id"] == events[0].sequence_id, (
            f"sequence_id mismatch: expected {events[0].sequence_id}, "
            f"got {test_meta['sequence_id']}"
        )
        assert test_meta["content_hash"] == events[0].content_hash, (
            f"content_hash mismatch: expected {events[0].content_hash}, "
            f"got {test_meta['content_hash']}"
        )
