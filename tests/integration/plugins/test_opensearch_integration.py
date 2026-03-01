"""Integration tests for the OpenSearch output plugin.

Covers data integrity, error recovery, edge cases, and OpenSearch-specific
behavior. All tests require a running OpenSearch instance and are marked
with ``@pytest.mark.integration``.
"""

import asyncio
import json
import uuid

import pytest
import pytest_asyncio

from tests.integration.conftest import OPENSEARCH_URL
from tests.integration.event_factory import EventFactory, EventSize
from tests.integration.verification import EventVerifier

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_plugin(index: str):
    """Create an unopened OpensearchOutputPlugin targeting *index*."""
    from eventum.plugins.output.plugins.opensearch.config import (
        OpensearchOutputPluginConfig,
    )
    from eventum.plugins.output.plugins.opensearch.plugin import (
        OpensearchOutputPlugin,
    )

    config = OpensearchOutputPluginConfig(
        hosts=[OPENSEARCH_URL],  # type: ignore
        username='admin',
        password='admin',
        index=index,
        verify=False,
    )
    return OpensearchOutputPlugin(config=config, params={'id': 1})


def _make_plugin_with_host(host: str, index: str):
    """Create an unopened plugin pointing at an arbitrary *host*."""
    from eventum.plugins.output.plugins.opensearch.config import (
        OpensearchOutputPluginConfig,
    )
    from eventum.plugins.output.plugins.opensearch.plugin import (
        OpensearchOutputPlugin,
    )

    config = OpensearchOutputPluginConfig(
        hosts=[host],  # type: ignore
        username='admin',
        password='admin',
        index=index,
        verify=False,
        connect_timeout=2,
        request_timeout=3,
    )
    return OpensearchOutputPlugin(config=config, params={'id': 1})


# =========================================================================
# Data Integrity
# =========================================================================


class TestDataIntegrity:
    """Verify that events survive the write/read roundtrip without corruption."""

    async def test_single_event_roundtrip(
        self,
        opensearch_plugin,
        opensearch_consumer,
        event_factory,
    ):
        """A single MEDIUM event must survive the full roundtrip."""
        event = event_factory.create(EventSize.MEDIUM)

        written = await opensearch_plugin.write([event.raw_json])
        assert written == 1, f'Expected 1 written, got {written}'

        await opensearch_consumer.wait_for_count(1)
        consumed = await opensearch_consumer.consume_all()

        verifier = EventVerifier(event_factory.batch_id, expected_count=1)
        result = verifier.verify(consumed, check_order=False)

        assert result.is_perfect, (
            f'Single-event roundtrip failed:\n{result.summary()}'
        )

    async def test_batch_integrity(
        self,
        opensearch_plugin,
        opensearch_consumer,
        event_factory,
    ):
        """All 1 000 events in a batch must have matching content hashes."""
        count = 1000
        events = event_factory.create_batch(count, EventSize.MEDIUM)

        written = await opensearch_plugin.write(
            [e.raw_json for e in events],
        )
        assert written == count, f'Expected {count} written, got {written}'

        await opensearch_consumer.wait_for_count(count)
        consumed = await opensearch_consumer.consume_all()

        verifier = EventVerifier(event_factory.batch_id, expected_count=count)
        result = verifier.verify(consumed, check_order=False)

        assert result.is_perfect, (
            f'Batch integrity check failed:\n{result.summary()}'
        )

    async def test_no_duplicates(
        self,
        opensearch_plugin,
        opensearch_consumer,
        event_factory,
    ):
        """Writing 500 events must produce exactly 500 unique documents."""
        count = 500
        events = event_factory.create_batch(count, EventSize.MEDIUM)

        await opensearch_plugin.write([e.raw_json for e in events])
        await opensearch_consumer.wait_for_count(count)
        consumed = await opensearch_consumer.consume_all()

        verifier = EventVerifier(event_factory.batch_id, expected_count=count)
        result = verifier.verify(consumed, check_order=False)

        assert result.duplicates == 0, (
            f'Found {result.duplicates} duplicate(s): '
            f'duplicate seq IDs = {result.duplicate_sequence_ids}'
        )
        assert result.total_received == count, (
            f'Expected {count} unique events, got {result.total_received}'
        )

    async def test_order_preservation(
        self,
        opensearch_plugin,
        opensearch_consumer,
        event_factory,
    ):
        """All 100 sequence IDs must be present (order is not guaranteed)."""
        count = 100
        events = event_factory.create_batch(count, EventSize.MEDIUM)

        await opensearch_plugin.write([e.raw_json for e in events])
        await opensearch_consumer.wait_for_count(count)
        consumed = await opensearch_consumer.consume_all()

        verifier = EventVerifier(event_factory.batch_id, expected_count=count)
        result = verifier.verify(consumed, check_order=False)

        assert len(result.missing_sequence_ids) == 0, (
            f'Missing sequence IDs: {result.missing_sequence_ids}'
        )

    async def test_unicode_events(
        self,
        opensearch_plugin,
        opensearch_consumer,
        event_factory,
    ):
        """Events with CJK, emoji, and RTL characters must roundtrip intact."""
        unicode_fields = {
            'cjk_text': '你好世界 — Chinese, Japanese, Korean test',
            'emoji_text': 'Party 🎉🚀 celebration with emojis',
            'rtl_text': 'مرحبا — Arabic right-to-left text',
            'mixed': '你好 🎉 مرحبا — all together',
        }

        events = [
            event_factory.create(
                EventSize.MEDIUM,
                extra_fields=unicode_fields,
            )
            for _ in range(5)
        ]

        await opensearch_plugin.write([e.raw_json for e in events])
        await opensearch_consumer.wait_for_count(5)
        consumed = await opensearch_consumer.consume_all()

        verifier = EventVerifier(event_factory.batch_id, expected_count=5)
        result = verifier.verify(consumed, check_order=False)

        assert result.hash_mismatches == 0, (
            f'Unicode content corrupted: {result.hash_mismatches} hash mismatch(es)'
        )
        assert result.is_perfect, (
            f'Unicode roundtrip failed:\n{result.summary()}'
        )

    async def test_json_special_chars(
        self,
        opensearch_plugin,
        opensearch_consumer,
        event_factory,
    ):
        """Events with newlines, tabs, and backslashes in string fields must roundtrip."""
        special_fields = {
            'with_newlines': 'line1\nline2\nline3',
            'with_tabs': 'col1\tcol2\tcol3',
            'with_backslashes': 'path\\to\\file\\name',
            'with_quotes': 'He said "hello" and she said \'hi\'',
            'with_mixed': 'start\n\ttab\n\\end',
        }

        event = event_factory.create(
            EventSize.MEDIUM,
            extra_fields=special_fields,
        )

        await opensearch_plugin.write([event.raw_json])
        await opensearch_consumer.wait_for_count(1)
        consumed = await opensearch_consumer.consume_all()

        verifier = EventVerifier(event_factory.batch_id, expected_count=1)
        result = verifier.verify(consumed, check_order=False)

        assert result.is_perfect, (
            f'JSON special chars roundtrip failed:\n{result.summary()}'
        )

    async def test_large_event(
        self,
        opensearch_plugin,
        opensearch_consumer,
        event_factory,
    ):
        """A single HUGE (~1 MB) event must survive the roundtrip."""
        event = event_factory.create(EventSize.HUGE)

        written = await opensearch_plugin.write([event.raw_json])
        assert written == 1, f'Expected 1 written, got {written}'

        await opensearch_consumer.wait_for_count(1, timeout=60.0)
        consumed = await opensearch_consumer.consume_all(timeout=30.0)

        verifier = EventVerifier(event_factory.batch_id, expected_count=1)
        result = verifier.verify(consumed, check_order=False)

        assert result.is_perfect, (
            f'Large event roundtrip failed:\n{result.summary()}'
        )

    async def test_mixed_event_sizes(
        self,
        opensearch_plugin,
        opensearch_consumer,
        event_factory,
    ):
        """A mixed batch of SMALL, MEDIUM, and LARGE events must all roundtrip."""
        small = event_factory.create_batch(10, EventSize.SMALL)
        medium = event_factory.create_batch(10, EventSize.MEDIUM)
        large = event_factory.create_batch(5, EventSize.LARGE)

        all_events = small + medium + large
        total = len(all_events)

        written = await opensearch_plugin.write(
            [e.raw_json for e in all_events],
        )
        assert written == total, f'Expected {total} written, got {written}'

        await opensearch_consumer.wait_for_count(total, timeout=60.0)
        consumed = await opensearch_consumer.consume_all()

        verifier = EventVerifier(event_factory.batch_id, expected_count=total)
        result = verifier.verify(consumed, check_order=False)

        assert result.is_perfect, (
            f'Mixed-size batch roundtrip failed:\n{result.summary()}'
        )


# =========================================================================
# Error Recovery
# =========================================================================


class TestErrorRecovery:
    """Verify graceful behavior under error conditions."""

    async def test_open_failure_wrong_host(self, opensearch_consumer):
        """Connecting to a non-existent host must fail on write."""
        plugin = _make_plugin_with_host(
            'http://localhost:19999',
            opensearch_consumer.index,
        )

        # open() creates the HTTP client but does not connect;
        # the actual connection failure surfaces on write.
        await plugin.open()

        from eventum.plugins.output.exceptions import PluginWriteError

        factory = EventFactory()
        event = factory.create(EventSize.SMALL)

        with pytest.raises(PluginWriteError):
            await plugin.write([event.raw_json])

        await plugin.close()

    async def test_write_before_open(self, opensearch_consumer):
        """Writing to an unopened plugin must raise PluginWriteError."""
        from eventum.plugins.output.exceptions import PluginWriteError

        plugin = _make_plugin(opensearch_consumer.index)
        factory = EventFactory()
        event = factory.create(EventSize.SMALL)

        with pytest.raises(PluginWriteError):
            await plugin.write([event.raw_json])

    async def test_single_vs_bulk_api(
        self,
        opensearch_plugin,
        opensearch_consumer,
        event_factory,
    ):
        """Writing 1 event (_doc) then 5 events (_bulk) must deliver all 6."""
        single = event_factory.create(EventSize.MEDIUM)
        batch = event_factory.create_batch(5, EventSize.MEDIUM)

        written_single = await opensearch_plugin.write([single.raw_json])
        assert written_single == 1

        written_bulk = await opensearch_plugin.write(
            [e.raw_json for e in batch],
        )
        assert written_bulk == 5

        total = 6
        await opensearch_consumer.wait_for_count(total)
        consumed = await opensearch_consumer.consume_all()

        verifier = EventVerifier(event_factory.batch_id, expected_count=total)
        result = verifier.verify(consumed, check_order=False)

        assert result.is_perfect, (
            f'Single+bulk API roundtrip failed:\n{result.summary()}'
        )

    async def test_bulk_with_partial_success(
        self,
        opensearch_plugin,
        opensearch_consumer,
        event_factory,
    ):
        """A large batch (5 000) must be fully indexed without partial failures."""
        count = 5000
        events = event_factory.create_batch(count, EventSize.SMALL)

        written = await opensearch_plugin.write(
            [e.raw_json for e in events],
        )
        assert written == count, f'Expected {count} written, got {written}'

        await opensearch_consumer.wait_for_count(count, timeout=60.0)
        actual = await opensearch_consumer.count()

        assert actual == count, (
            f'Expected {count} documents in index, found {actual}'
        )


# =========================================================================
# Edge Cases
# =========================================================================


class TestEdgeCases:
    """Verify correct behavior at boundary conditions."""

    async def test_empty_event_list(
        self,
        opensearch_plugin,
        opensearch_consumer,
    ):
        """write([]) must return 0 and not create any documents."""
        written = await opensearch_plugin.write([])
        assert written == 0, (
            f'Expected 0 written for empty list, got {written}'
        )

        count = await opensearch_consumer.count()
        assert count == 0, f'Expected 0 documents in index, found {count}'

    async def test_rapid_open_close_cycles(
        self,
        opensearch_consumer,
        event_factory,
    ):
        """20 open/write/close cycles on fresh plugins must all succeed."""
        total_written = 0

        for _ in range(20):
            plugin = _make_plugin(opensearch_consumer.index)
            await plugin.open()

            event = event_factory.create(EventSize.SMALL)
            written = await plugin.write([event.raw_json])
            total_written += written

            await plugin.close()

        await opensearch_consumer.wait_for_count(20, timeout=30.0)
        actual = await opensearch_consumer.count()

        assert actual == 20, (
            f'Expected 20 documents after 20 cycles, found {actual}'
        )
        assert total_written == 20, (
            f'Expected 20 total written, got {total_written}'
        )

    async def test_double_open_idempotent(
        self,
        opensearch_consumer,
        event_factory,
    ):
        """Calling open() twice must be a no-op and writing must still work."""
        plugin = _make_plugin(opensearch_consumer.index)
        await plugin.open()
        await plugin.open()  # second call — should be idempotent

        event = event_factory.create(EventSize.MEDIUM)
        written = await plugin.write([event.raw_json])
        assert written == 1

        await opensearch_consumer.wait_for_count(1)
        consumed = await opensearch_consumer.consume_all()

        verifier = EventVerifier(event_factory.batch_id, expected_count=1)
        result = verifier.verify(consumed, check_order=False)

        assert result.is_perfect, (
            f'Double-open roundtrip failed:\n{result.summary()}'
        )

        await plugin.close()

    async def test_double_close_safe(self, opensearch_consumer):
        """Calling close() twice must not raise."""
        plugin = _make_plugin(opensearch_consumer.index)
        await plugin.open()
        await plugin.close()
        await plugin.close()  # must not raise

    async def test_maximum_batch_size(
        self,
        opensearch_plugin,
        opensearch_consumer,
        event_factory,
    ):
        """A single write of 10 000 events must deliver all of them."""
        count = 10_000
        events = event_factory.create_batch(count, EventSize.SMALL)

        written = await opensearch_plugin.write(
            [e.raw_json for e in events],
        )
        assert written == count, f'Expected {count} written, got {written}'

        await opensearch_consumer.wait_for_count(count, timeout=120.0)
        consumed = await opensearch_consumer.consume_all(timeout=30.0)

        verifier = EventVerifier(event_factory.batch_id, expected_count=count)
        result = verifier.verify(consumed, check_order=False)

        assert result.is_perfect, (
            f'Max batch roundtrip failed:\n{result.summary()}'
        )

    async def test_concurrent_writes(
        self,
        opensearch_plugin,
        opensearch_consumer,
        event_factory,
    ):
        """10 concurrent writes of 100 events each must deliver all 1 000."""
        batches = [
            event_factory.create_batch(100, EventSize.SMALL) for _ in range(10)
        ]

        tasks = [
            opensearch_plugin.write([e.raw_json for e in batch])
            for batch in batches
        ]
        results = await asyncio.gather(*tasks)

        total_written = sum(results)
        assert total_written == 1000, (
            f'Expected 1000 total written, got {total_written}'
        )

        await opensearch_consumer.wait_for_count(1000, timeout=60.0)
        consumed = await opensearch_consumer.consume_all()

        verifier = EventVerifier(event_factory.batch_id, expected_count=1000)
        result = verifier.verify(consumed, check_order=False)

        assert result.is_perfect, (
            f'Concurrent writes roundtrip failed:\n{result.summary()}'
        )


# =========================================================================
# OpenSearch-Specific
# =========================================================================


class TestOpenSearchSpecific:
    """Tests targeting OpenSearch-specific API paths and behavior."""

    async def test_single_doc_api(
        self,
        opensearch_plugin,
        opensearch_consumer,
        event_factory,
    ):
        """Writing exactly 1 event exercises the _doc API path."""
        event = event_factory.create(EventSize.MEDIUM)

        written = await opensearch_plugin.write([event.raw_json])
        assert written == 1

        await opensearch_consumer.wait_for_count(1)
        consumed = await opensearch_consumer.consume_all()

        verifier = EventVerifier(event_factory.batch_id, expected_count=1)
        result = verifier.verify(consumed, check_order=False)

        assert result.is_perfect, (
            f'Single _doc API roundtrip failed:\n{result.summary()}'
        )

    async def test_bulk_api(
        self,
        opensearch_plugin,
        opensearch_consumer,
        event_factory,
    ):
        """Writing 50 events exercises the _bulk API path."""
        count = 50
        events = event_factory.create_batch(count, EventSize.MEDIUM)

        written = await opensearch_plugin.write(
            [e.raw_json for e in events],
        )
        assert written == count

        await opensearch_consumer.wait_for_count(count)
        consumed = await opensearch_consumer.consume_all()

        verifier = EventVerifier(event_factory.batch_id, expected_count=count)
        result = verifier.verify(consumed, check_order=False)

        assert result.is_perfect, (
            f'Bulk API roundtrip failed:\n{result.summary()}'
        )

    async def test_index_isolation(self, opensearch_url, event_factory):
        """Events written to one index must not appear in another."""
        from tests.integration.backends.opensearch import OpenSearchConsumer

        consumer_a = OpenSearchConsumer(base_url=opensearch_url)
        consumer_b = OpenSearchConsumer(base_url=opensearch_url)

        await consumer_a.setup()
        await consumer_b.setup()

        try:
            plugin_a = _make_plugin(consumer_a.index)
            plugin_b = _make_plugin(consumer_b.index)

            await plugin_a.open()
            await plugin_b.open()

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

            # Verify each index has exactly its own events
            verifier_a = EventVerifier(factory_a.batch_id, expected_count=50)
            result_a = verifier_a.verify(consumed_a, check_order=False)

            verifier_b = EventVerifier(factory_b.batch_id, expected_count=30)
            result_b = verifier_b.verify(consumed_b, check_order=False)

            assert result_a.is_perfect, (
                f'Index A isolation failed:\n{result_a.summary()}'
            )
            assert result_b.is_perfect, (
                f'Index B isolation failed:\n{result_b.summary()}'
            )

            # Cross-check: batch A events must not appear in index B
            cross_verifier = EventVerifier(
                factory_a.batch_id, expected_count=0
            )
            cross_result = cross_verifier.verify(consumed_b, check_order=False)
            assert cross_result.total_received == 0, (
                f'Index isolation breach: {cross_result.total_received} events '
                f'from batch A found in index B'
            )

            await plugin_a.close()
            await plugin_b.close()
        finally:
            await consumer_a.teardown()
            await consumer_b.teardown()

    async def test_large_batch_integrity(
        self,
        opensearch_plugin,
        opensearch_consumer,
        event_factory,
    ):
        """5 000 events must all pass hash verification."""
        count = 5000
        events = event_factory.create_batch(count, EventSize.SMALL)

        written = await opensearch_plugin.write(
            [e.raw_json for e in events],
        )
        assert written == count, f'Expected {count} written, got {written}'

        await opensearch_consumer.wait_for_count(count, timeout=60.0)
        consumed = await opensearch_consumer.consume_all(timeout=30.0)

        verifier = EventVerifier(event_factory.batch_id, expected_count=count)
        result = verifier.verify(consumed, check_order=False)

        assert result.is_perfect, (
            f'Large batch integrity failed:\n{result.summary()}'
        )

    async def test_events_searchable_immediately_after_refresh(
        self,
        opensearch_plugin,
        opensearch_consumer,
        event_factory,
    ):
        """After a manual _refresh(), events must be immediately searchable."""
        count = 10
        events = event_factory.create_batch(count, EventSize.MEDIUM)

        await opensearch_plugin.write([e.raw_json for e in events])

        # Force refresh instead of wait_for_count polling
        await opensearch_consumer._refresh()

        actual = await opensearch_consumer.count()
        assert actual == count, (
            f'Expected {count} documents after refresh, found {actual}'
        )

        consumed = await opensearch_consumer.consume_all()

        verifier = EventVerifier(event_factory.batch_id, expected_count=count)
        result = verifier.verify(consumed, check_order=False)

        assert result.is_perfect, (
            f'Post-refresh search failed:\n{result.summary()}'
        )

    async def test_multiple_sequential_writes(
        self,
        opensearch_plugin,
        opensearch_consumer,
        event_factory,
    ):
        """Three separate writes of 100 events must total 300 in the index."""
        per_batch = 100

        for _ in range(3):
            batch = event_factory.create_batch(per_batch, EventSize.SMALL)
            written = await opensearch_plugin.write(
                [e.raw_json for e in batch],
            )
            assert written == per_batch

        total = per_batch * 3
        await opensearch_consumer.wait_for_count(total)
        consumed = await opensearch_consumer.consume_all()

        verifier = EventVerifier(event_factory.batch_id, expected_count=total)
        result = verifier.verify(consumed, check_order=False)

        assert result.is_perfect, (
            f'Sequential writes roundtrip failed:\n{result.summary()}'
        )

    async def test_event_content_preserved(
        self,
        opensearch_plugin,
        opensearch_consumer,
        event_factory,
    ):
        """Core ECS fields must be present and intact in the indexed document."""
        event = event_factory.create(EventSize.MEDIUM)

        await opensearch_plugin.write([event.raw_json])
        await opensearch_consumer.wait_for_count(1)
        consumed = await opensearch_consumer.consume_all()

        assert len(consumed) == 1, f'Expected 1 document, got {len(consumed)}'

        doc = json.loads(consumed[0])

        # Verify core ECS fields exist
        assert '@timestamp' in doc, 'Missing @timestamp field'
        assert 'agent' in doc, 'Missing agent field'
        assert isinstance(doc['agent'], dict), 'agent must be an object'
        assert 'id' in doc['agent'], 'Missing agent.id field'

        assert 'ecs' in doc, 'Missing ecs field'
        assert 'version' in doc['ecs'], 'Missing ecs.version field'

        assert 'host' in doc, 'Missing host field'
        assert 'hostname' in doc['host'], 'Missing host.hostname field'

        assert 'message' in doc, 'Missing message field'
        assert len(doc['message']) > 0, 'message field must not be empty'

        assert '_test' in doc, 'Missing _test metadata field'
        assert doc['_test']['batch_id'] == event_factory.batch_id, (
            'batch_id mismatch in indexed document'
        )
        assert doc['_test']['sequence_id'] == event.sequence_id, (
            'sequence_id mismatch in indexed document'
        )
        assert doc['_test']['content_hash'] == event.content_hash, (
            'content_hash mismatch in indexed document'
        )
