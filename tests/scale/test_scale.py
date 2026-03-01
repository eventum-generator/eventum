"""Scale ramp-up tests for all output backends.

Gradually increases the number of concurrent generators (1 -> 2 -> 5 -> 10)
targeting each backend and measures aggregate events-per-second at each
level. Detects saturation when per-generator EPS drops below 50% of the
single-generator baseline.

All tests are marked ``@pytest.mark.scale`` and require running backend
services (OpenSearch, ClickHouse, Kafka) plus a local TCP server.
"""

from __future__ import annotations

import time

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

EVENT_COUNT = 10_000
LEVELS_FULL = [1, 2, 5, 10]
LEVELS_TCP = [1, 2, 5]  # TCP is in-process, use fewer levels
COUNT_TOLERANCE = 0.95
WAIT_TIMEOUT = 60


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _print_ramp_up_report(
    backend: str,
    results: dict[int, dict],
) -> None:
    """Print a human-readable ramp-up report for CI visibility."""
    baseline_per_gen = (
        results[1]['per_gen_eps'] if 1 in results else 0
    )

    print(f"\n{'=' * 60}")
    print(f'SCALE RAMP-UP REPORT: {backend}')
    print(
        f"{'Level':<10} {'Agg EPS':<15} {'Per-Gen EPS':<15} {'Elapsed':<10}"
    )

    for level, data in sorted(results.items()):
        saturation_pct = (
            (data['per_gen_eps'] / baseline_per_gen * 100)
            if baseline_per_gen > 0
            else 0
        )
        print(
            f"{level:<10} "
            f"{data['aggregate_eps']:<15.0f} "
            f"{data['per_gen_eps']:<15.0f} "
            f"{data['elapsed']:<10.1f}s "
            f"({saturation_pct:.0f}%)"
        )

    print(f"{'=' * 60}\n")

    # Detect saturation: per-gen EPS drops > 50% of baseline
    if baseline_per_gen > 0:
        for level, data in sorted(results.items()):
            if data['per_gen_eps'] < baseline_per_gen * 0.5:
                print(
                    f'Saturation detected at level {level}: '
                    f"per-gen EPS dropped to {data['per_gen_eps']:.0f} "
                    f'(baseline: {baseline_per_gen:.0f})'
                )
                break


# ---------------------------------------------------------------------------
# OpenSearch ramp-up
# ---------------------------------------------------------------------------


@pytest.mark.scale
async def test_opensearch_gradual_ramp_up(generator_factory, report_store) -> None:
    """Ramp up 1->2->5->10 generators, measure aggregate EPS at each level."""
    from tests.integration.backends.opensearch import OpenSearchConsumer

    results: dict[int, dict] = {}

    for level in LEVELS_FULL:
        consumers: list[OpenSearchConsumer] = []
        generators = []

        try:
            for i in range(level):
                consumer = OpenSearchConsumer(base_url=OPENSEARCH_URL)
                await consumer.setup()
                consumers.append(consumer)

                gen = generator_factory(
                    'opensearch',
                    f'scale-os-{level}-{i}',
                    event_count=EVENT_COUNT,
                    extra_params={'index': consumer.index},
                )
                generators.append(gen)

            # Start all generators
            start_time = time.monotonic()
            for gen in generators:
                assert gen.start(), (
                    f'Generator {gen.params.id} failed to start'
                )

            # Wait for all to finish
            for gen in generators:
                gen.join()

            elapsed = time.monotonic() - start_time
            total_events = level * EVENT_COUNT
            aggregate_eps = (
                total_events / elapsed if elapsed > 0 else 0
            )
            per_gen_eps = aggregate_eps / level

            results[level] = {
                'aggregate_eps': aggregate_eps,
                'per_gen_eps': per_gen_eps,
                'elapsed': elapsed,
            }

            # Verify all generators finished successfully
            for gen in generators:
                assert gen.is_ended_up_successfully, (
                    f'Generator {gen.params.id} failed'
                )

            # Verify event counts
            for consumer in consumers:
                actual = await consumer.wait_for_count(
                    EVENT_COUNT, timeout=WAIT_TIMEOUT,
                )
                assert actual >= EVENT_COUNT * COUNT_TOLERANCE, (
                    f'Expected ~{EVENT_COUNT}, got {actual}'
                )
        finally:
            for gen in generators:
                if gen.is_running:
                    gen.stop()
            for consumer in consumers:
                await consumer.teardown()

    _print_ramp_up_report('opensearch', results)
    report_store.add_scale_result('test_opensearch_gradual_ramp_up', results)


# ---------------------------------------------------------------------------
# ClickHouse ramp-up
# ---------------------------------------------------------------------------


@pytest.mark.scale
async def test_clickhouse_gradual_ramp_up(generator_factory, report_store) -> None:
    """Ramp up 1->2->5->10 generators, measure aggregate EPS at each level."""
    from tests.integration.backends.clickhouse import ClickHouseConsumer

    results: dict[int, dict] = {}

    for level in LEVELS_FULL:
        consumers: list[ClickHouseConsumer] = []
        generators = []

        try:
            for i in range(level):
                consumer = ClickHouseConsumer(
                    host=CLICKHOUSE_HOST, port=CLICKHOUSE_PORT,
                )
                await consumer.setup()
                consumers.append(consumer)

                gen = generator_factory(
                    'clickhouse',
                    f'scale-ch-{level}-{i}',
                    event_count=EVENT_COUNT,
                    extra_params={
                        'database': consumer.database,
                        'table': consumer.table,
                    },
                )
                generators.append(gen)

            start_time = time.monotonic()
            for gen in generators:
                assert gen.start(), (
                    f'Generator {gen.params.id} failed to start'
                )

            for gen in generators:
                gen.join()

            elapsed = time.monotonic() - start_time
            total_events = level * EVENT_COUNT
            aggregate_eps = (
                total_events / elapsed if elapsed > 0 else 0
            )
            per_gen_eps = aggregate_eps / level

            results[level] = {
                'aggregate_eps': aggregate_eps,
                'per_gen_eps': per_gen_eps,
                'elapsed': elapsed,
            }

            for gen in generators:
                assert gen.is_ended_up_successfully, (
                    f'Generator {gen.params.id} failed'
                )

            for consumer in consumers:
                actual = await consumer.wait_for_count(
                    EVENT_COUNT, timeout=WAIT_TIMEOUT,
                )
                assert actual >= EVENT_COUNT * COUNT_TOLERANCE, (
                    f'Expected ~{EVENT_COUNT}, got {actual}'
                )
        finally:
            for gen in generators:
                if gen.is_running:
                    gen.stop()
            for consumer in consumers:
                await consumer.teardown()

    _print_ramp_up_report('clickhouse', results)
    report_store.add_scale_result('test_clickhouse_gradual_ramp_up', results)


# ---------------------------------------------------------------------------
# Kafka ramp-up
# ---------------------------------------------------------------------------


@pytest.mark.scale
async def test_kafka_gradual_ramp_up(generator_factory, report_store) -> None:
    """Ramp up 1->2->5->10 generators, measure aggregate EPS at each level."""
    from tests.integration.backends.kafka import (
        KafkaConsumer as KafkaTestConsumer,
    )

    results: dict[int, dict] = {}

    for level in LEVELS_FULL:
        consumers: list[KafkaTestConsumer] = []
        generators = []

        try:
            for i in range(level):
                consumer = KafkaTestConsumer(
                    bootstrap_servers=KAFKA_BOOTSTRAP,
                )
                await consumer.setup()
                consumers.append(consumer)

                gen = generator_factory(
                    'kafka',
                    f'scale-kafka-{level}-{i}',
                    event_count=EVENT_COUNT,
                    extra_params={'topic': consumer.topic},
                )
                generators.append(gen)

            start_time = time.monotonic()
            for gen in generators:
                assert gen.start(), (
                    f'Generator {gen.params.id} failed to start'
                )

            for gen in generators:
                gen.join()

            elapsed = time.monotonic() - start_time
            total_events = level * EVENT_COUNT
            aggregate_eps = (
                total_events / elapsed if elapsed > 0 else 0
            )
            per_gen_eps = aggregate_eps / level

            results[level] = {
                'aggregate_eps': aggregate_eps,
                'per_gen_eps': per_gen_eps,
                'elapsed': elapsed,
            }

            for gen in generators:
                assert gen.is_ended_up_successfully, (
                    f'Generator {gen.params.id} failed'
                )

            for consumer in consumers:
                actual = await consumer.wait_for_count(
                    EVENT_COUNT, timeout=WAIT_TIMEOUT,
                )
                assert actual >= EVENT_COUNT * COUNT_TOLERANCE, (
                    f'Expected ~{EVENT_COUNT}, got {actual}'
                )
        finally:
            for gen in generators:
                if gen.is_running:
                    gen.stop()
            for consumer in consumers:
                await consumer.teardown()

    _print_ramp_up_report('kafka', results)
    report_store.add_scale_result('test_kafka_gradual_ramp_up', results)


# ---------------------------------------------------------------------------
# TCP ramp-up
# ---------------------------------------------------------------------------


@pytest.mark.scale
async def test_tcp_gradual_ramp_up(generator_factory, report_store) -> None:
    """Ramp up 1->2->5 generators, measure aggregate EPS at each level."""
    from tests.integration.backends.tcp import TcpConsumer

    results: dict[int, dict] = {}

    for level in LEVELS_TCP:
        consumers: list[TcpConsumer] = []
        generators = []

        try:
            for i in range(level):
                consumer = TcpConsumer(host='127.0.0.1', port=0)
                await consumer.setup()
                consumers.append(consumer)

                gen = generator_factory(
                    'tcp',
                    f'scale-tcp-{level}-{i}',
                    event_count=EVENT_COUNT,
                    extra_params={
                        'tcp_host': consumer.host,
                        'tcp_port': str(consumer.port),
                    },
                )
                generators.append(gen)

            start_time = time.monotonic()
            for gen in generators:
                assert gen.start(), (
                    f'Generator {gen.params.id} failed to start'
                )

            for gen in generators:
                gen.join()

            elapsed = time.monotonic() - start_time
            total_events = level * EVENT_COUNT
            aggregate_eps = (
                total_events / elapsed if elapsed > 0 else 0
            )
            per_gen_eps = aggregate_eps / level

            results[level] = {
                'aggregate_eps': aggregate_eps,
                'per_gen_eps': per_gen_eps,
                'elapsed': elapsed,
            }

            for gen in generators:
                assert gen.is_ended_up_successfully, (
                    f'Generator {gen.params.id} failed'
                )

            for consumer in consumers:
                actual = await consumer.wait_for_count(
                    EVENT_COUNT, timeout=WAIT_TIMEOUT,
                )
                assert actual >= EVENT_COUNT * COUNT_TOLERANCE, (
                    f'Expected ~{EVENT_COUNT}, got {actual}'
                )
        finally:
            for gen in generators:
                if gen.is_running:
                    gen.stop()
            for consumer in consumers:
                await consumer.teardown()

    _print_ramp_up_report('tcp', results)
    report_store.add_scale_result('test_tcp_gradual_ramp_up', results)
