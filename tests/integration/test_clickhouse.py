"""Integration tests for the ClickHouse output plugin.

Validates data integrity, error recovery, edge cases, and
ClickHouse-specific behavior through end-to-end roundtrip tests.
"""

import asyncio
import json

import pytest

from tests.integration.conftest import CLICKHOUSE_HOST, CLICKHOUSE_PORT
from tests.integration.event_factory import EventFactory, EventSize
from tests.integration.verification import EventVerifier

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_plugin(*, database: str, table: str, **overrides):
    """Create an unopened ClickhouseOutputPlugin with the given config."""
    from eventum.plugins.output.plugins.clickhouse.config import (
        ClickhouseOutputPluginConfig,
    )
    from eventum.plugins.output.plugins.clickhouse.plugin import (
        ClickhouseOutputPlugin,
    )

    params = {
        'host': CLICKHOUSE_HOST,
        'port': CLICKHOUSE_PORT,
        'database': database,
        'table': table,
        **overrides,
    }
    config = ClickhouseOutputPluginConfig(**params)
    return ClickhouseOutputPlugin(config=config, params={'id': 1})


# ===================================================================
# Data Integrity
# ===================================================================


class TestDataIntegrity:
    """Verify that events survive the write-read roundtrip without
    corruption, duplication, or loss."""

    async def test_single_event_roundtrip(
        self,
        clickhouse_plugin,
        clickhouse_consumer,
        event_factory,
    ):
        """A single MEDIUM event must be perfectly preserved."""
        event = event_factory.create(EventSize.MEDIUM)

        await clickhouse_plugin.write([event.raw_json])
        await clickhouse_consumer.wait_for_count(1)

        consumed = await clickhouse_consumer.consume_all()

        result = EventVerifier(
            expected_batch_id=event_factory.batch_id,
            expected_count=1,
        ).verify(consumed)

        assert result.is_perfect, (
            f"Single event roundtrip failed:\n{result.summary()}"
        )

    async def test_batch_integrity(
        self,
        clickhouse_plugin,
        clickhouse_consumer,
        event_factory,
    ):
        """1000 MEDIUM events must all arrive with correct content hashes."""
        events = event_factory.create_batch(1000, EventSize.MEDIUM)

        await clickhouse_plugin.write([e.raw_json for e in events])
        await clickhouse_consumer.wait_for_count(1000, timeout=30.0)

        consumed = await clickhouse_consumer.consume_all()

        result = EventVerifier(
            expected_batch_id=event_factory.batch_id,
            expected_count=1000,
        ).verify(consumed)

        assert result.is_perfect, (
            f"Batch integrity check failed:\n{result.summary()}"
        )

    async def test_no_duplicates(
        self,
        clickhouse_plugin,
        clickhouse_consumer,
        event_factory,
    ):
        """Writing 500 events must yield exactly 500 unique sequence IDs
        with zero duplicates."""
        events = event_factory.create_batch(500, EventSize.MEDIUM)

        await clickhouse_plugin.write([e.raw_json for e in events])
        await clickhouse_consumer.wait_for_count(500, timeout=30.0)

        consumed = await clickhouse_consumer.consume_all()

        result = EventVerifier(
            expected_batch_id=event_factory.batch_id,
            expected_count=500,
        ).verify(consumed)

        assert result.duplicates == 0, (
            f"Duplicate events detected: {result.duplicate_sequence_ids}"
        )
        assert result.total_received == 500, (
            f"Expected exactly 500 events, got {result.total_received}"
        )

    async def test_order_preservation(
        self,
        clickhouse_plugin,
        clickhouse_consumer,
        event_factory,
    ):
        """Events written in a single batch must preserve insertion order
        within a MergeTree part."""
        events = event_factory.create_batch(100, EventSize.SMALL)

        await clickhouse_plugin.write([e.raw_json for e in events])

        await clickhouse_consumer.wait_for_count(100, timeout=30.0)

        consumed = await clickhouse_consumer.consume_all()

        result = EventVerifier(
            expected_batch_id=event_factory.batch_id,
            expected_count=100,
        ).verify(consumed, check_order=True)

        assert result.out_of_order_count == 0, (
            f"Events arrived out of order: "
            f"{result.out_of_order_count} out-of-order transitions"
        )
        assert result.is_perfect, (
            f"Order preservation check failed:\n{result.summary()}"
        )

    async def test_unicode_events(
        self,
        clickhouse_plugin,
        clickhouse_consumer,
        event_factory,
    ):
        """Events containing CJK, emoji, and RTL characters must
        roundtrip with matching content hashes."""
        unicode_payloads = [
            {"message": "\u4f60\u597d\u4e16\u754c CJK test"},
            {"message": "\U0001f389\U0001f680\u2728\U0001f30d emoji test"},
            {"message": "\u0645\u0631\u062d\u0628\u0627 \u0628\u0627\u0644\u0639\u0627\u0644\u0645 RTL test"},
            {"message": "\u4f60\u597d \U0001f389 \u0645\u0631\u062d\u0628\u0627 hello mixed"},
        ]

        events = [
            event_factory.create(EventSize.SMALL, extra_fields=payload)
            for payload in unicode_payloads
        ]

        await clickhouse_plugin.write([e.raw_json for e in events])
        await clickhouse_consumer.wait_for_count(len(events))

        consumed = await clickhouse_consumer.consume_all()

        result = EventVerifier(
            expected_batch_id=event_factory.batch_id,
            expected_count=len(events),
        ).verify(consumed)

        assert result.hash_mismatches == 0, (
            f"Unicode content was corrupted: "
            f"{result.hash_mismatches} hash mismatches"
        )
        assert result.is_perfect, (
            f"Unicode roundtrip failed:\n{result.summary()}"
        )

    async def test_json_special_chars(
        self,
        clickhouse_plugin,
        clickhouse_consumer,
        event_factory,
    ):
        """Events with newlines, tabs, and backslashes in string values
        must survive JSON serialization roundtrip."""
        special_payloads = [
            {"message": "line1\nline2\nline3"},
            {"message": "col1\tcol2\tcol3"},
            {"message": "path\\to\\file\\data"},
            {"message": 'quote"inside"string'},
            {"message": "mixed\nnew\tlines\\and\\slashes"},
        ]

        events = [
            event_factory.create(EventSize.SMALL, extra_fields=payload)
            for payload in special_payloads
        ]

        await clickhouse_plugin.write([e.raw_json for e in events])
        await clickhouse_consumer.wait_for_count(len(events))

        consumed = await clickhouse_consumer.consume_all()

        result = EventVerifier(
            expected_batch_id=event_factory.batch_id,
            expected_count=len(events),
        ).verify(consumed)

        assert result.is_perfect, (
            f"JSON special chars roundtrip failed:\n{result.summary()}"
        )

    async def test_large_event(
        self,
        clickhouse_plugin,
        clickhouse_consumer,
        event_factory,
    ):
        """A single HUGE event (~1MB) must roundtrip intact."""
        event = event_factory.create(EventSize.HUGE)

        await clickhouse_plugin.write([event.raw_json])
        await clickhouse_consumer.wait_for_count(1, timeout=30.0)

        consumed = await clickhouse_consumer.consume_all()

        result = EventVerifier(
            expected_batch_id=event_factory.batch_id,
            expected_count=1,
        ).verify(consumed)

        assert result.is_perfect, (
            f"Large event roundtrip failed:\n{result.summary()}"
        )

    async def test_mixed_event_sizes(
        self,
        clickhouse_plugin,
        clickhouse_consumer,
        event_factory,
    ):
        """A batch of 10 SMALL + 10 MEDIUM + 5 LARGE events must all
        arrive with correct hashes."""
        events = (
            event_factory.create_batch(10, EventSize.SMALL)
            + event_factory.create_batch(10, EventSize.MEDIUM)
            + event_factory.create_batch(5, EventSize.LARGE)
        )
        total = len(events)

        await clickhouse_plugin.write([e.raw_json for e in events])
        await clickhouse_consumer.wait_for_count(total, timeout=30.0)

        consumed = await clickhouse_consumer.consume_all()

        result = EventVerifier(
            expected_batch_id=event_factory.batch_id,
            expected_count=total,
        ).verify(consumed)

        assert result.is_perfect, (
            f"Mixed sizes roundtrip failed:\n{result.summary()}"
        )


# ===================================================================
# Error Recovery
# ===================================================================


class TestErrorRecovery:
    """Verify graceful error handling for misconfiguration and
    failure scenarios."""

    async def test_open_failure_wrong_host(self):
        """Opening a plugin with an unreachable host must raise
        PluginOpenError."""
        from eventum.plugins.output.exceptions import PluginOpenError

        plugin = _make_plugin(
            database='default',
            table='nonexistent',
            host='127.0.0.1',
            port=19999,
            connect_timeout=1,
        )

        with pytest.raises(PluginOpenError):
            await plugin.open()

    async def test_write_before_open(
        self,
        clickhouse_consumer,
        event_factory,
    ):
        """Writing to an unopened plugin must raise PluginWriteError."""
        from eventum.plugins.output.exceptions import PluginWriteError

        plugin = _make_plugin(
            database=clickhouse_consumer.database,
            table=clickhouse_consumer.table,
        )

        event = event_factory.create(EventSize.SMALL)

        with pytest.raises(PluginWriteError):
            await plugin.write([event.raw_json])

    async def test_write_to_nonexistent_table(
        self,
        clickhouse_consumer,
        event_factory,
    ):
        """Writing to a table that does not exist must raise
        PluginWriteError."""
        from eventum.plugins.output.exceptions import PluginWriteError

        plugin = _make_plugin(
            database=clickhouse_consumer.database,
            table='nonexistent_table_xyz_999',
        )
        await plugin.open()

        try:
            event = event_factory.create(EventSize.SMALL)
            with pytest.raises(PluginWriteError):
                await plugin.write([event.raw_json])
        finally:
            await plugin.close()

    async def test_large_batch_resilience(
        self,
        clickhouse_plugin,
        clickhouse_consumer,
        event_factory,
    ):
        """A 5000-event write must complete without partial failures."""
        events = event_factory.create_batch(5000, EventSize.SMALL)

        written = await clickhouse_plugin.write([e.raw_json for e in events])
        assert written == 5000, (
            f"Expected 5000 written rows, got {written}"
        )

        await clickhouse_consumer.wait_for_count(5000, timeout=30.0)

        consumed = await clickhouse_consumer.consume_all()

        result = EventVerifier(
            expected_batch_id=event_factory.batch_id,
            expected_count=5000,
        ).verify(consumed)

        assert result.is_perfect, (
            f"Large batch resilience check failed:\n{result.summary()}"
        )


# ===================================================================
# Edge Cases
# ===================================================================


class TestEdgeCases:
    """Verify correct behavior at boundary conditions and unusual
    usage patterns."""

    async def test_empty_event_list(
        self,
        clickhouse_plugin,
        clickhouse_consumer,
    ):
        """Writing an empty list must return 0 and leave the table
        unchanged."""
        written = await clickhouse_plugin.write([])
        assert written == 0, f"Expected 0 written for empty list, got {written}"

        count = await clickhouse_consumer.count()
        assert count == 0, (
            f"Table should be empty after writing empty list, got {count} rows"
        )

    async def test_rapid_open_close_cycles(
        self,
        clickhouse_consumer,
        event_factory,
    ):
        """20 rapid open/write/close cycles on fresh plugins must
        deliver all events."""
        cycles = 20

        for _ in range(cycles):
            plugin = _make_plugin(
                database=clickhouse_consumer.database,
                table=clickhouse_consumer.table,
            )
            await plugin.open()
            event = event_factory.create(EventSize.SMALL)
            await plugin.write([event.raw_json])
            await plugin.close()

        await clickhouse_consumer.wait_for_count(cycles, timeout=30.0)

        consumed = await clickhouse_consumer.consume_all()

        result = EventVerifier(
            expected_batch_id=event_factory.batch_id,
            expected_count=cycles,
        ).verify(consumed)

        assert result.is_perfect, (
            f"Rapid open/close cycles failed:\n{result.summary()}"
        )

    async def test_double_open_idempotent(
        self,
        clickhouse_consumer,
        event_factory,
    ):
        """Calling open() twice must not cause errors; writes must
        still succeed."""
        plugin = _make_plugin(
            database=clickhouse_consumer.database,
            table=clickhouse_consumer.table,
        )
        await plugin.open()
        await plugin.open()  # second open — should be idempotent

        try:
            event = event_factory.create(EventSize.SMALL)
            await plugin.write([event.raw_json])
            await clickhouse_consumer.wait_for_count(1)

            consumed = await clickhouse_consumer.consume_all()

            result = EventVerifier(
                expected_batch_id=event_factory.batch_id,
                expected_count=1,
            ).verify(consumed)

            assert result.is_perfect, (
                f"Double open idempotency failed:\n{result.summary()}"
            )
        finally:
            await plugin.close()

    async def test_double_close_safe(
        self,
        clickhouse_plugin,
    ):
        """Calling close() twice must not raise an exception."""
        await clickhouse_plugin.close()
        # Second close — must be safe (the fixture also calls close
        # on teardown, so this verifies triple-close safety as well).
        await clickhouse_plugin.close()

    async def test_maximum_batch_size(
        self,
        clickhouse_plugin,
        clickhouse_consumer,
        event_factory,
    ):
        """10000 events in a single write must all be persisted."""
        events = event_factory.create_batch(10000, EventSize.SMALL)

        await clickhouse_plugin.write([e.raw_json for e in events])
        await clickhouse_consumer.wait_for_count(10000, timeout=60.0)

        count = await clickhouse_consumer.count()
        assert count == 10000, (
            f"Expected 10000 rows, got {count}"
        )

    async def test_concurrent_writes(
        self,
        clickhouse_plugin,
        clickhouse_consumer,
        event_factory,
    ):
        """10 concurrent writes of 100 events each must collectively
        deliver all 1000 events."""
        batches = [
            event_factory.create_batch(100, EventSize.SMALL)
            for _ in range(10)
        ]

        await asyncio.gather(
            *(
                clickhouse_plugin.write([e.raw_json for e in batch])
                for batch in batches
            ),
        )

        await clickhouse_consumer.wait_for_count(1000, timeout=30.0)

        consumed = await clickhouse_consumer.consume_all()

        result = EventVerifier(
            expected_batch_id=event_factory.batch_id,
            expected_count=1000,
        ).verify(consumed)

        assert result.is_perfect, (
            f"Concurrent writes failed:\n{result.summary()}"
        )


# ===================================================================
# ClickHouse-Specific
# ===================================================================


class TestClickhouseSpecific:
    """Verify ClickHouse-specific storage semantics and plugin
    configuration options."""

    async def test_raw_insert_format(
        self,
        clickhouse_plugin,
        clickhouse_consumer,
        event_factory,
    ):
        """Events must be stored as valid JSON in the ``event`` column
        and be parseable back into dicts."""
        events = event_factory.create_batch(5, EventSize.MEDIUM)

        await clickhouse_plugin.write([e.raw_json for e in events])
        await clickhouse_consumer.wait_for_count(5)

        consumed = await clickhouse_consumer.consume_all()
        assert len(consumed) == 5, (
            f"Expected 5 stored rows, got {len(consumed)}"
        )

        for i, raw in enumerate(consumed):
            parsed = json.loads(raw)
            assert isinstance(parsed, dict), (
                f"Row {i} is not a JSON object: {type(parsed)}"
            )
            assert '_test' in parsed, (
                f"Row {i} missing _test metadata field"
            )

    async def test_table_isolation(
        self,
        clickhouse_dsn,
        event_factory,
    ):
        """Events written to different tables must not leak across
        table boundaries."""
        from tests.integration.backends.clickhouse import ClickHouseConsumer

        host, port = clickhouse_dsn

        consumer_a = ClickHouseConsumer(host=host, port=port)
        consumer_b = ClickHouseConsumer(host=host, port=port)

        await consumer_a.setup()
        await consumer_b.setup()

        try:
            plugin_a = _make_plugin(
                database=consumer_a.database,
                table=consumer_a.table,
            )
            plugin_b = _make_plugin(
                database=consumer_b.database,
                table=consumer_b.table,
            )

            await plugin_a.open()
            await plugin_b.open()

            try:
                factory_a = EventFactory()
                factory_b = EventFactory()

                events_a = factory_a.create_batch(50, EventSize.SMALL)
                events_b = factory_b.create_batch(30, EventSize.SMALL)

                await plugin_a.write([e.raw_json for e in events_a])
                await plugin_b.write([e.raw_json for e in events_b])

                await consumer_a.wait_for_count(50)
                await consumer_b.wait_for_count(30)

                consumed_a = await consumer_a.consume_all()
                consumed_b = await consumer_b.consume_all()

                assert len(consumed_a) == 50, (
                    f"Table A: expected 50 rows, got {len(consumed_a)}"
                )
                assert len(consumed_b) == 30, (
                    f"Table B: expected 30 rows, got {len(consumed_b)}"
                )

                # Verify no cross-contamination by batch_id
                result_a = EventVerifier(
                    expected_batch_id=factory_a.batch_id,
                    expected_count=50,
                ).verify(consumed_a)

                result_b = EventVerifier(
                    expected_batch_id=factory_b.batch_id,
                    expected_count=30,
                ).verify(consumed_b)

                assert result_a.is_perfect, (
                    f"Table A contaminated:\n{result_a.summary()}"
                )
                assert result_b.is_perfect, (
                    f"Table B contaminated:\n{result_b.summary()}"
                )
            finally:
                await plugin_a.close()
                await plugin_b.close()
        finally:
            await consumer_a.teardown()
            await consumer_b.teardown()

    async def test_multiple_sequential_writes(
        self,
        clickhouse_plugin,
        clickhouse_consumer,
        event_factory,
    ):
        """Three separate writes of 100 events each must yield a total
        of 300 rows."""
        for _ in range(3):
            batch = event_factory.create_batch(100, EventSize.SMALL)
            await clickhouse_plugin.write([e.raw_json for e in batch])

        await clickhouse_consumer.wait_for_count(300, timeout=30.0)

        consumed = await clickhouse_consumer.consume_all()

        result = EventVerifier(
            expected_batch_id=event_factory.batch_id,
            expected_count=300,
        ).verify(consumed)

        assert result.is_perfect, (
            f"Multiple sequential writes failed:\n{result.summary()}"
        )

    async def test_single_row_insert(
        self,
        clickhouse_plugin,
        clickhouse_consumer,
        event_factory,
    ):
        """Writing exactly 1 event must produce exactly 1 row."""
        event = event_factory.create(EventSize.SMALL)

        written = await clickhouse_plugin.write([event.raw_json])
        assert written == 1, f"Expected 1 written row, got {written}"

        await clickhouse_consumer.wait_for_count(1)
        count = await clickhouse_consumer.count()
        assert count == 1, f"Expected 1 row in table, got {count}"

    async def test_event_content_preserved(
        self,
        clickhouse_plugin,
        clickhouse_consumer,
        event_factory,
    ):
        """A written event read back from ClickHouse must contain the
        expected ECS fields: @timestamp, agent, host, message, _test."""
        event = event_factory.create(EventSize.MEDIUM)

        await clickhouse_plugin.write([event.raw_json])
        await clickhouse_consumer.wait_for_count(1)

        consumed = await clickhouse_consumer.consume_all()
        assert len(consumed) == 1, (
            f"Expected 1 consumed event, got {len(consumed)}"
        )

        parsed = json.loads(consumed[0])

        required_fields = ['@timestamp', 'agent', 'host', 'message', '_test']
        for field in required_fields:
            assert field in parsed, (
                f"ECS field '{field}' missing from stored event"
            )

        assert isinstance(parsed['agent'], dict), (
            "Field 'agent' should be a nested object"
        )
        assert isinstance(parsed['host'], dict), (
            "Field 'host' should be a nested object"
        )
        assert isinstance(parsed['_test'], dict), (
            "Field '_test' should be a nested object"
        )

    async def test_custom_separator(
        self,
        clickhouse_consumer,
        event_factory,
    ):
        """A plugin configured with a custom separator must still
        deliver events correctly."""
        plugin = _make_plugin(
            database=clickhouse_consumer.database,
            table=clickhouse_consumer.table,
            separator='\n',
        )
        await plugin.open()

        try:
            events = event_factory.create_batch(10, EventSize.SMALL)
            await plugin.write([e.raw_json for e in events])
            await clickhouse_consumer.wait_for_count(10)

            consumed = await clickhouse_consumer.consume_all()

            result = EventVerifier(
                expected_batch_id=event_factory.batch_id,
                expected_count=10,
            ).verify(consumed)

            assert result.is_perfect, (
                f"Custom separator test failed:\n{result.summary()}"
            )
        finally:
            await plugin.close()

    async def test_large_event_field_integrity(
        self,
        clickhouse_plugin,
        clickhouse_consumer,
        event_factory,
    ):
        """LARGE events read back from ClickHouse must have their full
        message field intact (no truncation)."""
        events = event_factory.create_batch(3, EventSize.LARGE)

        await clickhouse_plugin.write([e.raw_json for e in events])
        await clickhouse_consumer.wait_for_count(3, timeout=30.0)

        consumed = await clickhouse_consumer.consume_all()
        assert len(consumed) == 3, (
            f"Expected 3 consumed events, got {len(consumed)}"
        )

        for i, raw in enumerate(consumed):
            parsed = json.loads(raw)
            message = parsed.get('message', '')

            # LARGE events target ~50KB messages; verify substantial
            # content survived (at least 40KB to allow for overhead).
            assert len(message) >= 40_000, (
                f"Event {i}: message field truncated — "
                f"expected >= 40000 chars, got {len(message)}"
            )
