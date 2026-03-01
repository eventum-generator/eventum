"""Longevity (soak) tests for output plugins.

Each test runs continuous writes for ``EVENTUM_LONGEVITY_DURATION`` seconds
(default 120, configurable via env) and asserts stability: no throughput
degradation, no memory leak, no file-descriptor leak, stable thread count.

All tests are marked ``@pytest.mark.longevity``.
"""

import asyncio
import os
import time

import pytest
import pytest_asyncio

from tests.integration.assertions import (
    assert_no_fd_leak,
    assert_no_memory_leak,
    assert_no_throughput_degradation,
    assert_threads_stable,
)
from tests.integration.conftest import (
    CLICKHOUSE_HOST,
    CLICKHOUSE_PORT,
    KAFKA_BOOTSTRAP,
    OPENSEARCH_URL,
)
from tests.integration.event_factory import EventFactory, EventSize
from tests.integration.verification import EventVerifier

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _print_longevity_report(backend: str, report) -> None:
    """Print a detailed longevity report to stdout."""
    print(f'\n{"=" * 60}')
    print(f'LONGEVITY REPORT: {backend}')
    print(f'Duration: {report.duration_seconds:.1f}s')
    print(f'Total events: {report.total_events}')
    print(
        f'EPS: mean={report.eps_mean:.0f} '
        f'p50={report.eps_p50:.0f} '
        f'p95={report.eps_p95:.0f}'
    )
    print(
        f'RSS: start={report.rss_start_bytes / 1024 / 1024:.1f}MB '
        f'end={report.rss_end_bytes / 1024 / 1024:.1f}MB '
        f'growth={report.rss_growth_bytes / 1024 / 1024:.1f}MB'
    )
    print(
        f'FDs: start={report.fd_start} '
        f'end={report.fd_end} '
        f'peak={report.fd_peak}'
    )
    print(
        f'Threads: start={report.thread_start} '
        f'end={report.thread_end} '
        f'peak={report.thread_peak}'
    )
    print(
        f'GC collections: '
        f'gen0={report.gc_collections[0]} '
        f'gen1={report.gc_collections[1]} '
        f'gen2={report.gc_collections[2]}'
    )
    if report.eps_slope is not None:
        slope_pct = (
            (report.eps_slope * 60.0 / report.eps_mean * 100.0)
            if report.eps_mean > 0
            else 0
        )
        print(
            f'EPS trend: slope={slope_pct:+.2f}%/min '
            f'R\u00b2={report.eps_r_squared:.4f}'
        )
    if report.rss_slope is not None:
        rss_slope_mb = report.rss_slope * 60.0 / (1024 * 1024)
        print(f'RSS trend: slope={rss_slope_mb:+.4f} MB/min')
    print(f'{"=" * 60}\n')


# =========================================================================
# OpenSearch
# =========================================================================


@pytest.mark.longevity
async def test_opensearch_sustained_throughput(
    longevity_duration,
    event_factory,
    metrics_collector,
):
    """Verify sustained throughput over time with no degradation."""
    from eventum.plugins.output.plugins.opensearch.config import (
        OpensearchOutputPluginConfig,
    )
    from eventum.plugins.output.plugins.opensearch.plugin import (
        OpensearchOutputPlugin,
    )
    from tests.integration.backends.opensearch import OpenSearchConsumer

    consumer = OpenSearchConsumer(base_url=OPENSEARCH_URL)
    await consumer.setup()

    config = OpensearchOutputPluginConfig(
        hosts=[OPENSEARCH_URL],  # type: ignore
        username='admin',
        password='admin',
        index=consumer.index,
        verify=False,
    )
    plugin = OpensearchOutputPlugin(config=config, params={'id': 1})
    await plugin.open()

    BATCH_SIZE = 100

    try:
        metrics_collector.start()
        start = time.monotonic()

        while time.monotonic() - start < longevity_duration:
            batch = event_factory.create_batch(BATCH_SIZE, EventSize.MEDIUM)
            written = await plugin.write([e.raw_json for e in batch])
            metrics_collector.record_events(written)

        report = metrics_collector.finalize()
        _print_longevity_report('opensearch', report)

        assert_no_throughput_degradation(report)
        assert_no_memory_leak(report)
        assert_no_fd_leak(report)
        assert_threads_stable(report)
    finally:
        await plugin.close()
        await consumer.teardown()


@pytest.mark.longevity
async def test_opensearch_data_integrity_over_time(
    longevity_duration,
    event_factory,
):
    """Verify data integrity is maintained throughout the run."""
    from eventum.plugins.output.plugins.opensearch.config import (
        OpensearchOutputPluginConfig,
    )
    from eventum.plugins.output.plugins.opensearch.plugin import (
        OpensearchOutputPlugin,
    )
    from tests.integration.backends.opensearch import OpenSearchConsumer

    consumer = OpenSearchConsumer(base_url=OPENSEARCH_URL)
    await consumer.setup()

    config = OpensearchOutputPluginConfig(
        hosts=[OPENSEARCH_URL],  # type: ignore
        username='admin',
        password='admin',
        index=consumer.index,
        verify=False,
    )
    plugin = OpensearchOutputPlugin(config=config, params={'id': 1})
    await plugin.open()

    BATCH_SIZE = 100
    VERIFY_INTERVAL = 30  # seconds
    total_written = 0

    try:
        start = time.monotonic()
        last_verify = start

        while time.monotonic() - start < longevity_duration:
            batch = event_factory.create_batch(BATCH_SIZE, EventSize.MEDIUM)
            written = await plugin.write([e.raw_json for e in batch])
            total_written += written

            # Periodic verification
            if (
                time.monotonic() - last_verify >= VERIFY_INTERVAL
                and total_written > 0
            ):
                actual_count = await consumer.wait_for_count(
                    total_written,
                    timeout=30,
                )
                assert actual_count >= total_written * 0.99, (
                    f'Data loss: expected ~{total_written}, got {actual_count}'
                )
                last_verify = time.monotonic()

        # Final full verification
        await consumer.wait_for_count(total_written, timeout=60)
        events = await consumer.consume_all()
        verifier = EventVerifier(event_factory.batch_id, total_written)
        result = verifier.verify(events)

        print(
            f'\nIntegrity: received={result.total_received}/{result.total_expected} '
            f'hash_mismatches={result.hash_mismatches} '
            f'duplicates={result.duplicates}'
        )

        assert result.hash_mismatches == 0, (
            f'Hash mismatches: {result.hash_mismatches}'
        )
        assert result.duplicates == 0, f'Duplicates found: {result.duplicates}'
        assert result.total_received >= total_written * 0.99, (
            f'Data loss: received {result.total_received}/{total_written}'
        )
    finally:
        await plugin.close()
        await consumer.teardown()


@pytest.mark.longevity
async def test_opensearch_no_connection_exhaustion(event_factory):
    """Verify no cumulative FD growth over many open/close cycles."""
    from eventum.plugins.output.plugins.opensearch.config import (
        OpensearchOutputPluginConfig,
    )
    from eventum.plugins.output.plugins.opensearch.plugin import (
        OpensearchOutputPlugin,
    )
    from tests.integration.backends.opensearch import OpenSearchConsumer

    CYCLES = 100
    EVENTS_PER_CYCLE = 10

    consumer = OpenSearchConsumer(base_url=OPENSEARCH_URL)
    await consumer.setup()

    try:
        fd_start = len(os.listdir(f'/proc/{os.getpid()}/fd'))

        for i in range(CYCLES):
            config = OpensearchOutputPluginConfig(
                hosts=[OPENSEARCH_URL],  # type: ignore
                username='admin',
                password='admin',
                index=consumer.index,
                verify=False,
            )
            plugin = OpensearchOutputPlugin(config=config, params={'id': 1})
            await plugin.open()

            batch = event_factory.create_batch(
                EVENTS_PER_CYCLE,
                EventSize.SMALL,
            )
            await plugin.write([e.raw_json for e in batch])

            await plugin.close()

        fd_end = len(os.listdir(f'/proc/{os.getpid()}/fd'))
        fd_growth = fd_end - fd_start

        print(
            f'\nFD growth after {CYCLES} cycles: {fd_growth} '
            f'(start={fd_start}, end={fd_end})'
        )

        assert fd_growth <= 20, (
            f'FD leak: grew by {fd_growth} after {CYCLES} open/close cycles'
        )

        # Verify all events arrived
        total_expected = CYCLES * EVENTS_PER_CYCLE
        actual = await consumer.wait_for_count(total_expected, timeout=30)
        assert actual >= total_expected * 0.99
    finally:
        await consumer.teardown()


# =========================================================================
# ClickHouse
# =========================================================================


@pytest.mark.longevity
async def test_clickhouse_sustained_throughput(
    longevity_duration,
    event_factory,
    metrics_collector,
):
    """Verify sustained throughput over time with no degradation."""
    from eventum.plugins.output.plugins.clickhouse.config import (
        ClickhouseOutputPluginConfig,
    )
    from eventum.plugins.output.plugins.clickhouse.plugin import (
        ClickhouseOutputPlugin,
    )
    from tests.integration.backends.clickhouse import ClickHouseConsumer

    consumer = ClickHouseConsumer(host=CLICKHOUSE_HOST, port=CLICKHOUSE_PORT)
    await consumer.setup()

    config = ClickhouseOutputPluginConfig(
        host=CLICKHOUSE_HOST,
        port=CLICKHOUSE_PORT,
        database=consumer.database,
        table=consumer.table,
    )
    plugin = ClickhouseOutputPlugin(config=config, params={'id': 1})
    await plugin.open()

    BATCH_SIZE = 100

    try:
        metrics_collector.start()
        start = time.monotonic()

        while time.monotonic() - start < longevity_duration:
            batch = event_factory.create_batch(BATCH_SIZE, EventSize.MEDIUM)
            written = await plugin.write([e.raw_json for e in batch])
            metrics_collector.record_events(written)

        report = metrics_collector.finalize()
        _print_longevity_report('clickhouse', report)

        assert_no_throughput_degradation(report)
        assert_no_memory_leak(report)
        assert_no_fd_leak(report)
        assert_threads_stable(report)
    finally:
        await plugin.close()
        await consumer.teardown()


@pytest.mark.longevity
async def test_clickhouse_data_integrity_over_time(
    longevity_duration,
    event_factory,
):
    """Verify data integrity is maintained throughout the run."""
    from eventum.plugins.output.plugins.clickhouse.config import (
        ClickhouseOutputPluginConfig,
    )
    from eventum.plugins.output.plugins.clickhouse.plugin import (
        ClickhouseOutputPlugin,
    )
    from tests.integration.backends.clickhouse import ClickHouseConsumer

    consumer = ClickHouseConsumer(host=CLICKHOUSE_HOST, port=CLICKHOUSE_PORT)
    await consumer.setup()

    config = ClickhouseOutputPluginConfig(
        host=CLICKHOUSE_HOST,
        port=CLICKHOUSE_PORT,
        database=consumer.database,
        table=consumer.table,
    )
    plugin = ClickhouseOutputPlugin(config=config, params={'id': 1})
    await plugin.open()

    BATCH_SIZE = 100
    VERIFY_INTERVAL = 30  # seconds
    total_written = 0

    try:
        start = time.monotonic()
        last_verify = start

        while time.monotonic() - start < longevity_duration:
            batch = event_factory.create_batch(BATCH_SIZE, EventSize.MEDIUM)
            written = await plugin.write([e.raw_json for e in batch])
            total_written += written

            # Periodic verification
            if (
                time.monotonic() - last_verify >= VERIFY_INTERVAL
                and total_written > 0
            ):
                actual_count = await consumer.wait_for_count(
                    total_written,
                    timeout=30,
                )
                assert actual_count >= total_written * 0.99, (
                    f'Data loss: expected ~{total_written}, got {actual_count}'
                )
                last_verify = time.monotonic()

        # Final full verification
        await consumer.wait_for_count(total_written, timeout=60)
        events = await consumer.consume_all()
        verifier = EventVerifier(event_factory.batch_id, total_written)
        result = verifier.verify(events)

        print(
            f'\nIntegrity: received={result.total_received}/{result.total_expected} '
            f'hash_mismatches={result.hash_mismatches} '
            f'duplicates={result.duplicates}'
        )

        assert result.hash_mismatches == 0, (
            f'Hash mismatches: {result.hash_mismatches}'
        )
        assert result.duplicates == 0, f'Duplicates found: {result.duplicates}'
        assert result.total_received >= total_written * 0.99, (
            f'Data loss: received {result.total_received}/{total_written}'
        )
    finally:
        await plugin.close()
        await consumer.teardown()


@pytest.mark.longevity
async def test_clickhouse_no_connection_exhaustion(event_factory):
    """Verify no cumulative FD growth over many open/close cycles."""
    from eventum.plugins.output.plugins.clickhouse.config import (
        ClickhouseOutputPluginConfig,
    )
    from eventum.plugins.output.plugins.clickhouse.plugin import (
        ClickhouseOutputPlugin,
    )
    from tests.integration.backends.clickhouse import ClickHouseConsumer

    CYCLES = 100
    EVENTS_PER_CYCLE = 10

    consumer = ClickHouseConsumer(host=CLICKHOUSE_HOST, port=CLICKHOUSE_PORT)
    await consumer.setup()

    try:
        fd_start = len(os.listdir(f'/proc/{os.getpid()}/fd'))

        for i in range(CYCLES):
            config = ClickhouseOutputPluginConfig(
                host=CLICKHOUSE_HOST,
                port=CLICKHOUSE_PORT,
                database=consumer.database,
                table=consumer.table,
            )
            plugin = ClickhouseOutputPlugin(config=config, params={'id': 1})
            await plugin.open()

            batch = event_factory.create_batch(
                EVENTS_PER_CYCLE,
                EventSize.SMALL,
            )
            await plugin.write([e.raw_json for e in batch])

            await plugin.close()

        fd_end = len(os.listdir(f'/proc/{os.getpid()}/fd'))
        fd_growth = fd_end - fd_start

        print(
            f'\nFD growth after {CYCLES} cycles: {fd_growth} '
            f'(start={fd_start}, end={fd_end})'
        )

        assert fd_growth <= 20, (
            f'FD leak: grew by {fd_growth} after {CYCLES} open/close cycles'
        )

        # Verify all events arrived
        total_expected = CYCLES * EVENTS_PER_CYCLE
        actual = await consumer.wait_for_count(total_expected, timeout=30)
        assert actual >= total_expected * 0.99
    finally:
        await consumer.teardown()


# =========================================================================
# Kafka
# =========================================================================


@pytest.mark.longevity
async def test_kafka_sustained_throughput(
    longevity_duration,
    event_factory,
    metrics_collector,
):
    """Verify sustained throughput over time with no degradation."""
    from eventum.plugins.output.plugins.kafka.config import (
        KafkaOutputPluginConfig,
    )
    from eventum.plugins.output.plugins.kafka.plugin import KafkaOutputPlugin
    from tests.integration.backends.kafka import KafkaConsumer

    consumer = KafkaConsumer(bootstrap_servers=KAFKA_BOOTSTRAP)
    await consumer.setup()

    config = KafkaOutputPluginConfig(
        bootstrap_servers=[KAFKA_BOOTSTRAP],
        topic=consumer.topic,
    )
    plugin = KafkaOutputPlugin(config=config, params={'id': 1})
    await plugin.open()

    BATCH_SIZE = 100

    try:
        metrics_collector.start()
        start = time.monotonic()

        while time.monotonic() - start < longevity_duration:
            batch = event_factory.create_batch(BATCH_SIZE, EventSize.MEDIUM)
            written = await plugin.write([e.raw_json for e in batch])
            metrics_collector.record_events(written)

        report = metrics_collector.finalize()
        _print_longevity_report('kafka', report)

        assert_no_throughput_degradation(report)
        assert_no_memory_leak(report)
        assert_no_fd_leak(report)
        assert_threads_stable(report)
    finally:
        await plugin.close()
        await consumer.teardown()


@pytest.mark.longevity
async def test_kafka_data_integrity_over_time(
    longevity_duration,
    event_factory,
):
    """Verify data integrity is maintained throughout the run."""
    from eventum.plugins.output.plugins.kafka.config import (
        KafkaOutputPluginConfig,
    )
    from eventum.plugins.output.plugins.kafka.plugin import KafkaOutputPlugin
    from tests.integration.backends.kafka import KafkaConsumer

    consumer = KafkaConsumer(bootstrap_servers=KAFKA_BOOTSTRAP)
    await consumer.setup()

    config = KafkaOutputPluginConfig(
        bootstrap_servers=[KAFKA_BOOTSTRAP],
        topic=consumer.topic,
    )
    plugin = KafkaOutputPlugin(config=config, params={'id': 1})
    await plugin.open()

    BATCH_SIZE = 100
    VERIFY_INTERVAL = 30  # seconds
    total_written = 0

    try:
        start = time.monotonic()
        last_verify = start

        while time.monotonic() - start < longevity_duration:
            batch = event_factory.create_batch(BATCH_SIZE, EventSize.MEDIUM)
            written = await plugin.write([e.raw_json for e in batch])
            total_written += written

            # Periodic verification
            if (
                time.monotonic() - last_verify >= VERIFY_INTERVAL
                and total_written > 0
            ):
                actual_count = await consumer.wait_for_count(
                    total_written,
                    timeout=30,
                )
                assert actual_count >= total_written * 0.99, (
                    f'Data loss: expected ~{total_written}, got {actual_count}'
                )
                last_verify = time.monotonic()

        # Final full verification
        await consumer.wait_for_count(total_written, timeout=60)
        events = await consumer.consume_all()
        verifier = EventVerifier(event_factory.batch_id, total_written)
        result = verifier.verify(events)

        print(
            f'\nIntegrity: received={result.total_received}/{result.total_expected} '
            f'hash_mismatches={result.hash_mismatches} '
            f'duplicates={result.duplicates}'
        )

        assert result.hash_mismatches == 0, (
            f'Hash mismatches: {result.hash_mismatches}'
        )
        assert result.duplicates == 0, f'Duplicates found: {result.duplicates}'
        assert result.total_received >= total_written * 0.99, (
            f'Data loss: received {result.total_received}/{total_written}'
        )
    finally:
        await plugin.close()
        await consumer.teardown()


@pytest.mark.longevity
async def test_kafka_no_connection_exhaustion(event_factory):
    """Verify no cumulative FD growth over many open/close cycles."""
    from eventum.plugins.output.plugins.kafka.config import (
        KafkaOutputPluginConfig,
    )
    from eventum.plugins.output.plugins.kafka.plugin import KafkaOutputPlugin
    from tests.integration.backends.kafka import KafkaConsumer

    CYCLES = 100
    EVENTS_PER_CYCLE = 10

    consumer = KafkaConsumer(bootstrap_servers=KAFKA_BOOTSTRAP)
    await consumer.setup()

    try:
        fd_start = len(os.listdir(f'/proc/{os.getpid()}/fd'))

        for i in range(CYCLES):
            config = KafkaOutputPluginConfig(
                bootstrap_servers=[KAFKA_BOOTSTRAP],
                topic=consumer.topic,
            )
            plugin = KafkaOutputPlugin(config=config, params={'id': 1})
            await plugin.open()

            batch = event_factory.create_batch(
                EVENTS_PER_CYCLE,
                EventSize.SMALL,
            )
            await plugin.write([e.raw_json for e in batch])

            await plugin.close()

        fd_end = len(os.listdir(f'/proc/{os.getpid()}/fd'))
        fd_growth = fd_end - fd_start

        print(
            f'\nFD growth after {CYCLES} cycles: {fd_growth} '
            f'(start={fd_start}, end={fd_end})'
        )

        assert fd_growth <= 20, (
            f'FD leak: grew by {fd_growth} after {CYCLES} open/close cycles'
        )

        # Verify all events arrived
        total_expected = CYCLES * EVENTS_PER_CYCLE
        actual = await consumer.wait_for_count(total_expected, timeout=30)
        assert actual >= total_expected * 0.99
    finally:
        await consumer.teardown()


# =========================================================================
# TCP
# =========================================================================


@pytest.mark.longevity
async def test_tcp_sustained_throughput(
    longevity_duration,
    event_factory,
    metrics_collector,
):
    """Verify sustained throughput over time with no degradation."""
    from eventum.plugins.output.plugins.tcp.config import TcpOutputPluginConfig
    from eventum.plugins.output.plugins.tcp.plugin import TcpOutputPlugin
    from tests.integration.backends.tcp import TcpConsumer

    consumer = TcpConsumer(host='127.0.0.1', port=0)
    await consumer.setup()

    config = TcpOutputPluginConfig(
        host=consumer.host,
        port=consumer.port,
    )
    plugin = TcpOutputPlugin(config=config, params={'id': 1})
    await plugin.open()

    BATCH_SIZE = 100

    try:
        metrics_collector.start()
        start = time.monotonic()

        while time.monotonic() - start < longevity_duration:
            batch = event_factory.create_batch(BATCH_SIZE, EventSize.MEDIUM)
            written = await plugin.write([e.raw_json for e in batch])
            metrics_collector.record_events(written)

        report = metrics_collector.finalize()
        _print_longevity_report('tcp', report)

        assert_no_throughput_degradation(report)
        assert_no_memory_leak(report)
        assert_no_fd_leak(report)
        assert_threads_stable(report)
    finally:
        await plugin.close()
        await consumer.teardown()


@pytest.mark.longevity
async def test_tcp_data_integrity_over_time(
    longevity_duration,
    event_factory,
):
    """Verify data integrity is maintained throughout the run."""
    from eventum.plugins.output.plugins.tcp.config import TcpOutputPluginConfig
    from eventum.plugins.output.plugins.tcp.plugin import TcpOutputPlugin
    from tests.integration.backends.tcp import TcpConsumer

    consumer = TcpConsumer(host='127.0.0.1', port=0)
    await consumer.setup()

    config = TcpOutputPluginConfig(
        host=consumer.host,
        port=consumer.port,
    )
    plugin = TcpOutputPlugin(config=config, params={'id': 1})
    await plugin.open()

    BATCH_SIZE = 100
    VERIFY_INTERVAL = 30  # seconds
    total_written = 0

    try:
        start = time.monotonic()
        last_verify = start

        while time.monotonic() - start < longevity_duration:
            batch = event_factory.create_batch(BATCH_SIZE, EventSize.MEDIUM)
            written = await plugin.write([e.raw_json for e in batch])
            total_written += written

            # Periodic verification
            if (
                time.monotonic() - last_verify >= VERIFY_INTERVAL
                and total_written > 0
            ):
                actual_count = await consumer.wait_for_count(
                    total_written,
                    timeout=30,
                )
                assert actual_count >= total_written * 0.99, (
                    f'Data loss: expected ~{total_written}, got {actual_count}'
                )
                last_verify = time.monotonic()

        # Final full verification
        await consumer.wait_for_count(total_written, timeout=60)
        await asyncio.sleep(0.5)
        events = await consumer.consume_all()
        verifier = EventVerifier(event_factory.batch_id, total_written)
        result = verifier.verify(events)

        print(
            f'\nIntegrity: received={result.total_received}/{result.total_expected} '
            f'hash_mismatches={result.hash_mismatches} '
            f'duplicates={result.duplicates}'
        )

        assert result.hash_mismatches == 0, (
            f'Hash mismatches: {result.hash_mismatches}'
        )
        assert result.duplicates == 0, f'Duplicates found: {result.duplicates}'
        assert result.total_received >= total_written * 0.99, (
            f'Data loss: received {result.total_received}/{total_written}'
        )
    finally:
        await plugin.close()
        await consumer.teardown()


@pytest.mark.longevity
async def test_tcp_no_connection_exhaustion(event_factory):
    """Verify no cumulative FD growth over many open/close cycles."""
    from eventum.plugins.output.plugins.tcp.config import TcpOutputPluginConfig
    from eventum.plugins.output.plugins.tcp.plugin import TcpOutputPlugin
    from tests.integration.backends.tcp import TcpConsumer

    CYCLES = 100
    EVENTS_PER_CYCLE = 10

    consumer = TcpConsumer(host='127.0.0.1', port=0)
    await consumer.setup()

    try:
        fd_start = len(os.listdir(f'/proc/{os.getpid()}/fd'))

        for i in range(CYCLES):
            config = TcpOutputPluginConfig(
                host=consumer.host,
                port=consumer.port,
            )
            plugin = TcpOutputPlugin(config=config, params={'id': 1})
            await plugin.open()

            batch = event_factory.create_batch(
                EVENTS_PER_CYCLE,
                EventSize.SMALL,
            )
            await plugin.write([e.raw_json for e in batch])

            await plugin.close()

        fd_end = len(os.listdir(f'/proc/{os.getpid()}/fd'))
        fd_growth = fd_end - fd_start

        print(
            f'\nFD growth after {CYCLES} cycles: {fd_growth} '
            f'(start={fd_start}, end={fd_end})'
        )

        assert fd_growth <= 20, (
            f'FD leak: grew by {fd_growth} after {CYCLES} open/close cycles'
        )

        # Verify all events arrived
        total_expected = CYCLES * EVENTS_PER_CYCLE
        await asyncio.sleep(0.5)
        actual = await consumer.count()
        assert actual >= total_expected * 0.99
    finally:
        await consumer.teardown()
