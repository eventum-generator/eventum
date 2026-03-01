"""Lifecycle stability tests for all output backends.

Verifies that generators can be reliably started, stopped, and restarted
without thread leaks or unclean shutdowns. Includes rapid start/stop
cycling and mid-execution termination tests.

All tests are marked ``@pytest.mark.scale`` and require running backend
services (OpenSearch, ClickHouse, Kafka) plus a local TCP server.
"""

from __future__ import annotations

import asyncio
import threading

import pytest

from tests.integration.conftest import (
    CLICKHOUSE_HOST,
    CLICKHOUSE_PORT,
    KAFKA_BOOTSTRAP,
    OPENSEARCH_URL,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CYCLES = 20
CYCLE_EVENT_COUNT = 1000
LARGE_EVENT_COUNT = 1_000_000  # Enough to keep generator busy
MAX_THREAD_GROWTH = 5
STOP_DELAY_SECONDS = 2.0


# ---------------------------------------------------------------------------
# Start/stop cycles — OpenSearch
# ---------------------------------------------------------------------------


@pytest.mark.scale
async def test_opensearch_start_stop_cycles(generator_factory) -> None:
    """Start/stop generator 20 times, verify no thread leaks."""
    from tests.integration.backends.opensearch import OpenSearchConsumer

    thread_counts: list[tuple[int, int]] = []

    for i in range(CYCLES):
        consumer = OpenSearchConsumer(base_url=OPENSEARCH_URL)
        await consumer.setup()

        try:
            gen = generator_factory(
                'opensearch',
                f'lifecycle-os-{i}',
                event_count=CYCLE_EVENT_COUNT,
                extra_params={'index': consumer.index},
            )

            thread_before = threading.active_count()
            assert gen.start(), f'Cycle {i}: Generator failed to start'
            gen.join()
            assert gen.is_ended_up_successfully, (
                f'Cycle {i}: Generator ended with error'
            )
            thread_after = threading.active_count()

            thread_counts.append((thread_before, thread_after))
        finally:
            await consumer.teardown()

    first_before = thread_counts[0][0]
    last_after = thread_counts[-1][1]
    growth = last_after - first_before

    print(
        f'\nThread counts over {CYCLES} cycles: '
        f'start={first_before} end={last_after} growth={growth}'
    )
    assert growth <= MAX_THREAD_GROWTH, (
        f'Thread leak: grew by {growth} over {CYCLES} cycles'
    )


# ---------------------------------------------------------------------------
# Start/stop cycles — ClickHouse
# ---------------------------------------------------------------------------


@pytest.mark.scale
async def test_clickhouse_start_stop_cycles(generator_factory) -> None:
    """Start/stop generator 20 times, verify no thread leaks."""
    from tests.integration.backends.clickhouse import ClickHouseConsumer

    thread_counts: list[tuple[int, int]] = []

    for i in range(CYCLES):
        consumer = ClickHouseConsumer(
            host=CLICKHOUSE_HOST, port=CLICKHOUSE_PORT,
        )
        await consumer.setup()

        try:
            gen = generator_factory(
                'clickhouse',
                f'lifecycle-ch-{i}',
                event_count=CYCLE_EVENT_COUNT,
                extra_params={
                    'database': consumer.database,
                    'table': consumer.table,
                },
            )

            thread_before = threading.active_count()
            assert gen.start(), f'Cycle {i}: Generator failed to start'
            gen.join()
            assert gen.is_ended_up_successfully, (
                f'Cycle {i}: Generator ended with error'
            )
            thread_after = threading.active_count()

            thread_counts.append((thread_before, thread_after))
        finally:
            await consumer.teardown()

    first_before = thread_counts[0][0]
    last_after = thread_counts[-1][1]
    growth = last_after - first_before

    print(
        f'\nThread counts over {CYCLES} cycles: '
        f'start={first_before} end={last_after} growth={growth}'
    )
    assert growth <= MAX_THREAD_GROWTH, (
        f'Thread leak: grew by {growth} over {CYCLES} cycles'
    )


# ---------------------------------------------------------------------------
# Start/stop cycles — Kafka
# ---------------------------------------------------------------------------


@pytest.mark.scale
async def test_kafka_start_stop_cycles(generator_factory) -> None:
    """Start/stop generator 20 times, verify no thread leaks."""
    from tests.integration.backends.kafka import (
        KafkaConsumer as KafkaTestConsumer,
    )

    thread_counts: list[tuple[int, int]] = []

    for i in range(CYCLES):
        consumer = KafkaTestConsumer(bootstrap_servers=KAFKA_BOOTSTRAP)
        await consumer.setup()

        try:
            gen = generator_factory(
                'kafka',
                f'lifecycle-kafka-{i}',
                event_count=CYCLE_EVENT_COUNT,
                extra_params={'topic': consumer.topic},
            )

            thread_before = threading.active_count()
            assert gen.start(), f'Cycle {i}: Generator failed to start'
            gen.join()
            assert gen.is_ended_up_successfully, (
                f'Cycle {i}: Generator ended with error'
            )
            thread_after = threading.active_count()

            thread_counts.append((thread_before, thread_after))
        finally:
            await consumer.teardown()

    first_before = thread_counts[0][0]
    last_after = thread_counts[-1][1]
    growth = last_after - first_before

    print(
        f'\nThread counts over {CYCLES} cycles: '
        f'start={first_before} end={last_after} growth={growth}'
    )
    assert growth <= MAX_THREAD_GROWTH, (
        f'Thread leak: grew by {growth} over {CYCLES} cycles'
    )


# ---------------------------------------------------------------------------
# Start/stop cycles — TCP
# ---------------------------------------------------------------------------


@pytest.mark.scale
async def test_tcp_start_stop_cycles(generator_factory) -> None:
    """Start/stop generator 20 times, verify no thread leaks."""
    from tests.integration.backends.tcp import TcpConsumer

    thread_counts: list[tuple[int, int]] = []

    for i in range(CYCLES):
        consumer = TcpConsumer(host='127.0.0.1', port=0)
        await consumer.setup()

        try:
            gen = generator_factory(
                'tcp',
                f'lifecycle-tcp-{i}',
                event_count=CYCLE_EVENT_COUNT,
                extra_params={
                    'tcp_host': consumer.host,
                    'tcp_port': str(consumer.port),
                },
            )

            thread_before = threading.active_count()
            assert gen.start(), f'Cycle {i}: Generator failed to start'
            gen.join()
            assert gen.is_ended_up_successfully, (
                f'Cycle {i}: Generator ended with error'
            )
            thread_after = threading.active_count()

            thread_counts.append((thread_before, thread_after))
        finally:
            await consumer.teardown()

    first_before = thread_counts[0][0]
    last_after = thread_counts[-1][1]
    growth = last_after - first_before

    print(
        f'\nThread counts over {CYCLES} cycles: '
        f'start={first_before} end={last_after} growth={growth}'
    )
    assert growth <= MAX_THREAD_GROWTH, (
        f'Thread leak: grew by {growth} over {CYCLES} cycles'
    )


# ---------------------------------------------------------------------------
# Stop during execution — OpenSearch
# ---------------------------------------------------------------------------


@pytest.mark.scale
async def test_opensearch_stop_during_execution(
    generator_factory,
) -> None:
    """Stop generator mid-execution, verify clean shutdown."""
    from tests.integration.backends.opensearch import OpenSearchConsumer

    consumer = OpenSearchConsumer(base_url=OPENSEARCH_URL)
    await consumer.setup()

    try:
        gen = generator_factory(
            'opensearch',
            'stop-mid-os',
            event_count=LARGE_EVENT_COUNT,
            extra_params={'index': consumer.index},
        )

        assert gen.start(), 'Generator failed to start'
        assert gen.is_running, 'Generator should be running'

        await asyncio.sleep(STOP_DELAY_SECONDS)

        gen.stop()

        assert gen.is_ended_up, 'Generator should have ended'
        assert not gen.is_running, 'Generator should not be running'
    finally:
        await consumer.teardown()


# ---------------------------------------------------------------------------
# Stop during execution — ClickHouse
# ---------------------------------------------------------------------------


@pytest.mark.scale
async def test_clickhouse_stop_during_execution(
    generator_factory,
) -> None:
    """Stop generator mid-execution, verify clean shutdown."""
    from tests.integration.backends.clickhouse import ClickHouseConsumer

    consumer = ClickHouseConsumer(
        host=CLICKHOUSE_HOST, port=CLICKHOUSE_PORT,
    )
    await consumer.setup()

    try:
        gen = generator_factory(
            'clickhouse',
            'stop-mid-ch',
            event_count=LARGE_EVENT_COUNT,
            extra_params={
                'database': consumer.database,
                'table': consumer.table,
            },
        )

        assert gen.start(), 'Generator failed to start'
        assert gen.is_running, 'Generator should be running'

        await asyncio.sleep(STOP_DELAY_SECONDS)

        gen.stop()

        assert gen.is_ended_up, 'Generator should have ended'
        assert not gen.is_running, 'Generator should not be running'
    finally:
        await consumer.teardown()


# ---------------------------------------------------------------------------
# Stop during execution — Kafka
# ---------------------------------------------------------------------------


@pytest.mark.scale
async def test_kafka_stop_during_execution(generator_factory) -> None:
    """Stop generator mid-execution, verify clean shutdown."""
    from tests.integration.backends.kafka import (
        KafkaConsumer as KafkaTestConsumer,
    )

    consumer = KafkaTestConsumer(bootstrap_servers=KAFKA_BOOTSTRAP)
    await consumer.setup()

    try:
        gen = generator_factory(
            'kafka',
            'stop-mid-kafka',
            event_count=LARGE_EVENT_COUNT,
            extra_params={'topic': consumer.topic},
        )

        assert gen.start(), 'Generator failed to start'
        assert gen.is_running, 'Generator should be running'

        await asyncio.sleep(STOP_DELAY_SECONDS)

        gen.stop()

        assert gen.is_ended_up, 'Generator should have ended'
        assert not gen.is_running, 'Generator should not be running'
    finally:
        await consumer.teardown()


# ---------------------------------------------------------------------------
# Stop during execution — TCP
# ---------------------------------------------------------------------------


@pytest.mark.scale
async def test_tcp_stop_during_execution(generator_factory) -> None:
    """Stop generator mid-execution, verify clean shutdown."""
    from tests.integration.backends.tcp import TcpConsumer

    consumer = TcpConsumer(host='127.0.0.1', port=0)
    await consumer.setup()

    try:
        gen = generator_factory(
            'tcp',
            'stop-mid-tcp',
            event_count=LARGE_EVENT_COUNT,
            extra_params={
                'tcp_host': consumer.host,
                'tcp_port': str(consumer.port),
            },
        )

        assert gen.start(), 'Generator failed to start'
        assert gen.is_running, 'Generator should be running'

        await asyncio.sleep(STOP_DELAY_SECONDS)

        gen.stop()

        assert gen.is_ended_up, 'Generator should have ended'
        assert not gen.is_running, 'Generator should not be running'
    finally:
        await consumer.teardown()
