"""Enterprise-grade throughput benchmark tests for output plugins.

Measures sustained write throughput (events per second) across all four
output backends under various batch sizes and event sizes. Each test
runs a warmup phase followed by a timed measurement phase, collecting
periodic performance snapshots for statistical analysis.

All tests are marked ``@pytest.mark.performance`` and require running
backend services (OpenSearch, ClickHouse, Kafka) plus a local TCP server.
"""

from __future__ import annotations

import asyncio
import time

import pytest

from tests.integration.assertions import assert_no_throughput_degradation
from tests.integration.conftest import (
    CLICKHOUSE_HOST,
    CLICKHOUSE_PORT,
    KAFKA_BOOTSTRAP,
    OPENSEARCH_URL,
)
from tests.integration.event_factory import EventFactory, EventSize
from tests.integration.metrics import MetricsCollector

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WARMUP_SECONDS = 5.0
MEASUREMENT_SECONDS = 30.0
CONCURRENT_WRITERS = 10
CONCURRENT_BATCH_SIZE = 100
CONCURRENT_MEASUREMENT_SECONDS = 15.0

# Soft EPS thresholds — warn only, do not fail (hardware-dependent)
MIN_EPS: dict[str, int] = {
    'opensearch': 500,
    'clickhouse': 1000,
    'kafka': 1000,
    'tcp': 5000,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _print_report(
    backend: str,
    report,
    *,
    batch_size: int | None = None,
    event_size: EventSize | None = None,
    concurrency: int | None = None,
) -> None:
    """Print a human-readable performance report for CI visibility."""
    label_parts = [f'Backend: {backend}']
    if batch_size is not None:
        label_parts.append(f'batch_size={batch_size}')
    if event_size is not None:
        label_parts.append(f'event_size={event_size.value}')
    if concurrency is not None:
        label_parts.append(f'concurrency={concurrency}')
    label = ' | '.join(label_parts)

    print(f'\n{"=" * 60}')
    print(label)
    print(
        f'Duration: {report.duration_seconds:.1f}s | '
        f'Total events: {report.total_events}'
    )
    print(
        f'EPS: mean={report.eps_mean:.0f} '
        f'p50={report.eps_p50:.0f} '
        f'p95={report.eps_p95:.0f} '
        f'p99={report.eps_p99:.0f}'
    )
    print(
        f'EPS range: min={report.eps_min:.0f} '
        f'max={report.eps_max:.0f} '
        f'stddev={report.eps_stddev:.0f}'
    )
    print(
        f'RSS: start={report.rss_start_bytes / 1024 / 1024:.1f}MB '
        f'end={report.rss_end_bytes / 1024 / 1024:.1f}MB '
        f'peak={report.rss_peak_bytes / 1024 / 1024:.1f}MB'
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
    print(f'{"=" * 60}\n')


def _check_soft_threshold(backend: str, report) -> None:
    """Print a warning if EPS is below the expected minimum."""
    threshold = MIN_EPS.get(backend, 0)
    if report.eps_mean < threshold:
        print(
            f'WARNING: EPS ({report.eps_mean:.0f}) below expected '
            f'minimum ({threshold})'
        )


# ---------------------------------------------------------------------------
# OpenSearch throughput
# ---------------------------------------------------------------------------


@pytest.mark.performance
@pytest.mark.parametrize('batch_size', [1, 10, 100, 1000])
@pytest.mark.parametrize(
    'event_size',
    [EventSize.SMALL, EventSize.MEDIUM, EventSize.LARGE],
)
async def test_opensearch_throughput(
    batch_size: int,
    event_size: EventSize,
    metrics_collector: MetricsCollector,
) -> None:
    """Measure sustained OpenSearch write throughput."""
    from eventum.plugins.output.plugins.opensearch.config import (
        OpensearchOutputPluginConfig,
    )
    from eventum.plugins.output.plugins.opensearch.plugin import (
        OpensearchOutputPlugin,
    )
    from tests.integration.backends.opensearch import OpenSearchConsumer

    consumer = OpenSearchConsumer(base_url=OPENSEARCH_URL)
    await consumer.setup()

    try:
        config = OpensearchOutputPluginConfig(
            hosts=[OPENSEARCH_URL],  # type: ignore
            username='admin',
            password='admin',
            index=consumer.index,
            verify=False,
        )
        plugin = OpensearchOutputPlugin(config=config, params={'id': 1})
        await plugin.open()

        try:
            factory = EventFactory()
            metrics_collector.start()

            start = time.monotonic()
            while (
                time.monotonic() - start < WARMUP_SECONDS + MEASUREMENT_SECONDS
            ):
                batch = factory.create_batch(batch_size, event_size)
                written = await plugin.write([e.raw_json for e in batch])
                metrics_collector.record_events(written)

            report = metrics_collector.finalize()

            _print_report(
                'opensearch',
                report,
                batch_size=batch_size,
                event_size=event_size,
            )

            assert_no_throughput_degradation(report)
            assert report.total_events > 0, 'No events were written'

            _check_soft_threshold('opensearch', report)
        finally:
            await plugin.close()
    finally:
        await consumer.teardown()


# ---------------------------------------------------------------------------
# ClickHouse throughput
# ---------------------------------------------------------------------------


@pytest.mark.performance
@pytest.mark.parametrize('batch_size', [1, 10, 100, 1000])
@pytest.mark.parametrize(
    'event_size',
    [EventSize.SMALL, EventSize.MEDIUM, EventSize.LARGE],
)
async def test_clickhouse_throughput(
    batch_size: int,
    event_size: EventSize,
    metrics_collector: MetricsCollector,
) -> None:
    """Measure sustained ClickHouse write throughput."""
    from eventum.plugins.output.plugins.clickhouse.config import (
        ClickhouseOutputPluginConfig,
    )
    from eventum.plugins.output.plugins.clickhouse.plugin import (
        ClickhouseOutputPlugin,
    )
    from tests.integration.backends.clickhouse import ClickHouseConsumer

    consumer = ClickHouseConsumer(host=CLICKHOUSE_HOST, port=CLICKHOUSE_PORT)
    await consumer.setup()

    try:
        config = ClickhouseOutputPluginConfig(
            host=CLICKHOUSE_HOST,
            port=CLICKHOUSE_PORT,
            database=consumer.database,
            table=consumer.table,
        )
        plugin = ClickhouseOutputPlugin(config=config, params={'id': 1})
        await plugin.open()

        try:
            factory = EventFactory()
            metrics_collector.start()

            start = time.monotonic()
            while (
                time.monotonic() - start < WARMUP_SECONDS + MEASUREMENT_SECONDS
            ):
                batch = factory.create_batch(batch_size, event_size)
                written = await plugin.write([e.raw_json for e in batch])
                metrics_collector.record_events(written)

            report = metrics_collector.finalize()

            _print_report(
                'clickhouse',
                report,
                batch_size=batch_size,
                event_size=event_size,
            )

            assert_no_throughput_degradation(report)
            assert report.total_events > 0, 'No events were written'

            _check_soft_threshold('clickhouse', report)
        finally:
            await plugin.close()
    finally:
        await consumer.teardown()


# ---------------------------------------------------------------------------
# Kafka throughput
# ---------------------------------------------------------------------------


@pytest.mark.performance
@pytest.mark.parametrize('batch_size', [1, 10, 100, 1000])
@pytest.mark.parametrize(
    'event_size',
    [EventSize.SMALL, EventSize.MEDIUM, EventSize.LARGE],
)
async def test_kafka_throughput(
    batch_size: int,
    event_size: EventSize,
    metrics_collector: MetricsCollector,
) -> None:
    """Measure sustained Kafka write throughput."""
    from eventum.plugins.output.plugins.kafka.config import (
        KafkaOutputPluginConfig,
    )
    from eventum.plugins.output.plugins.kafka.plugin import KafkaOutputPlugin
    from tests.integration.backends.kafka import (
        KafkaConsumer as KafkaTestConsumer,
    )

    consumer = KafkaTestConsumer(bootstrap_servers=KAFKA_BOOTSTRAP)
    await consumer.setup()

    try:
        config = KafkaOutputPluginConfig(
            bootstrap_servers=[KAFKA_BOOTSTRAP],
            topic=consumer.topic,
        )
        plugin = KafkaOutputPlugin(config=config, params={'id': 1})
        await plugin.open()

        try:
            factory = EventFactory()
            metrics_collector.start()

            start = time.monotonic()
            while (
                time.monotonic() - start < WARMUP_SECONDS + MEASUREMENT_SECONDS
            ):
                batch = factory.create_batch(batch_size, event_size)
                written = await plugin.write([e.raw_json for e in batch])
                metrics_collector.record_events(written)

            report = metrics_collector.finalize()

            _print_report(
                'kafka',
                report,
                batch_size=batch_size,
                event_size=event_size,
            )

            assert_no_throughput_degradation(report)
            assert report.total_events > 0, 'No events were written'

            _check_soft_threshold('kafka', report)
        finally:
            await plugin.close()
    finally:
        await consumer.teardown()


# ---------------------------------------------------------------------------
# TCP throughput
# ---------------------------------------------------------------------------


@pytest.mark.performance
@pytest.mark.parametrize('batch_size', [1, 10, 100, 1000])
@pytest.mark.parametrize(
    'event_size',
    [EventSize.SMALL, EventSize.MEDIUM, EventSize.LARGE],
)
async def test_tcp_throughput(
    batch_size: int,
    event_size: EventSize,
    metrics_collector: MetricsCollector,
) -> None:
    """Measure sustained TCP write throughput."""
    from eventum.plugins.output.plugins.tcp.config import TcpOutputPluginConfig
    from eventum.plugins.output.plugins.tcp.plugin import TcpOutputPlugin
    from tests.integration.backends.tcp import TcpConsumer

    consumer = TcpConsumer(host='127.0.0.1', port=0)
    await consumer.setup()

    try:
        config = TcpOutputPluginConfig(
            host=consumer.host,
            port=consumer.port,
        )
        plugin = TcpOutputPlugin(config=config, params={'id': 1})
        await plugin.open()

        try:
            factory = EventFactory()
            metrics_collector.start()

            start = time.monotonic()
            while (
                time.monotonic() - start < WARMUP_SECONDS + MEASUREMENT_SECONDS
            ):
                batch = factory.create_batch(batch_size, event_size)
                written = await plugin.write([e.raw_json for e in batch])
                metrics_collector.record_events(written)

            report = metrics_collector.finalize()

            _print_report(
                'tcp',
                report,
                batch_size=batch_size,
                event_size=event_size,
            )

            assert_no_throughput_degradation(report)
            assert report.total_events > 0, 'No events were written'

            _check_soft_threshold('tcp', report)
        finally:
            await plugin.close()
    finally:
        await consumer.teardown()


# ---------------------------------------------------------------------------
# Concurrent throughput — OpenSearch
# ---------------------------------------------------------------------------


@pytest.mark.performance
async def test_opensearch_concurrent_throughput(
    metrics_collector: MetricsCollector,
) -> None:
    """Measure OpenSearch throughput with concurrent writers."""
    from eventum.plugins.output.plugins.opensearch.config import (
        OpensearchOutputPluginConfig,
    )
    from eventum.plugins.output.plugins.opensearch.plugin import (
        OpensearchOutputPlugin,
    )
    from tests.integration.backends.opensearch import OpenSearchConsumer

    consumer = OpenSearchConsumer(base_url=OPENSEARCH_URL)
    await consumer.setup()

    try:
        config = OpensearchOutputPluginConfig(
            hosts=[OPENSEARCH_URL],  # type: ignore
            username='admin',
            password='admin',
            index=consumer.index,
            verify=False,
        )
        plugin = OpensearchOutputPlugin(config=config, params={'id': 1})
        await plugin.open()

        try:
            factory = EventFactory()
            metrics_collector.start()
            start = time.monotonic()

            async def writer() -> None:
                while (
                    time.monotonic() - start < CONCURRENT_MEASUREMENT_SECONDS
                ):
                    batch = factory.create_batch(
                        CONCURRENT_BATCH_SIZE,
                        EventSize.MEDIUM,
                    )
                    written = await plugin.write(
                        [e.raw_json for e in batch],
                    )
                    metrics_collector.record_events(written)

            await asyncio.gather(
                *[writer() for _ in range(CONCURRENT_WRITERS)],
            )

            report = metrics_collector.finalize()

            _print_report(
                'opensearch',
                report,
                concurrency=CONCURRENT_WRITERS,
            )

            assert_no_throughput_degradation(report)
            assert report.total_events > 0, 'No events were written'

            _check_soft_threshold('opensearch', report)
        finally:
            await plugin.close()
    finally:
        await consumer.teardown()


# ---------------------------------------------------------------------------
# Concurrent throughput — ClickHouse
# ---------------------------------------------------------------------------


@pytest.mark.performance
async def test_clickhouse_concurrent_throughput(
    metrics_collector: MetricsCollector,
) -> None:
    """Measure ClickHouse throughput with concurrent writers."""
    from eventum.plugins.output.plugins.clickhouse.config import (
        ClickhouseOutputPluginConfig,
    )
    from eventum.plugins.output.plugins.clickhouse.plugin import (
        ClickhouseOutputPlugin,
    )
    from tests.integration.backends.clickhouse import ClickHouseConsumer

    consumer = ClickHouseConsumer(host=CLICKHOUSE_HOST, port=CLICKHOUSE_PORT)
    await consumer.setup()

    try:
        config = ClickhouseOutputPluginConfig(
            host=CLICKHOUSE_HOST,
            port=CLICKHOUSE_PORT,
            database=consumer.database,
            table=consumer.table,
        )
        plugin = ClickhouseOutputPlugin(config=config, params={'id': 1})
        await plugin.open()

        try:
            factory = EventFactory()
            metrics_collector.start()
            start = time.monotonic()

            async def writer() -> None:
                while (
                    time.monotonic() - start < CONCURRENT_MEASUREMENT_SECONDS
                ):
                    batch = factory.create_batch(
                        CONCURRENT_BATCH_SIZE,
                        EventSize.MEDIUM,
                    )
                    written = await plugin.write(
                        [e.raw_json for e in batch],
                    )
                    metrics_collector.record_events(written)

            await asyncio.gather(
                *[writer() for _ in range(CONCURRENT_WRITERS)],
            )

            report = metrics_collector.finalize()

            _print_report(
                'clickhouse',
                report,
                concurrency=CONCURRENT_WRITERS,
            )

            assert_no_throughput_degradation(report)
            assert report.total_events > 0, 'No events were written'

            _check_soft_threshold('clickhouse', report)
        finally:
            await plugin.close()
    finally:
        await consumer.teardown()


# ---------------------------------------------------------------------------
# Concurrent throughput — Kafka
# ---------------------------------------------------------------------------


@pytest.mark.performance
async def test_kafka_concurrent_throughput(
    metrics_collector: MetricsCollector,
) -> None:
    """Measure Kafka throughput with concurrent writers."""
    from eventum.plugins.output.plugins.kafka.config import (
        KafkaOutputPluginConfig,
    )
    from eventum.plugins.output.plugins.kafka.plugin import KafkaOutputPlugin
    from tests.integration.backends.kafka import (
        KafkaConsumer as KafkaTestConsumer,
    )

    consumer = KafkaTestConsumer(bootstrap_servers=KAFKA_BOOTSTRAP)
    await consumer.setup()

    try:
        config = KafkaOutputPluginConfig(
            bootstrap_servers=[KAFKA_BOOTSTRAP],
            topic=consumer.topic,
        )
        plugin = KafkaOutputPlugin(config=config, params={'id': 1})
        await plugin.open()

        try:
            factory = EventFactory()
            metrics_collector.start()
            start = time.monotonic()

            async def writer() -> None:
                while (
                    time.monotonic() - start < CONCURRENT_MEASUREMENT_SECONDS
                ):
                    batch = factory.create_batch(
                        CONCURRENT_BATCH_SIZE,
                        EventSize.MEDIUM,
                    )
                    written = await plugin.write(
                        [e.raw_json for e in batch],
                    )
                    metrics_collector.record_events(written)

            await asyncio.gather(
                *[writer() for _ in range(CONCURRENT_WRITERS)],
            )

            report = metrics_collector.finalize()

            _print_report(
                'kafka',
                report,
                concurrency=CONCURRENT_WRITERS,
            )

            assert_no_throughput_degradation(report)
            assert report.total_events > 0, 'No events were written'

            _check_soft_threshold('kafka', report)
        finally:
            await plugin.close()
    finally:
        await consumer.teardown()


# ---------------------------------------------------------------------------
# Concurrent throughput — TCP
# ---------------------------------------------------------------------------


@pytest.mark.performance
async def test_tcp_concurrent_throughput(
    metrics_collector: MetricsCollector,
) -> None:
    """Measure TCP throughput with concurrent writers."""
    from eventum.plugins.output.plugins.tcp.config import TcpOutputPluginConfig
    from eventum.plugins.output.plugins.tcp.plugin import TcpOutputPlugin
    from tests.integration.backends.tcp import TcpConsumer

    consumer = TcpConsumer(host='127.0.0.1', port=0)
    await consumer.setup()

    try:
        config = TcpOutputPluginConfig(
            host=consumer.host,
            port=consumer.port,
        )
        plugin = TcpOutputPlugin(config=config, params={'id': 1})
        await plugin.open()

        try:
            factory = EventFactory()
            metrics_collector.start()
            start = time.monotonic()

            async def writer() -> None:
                while (
                    time.monotonic() - start < CONCURRENT_MEASUREMENT_SECONDS
                ):
                    batch = factory.create_batch(
                        CONCURRENT_BATCH_SIZE,
                        EventSize.MEDIUM,
                    )
                    written = await plugin.write(
                        [e.raw_json for e in batch],
                    )
                    metrics_collector.record_events(written)

            await asyncio.gather(
                *[writer() for _ in range(CONCURRENT_WRITERS)],
            )

            report = metrics_collector.finalize()

            _print_report(
                'tcp',
                report,
                concurrency=CONCURRENT_WRITERS,
            )

            assert_no_throughput_degradation(report)
            assert report.total_events > 0, 'No events were written'

            _check_soft_threshold('tcp', report)
        finally:
            await plugin.close()
    finally:
        await consumer.teardown()
