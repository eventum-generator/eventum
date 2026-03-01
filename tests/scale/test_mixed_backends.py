"""Mixed backend scale tests.

Verifies that generators targeting different backends can run simultaneously
without interference. Includes a test that all four backends can be driven
concurrently, and a throughput-isolation test that measures whether running
multiple backends degrades any single backend's performance.

All tests are marked ``@pytest.mark.scale`` and require running backend
services (OpenSearch, ClickHouse, Kafka) plus a local TCP server.
"""

from __future__ import annotations

import time

import pytest

from eventum.core.generator import Generator
from tests.integration.conftest import (
    CLICKHOUSE_HOST,
    CLICKHOUSE_PORT,
    KAFKA_BOOTSTRAP,
    OPENSEARCH_URL,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EVENT_COUNT = 5000
COUNT_TOLERANCE = 0.95
WAIT_TIMEOUT = 60
ISOLATION_EVENT_COUNT = 5000
# Allow up to 40% throughput drop when running alongside other backends
ISOLATION_DEGRADATION_THRESHOLD = 0.40


# ---------------------------------------------------------------------------
# Mixed backends — simultaneous
# ---------------------------------------------------------------------------


@pytest.mark.scale
async def test_mixed_backends_simultaneous(generator_factory) -> None:
    """Run generators targeting different backends simultaneously."""
    from tests.integration.backends.clickhouse import ClickHouseConsumer
    from tests.integration.backends.kafka import (
        KafkaConsumer as KafkaTestConsumer,
    )
    from tests.integration.backends.opensearch import OpenSearchConsumer
    from tests.integration.backends.tcp import TcpConsumer

    # Setup all consumers
    os_consumer = OpenSearchConsumer(base_url=OPENSEARCH_URL)
    await os_consumer.setup()

    ch_consumer = ClickHouseConsumer(
        host=CLICKHOUSE_HOST, port=CLICKHOUSE_PORT,
    )
    await ch_consumer.setup()

    kafka_consumer = KafkaTestConsumer(bootstrap_servers=KAFKA_BOOTSTRAP)
    await kafka_consumer.setup()

    tcp_consumer = TcpConsumer(host='127.0.0.1', port=0)
    await tcp_consumer.setup()

    generators: list[Generator] = []
    consumers = [os_consumer, ch_consumer, kafka_consumer, tcp_consumer]

    try:
        # Create generators
        os_gen = generator_factory(
            'opensearch',
            'mixed-os',
            event_count=EVENT_COUNT,
            extra_params={'index': os_consumer.index},
        )
        ch_gen = generator_factory(
            'clickhouse',
            'mixed-ch',
            event_count=EVENT_COUNT,
            extra_params={
                'database': ch_consumer.database,
                'table': ch_consumer.table,
            },
        )
        kafka_gen = generator_factory(
            'kafka',
            'mixed-kafka',
            event_count=EVENT_COUNT,
            extra_params={'topic': kafka_consumer.topic},
        )
        tcp_gen = generator_factory(
            'tcp',
            'mixed-tcp',
            event_count=EVENT_COUNT,
            extra_params={
                'tcp_host': tcp_consumer.host,
                'tcp_port': str(tcp_consumer.port),
            },
        )

        generators = [os_gen, ch_gen, kafka_gen, tcp_gen]

        # Start all simultaneously
        start = time.monotonic()
        for gen in generators:
            assert gen.start(), f'{gen.params.id} failed to start'

        # Wait for all to finish
        for gen in generators:
            gen.join()

        elapsed = time.monotonic() - start

        # Verify all finished successfully
        for gen in generators:
            assert gen.is_ended_up_successfully, (
                f'{gen.params.id} ended with error'
            )

        # Verify event counts (with tolerance)
        os_count = await os_consumer.wait_for_count(
            EVENT_COUNT, timeout=WAIT_TIMEOUT,
        )
        ch_count = await ch_consumer.wait_for_count(
            EVENT_COUNT, timeout=WAIT_TIMEOUT,
        )
        kafka_count = await kafka_consumer.wait_for_count(
            EVENT_COUNT, timeout=WAIT_TIMEOUT,
        )
        tcp_count = await tcp_consumer.wait_for_count(
            EVENT_COUNT, timeout=WAIT_TIMEOUT,
        )

        print(f'\nMixed backends results (elapsed: {elapsed:.1f}s):')
        print(f'  OpenSearch: {os_count}/{EVENT_COUNT}')
        print(f'  ClickHouse: {ch_count}/{EVENT_COUNT}')
        print(f'  Kafka:      {kafka_count}/{EVENT_COUNT}')
        print(f'  TCP:        {tcp_count}/{EVENT_COUNT}')

        for name, count in [
            ('opensearch', os_count),
            ('clickhouse', ch_count),
            ('kafka', kafka_count),
            ('tcp', tcp_count),
        ]:
            assert count >= EVENT_COUNT * COUNT_TOLERANCE, (
                f'{name}: expected ~{EVENT_COUNT}, got {count}'
            )
    finally:
        for gen in generators:
            if gen.is_running:
                gen.stop()
        for consumer in consumers:
            await consumer.teardown()


# ---------------------------------------------------------------------------
# Mixed backends — no interference
# ---------------------------------------------------------------------------


@pytest.mark.scale
async def test_mixed_backends_no_interference(generator_factory) -> None:
    """Verify throughput of one backend is not significantly affected by others.

    Runs each backend in isolation to establish a baseline EPS, then runs
    all four simultaneously and checks that each backend's EPS does not
    drop below ``1 - ISOLATION_DEGRADATION_THRESHOLD`` of its baseline.
    """
    from tests.integration.backends.clickhouse import ClickHouseConsumer
    from tests.integration.backends.kafka import (
        KafkaConsumer as KafkaTestConsumer,
    )
    from tests.integration.backends.opensearch import OpenSearchConsumer
    from tests.integration.backends.tcp import TcpConsumer

    # -- Phase 1: measure each backend in isolation --

    baseline_eps: dict[str, float] = {}

    # OpenSearch baseline
    os_consumer = OpenSearchConsumer(base_url=OPENSEARCH_URL)
    await os_consumer.setup()
    try:
        gen = generator_factory(
            'opensearch',
            'iso-os',
            event_count=ISOLATION_EVENT_COUNT,
            extra_params={'index': os_consumer.index},
        )
        start = time.monotonic()
        assert gen.start(), 'OpenSearch baseline generator failed to start'
        gen.join()
        elapsed = time.monotonic() - start
        assert gen.is_ended_up_successfully
        baseline_eps['opensearch'] = (
            ISOLATION_EVENT_COUNT / elapsed if elapsed > 0 else 0
        )
    finally:
        await os_consumer.teardown()

    # ClickHouse baseline
    ch_consumer = ClickHouseConsumer(
        host=CLICKHOUSE_HOST, port=CLICKHOUSE_PORT,
    )
    await ch_consumer.setup()
    try:
        gen = generator_factory(
            'clickhouse',
            'iso-ch',
            event_count=ISOLATION_EVENT_COUNT,
            extra_params={
                'database': ch_consumer.database,
                'table': ch_consumer.table,
            },
        )
        start = time.monotonic()
        assert gen.start(), 'ClickHouse baseline generator failed to start'
        gen.join()
        elapsed = time.monotonic() - start
        assert gen.is_ended_up_successfully
        baseline_eps['clickhouse'] = (
            ISOLATION_EVENT_COUNT / elapsed if elapsed > 0 else 0
        )
    finally:
        await ch_consumer.teardown()

    # Kafka baseline
    kafka_consumer = KafkaTestConsumer(bootstrap_servers=KAFKA_BOOTSTRAP)
    await kafka_consumer.setup()
    try:
        gen = generator_factory(
            'kafka',
            'iso-kafka',
            event_count=ISOLATION_EVENT_COUNT,
            extra_params={'topic': kafka_consumer.topic},
        )
        start = time.monotonic()
        assert gen.start(), 'Kafka baseline generator failed to start'
        gen.join()
        elapsed = time.monotonic() - start
        assert gen.is_ended_up_successfully
        baseline_eps['kafka'] = (
            ISOLATION_EVENT_COUNT / elapsed if elapsed > 0 else 0
        )
    finally:
        await kafka_consumer.teardown()

    # TCP baseline
    tcp_consumer = TcpConsumer(host='127.0.0.1', port=0)
    await tcp_consumer.setup()
    try:
        gen = generator_factory(
            'tcp',
            'iso-tcp',
            event_count=ISOLATION_EVENT_COUNT,
            extra_params={
                'tcp_host': tcp_consumer.host,
                'tcp_port': str(tcp_consumer.port),
            },
        )
        start = time.monotonic()
        assert gen.start(), 'TCP baseline generator failed to start'
        gen.join()
        elapsed = time.monotonic() - start
        assert gen.is_ended_up_successfully
        baseline_eps['tcp'] = (
            ISOLATION_EVENT_COUNT / elapsed if elapsed > 0 else 0
        )
    finally:
        await tcp_consumer.teardown()

    # -- Phase 2: run all backends simultaneously --

    os_consumer = OpenSearchConsumer(base_url=OPENSEARCH_URL)
    await os_consumer.setup()

    ch_consumer = ClickHouseConsumer(
        host=CLICKHOUSE_HOST, port=CLICKHOUSE_PORT,
    )
    await ch_consumer.setup()

    kafka_consumer = KafkaTestConsumer(bootstrap_servers=KAFKA_BOOTSTRAP)
    await kafka_consumer.setup()

    tcp_consumer = TcpConsumer(host='127.0.0.1', port=0)
    await tcp_consumer.setup()

    consumers = [os_consumer, ch_consumer, kafka_consumer, tcp_consumer]
    generators: list[Generator] = []

    try:
        backend_gens: dict[str, Generator] = {}

        os_gen = generator_factory(
            'opensearch',
            'mixed-iso-os',
            event_count=ISOLATION_EVENT_COUNT,
            extra_params={'index': os_consumer.index},
        )
        ch_gen = generator_factory(
            'clickhouse',
            'mixed-iso-ch',
            event_count=ISOLATION_EVENT_COUNT,
            extra_params={
                'database': ch_consumer.database,
                'table': ch_consumer.table,
            },
        )
        kafka_gen = generator_factory(
            'kafka',
            'mixed-iso-kafka',
            event_count=ISOLATION_EVENT_COUNT,
            extra_params={'topic': kafka_consumer.topic},
        )
        tcp_gen = generator_factory(
            'tcp',
            'mixed-iso-tcp',
            event_count=ISOLATION_EVENT_COUNT,
            extra_params={
                'tcp_host': tcp_consumer.host,
                'tcp_port': str(tcp_consumer.port),
            },
        )

        backend_gens = {
            'opensearch': os_gen,
            'clickhouse': ch_gen,
            'kafka': kafka_gen,
            'tcp': tcp_gen,
        }
        generators = list(backend_gens.values())

        # Time each backend individually within the simultaneous run
        start_times: dict[str, float] = {}
        end_times: dict[str, float] = {}

        global_start = time.monotonic()

        for backend, gen in backend_gens.items():
            assert gen.start(), f'{backend} mixed generator failed to start'
            start_times[backend] = time.monotonic()

        for backend, gen in backend_gens.items():
            gen.join()
            end_times[backend] = time.monotonic()
            assert gen.is_ended_up_successfully, (
                f'{backend} mixed generator failed'
            )

        global_elapsed = time.monotonic() - global_start

        # Calculate mixed EPS for each backend
        mixed_eps: dict[str, float] = {}
        for backend in backend_gens:
            elapsed = end_times[backend] - start_times[backend]
            mixed_eps[backend] = (
                ISOLATION_EVENT_COUNT / elapsed if elapsed > 0 else 0
            )

        # -- Report --
        print(f"\n{'=' * 60}")
        print('INTERFERENCE TEST REPORT')
        print(f'Total elapsed: {global_elapsed:.1f}s')
        print(
            f"{'Backend':<15} {'Baseline EPS':<15} "
            f"{'Mixed EPS':<15} {'Ratio':<10}"
        )

        for backend in sorted(baseline_eps):
            base = baseline_eps[backend]
            mixed = mixed_eps.get(backend, 0)
            ratio = mixed / base if base > 0 else 0
            print(
                f'{backend:<15} {base:<15.0f} '
                f'{mixed:<15.0f} {ratio:<10.2f}'
            )

        print(f"{'=' * 60}\n")

        # -- Assert no significant degradation --
        min_ratio = 1.0 - ISOLATION_DEGRADATION_THRESHOLD

        for backend in baseline_eps:
            base = baseline_eps[backend]
            mixed = mixed_eps.get(backend, 0)

            if base > 0:
                ratio = mixed / base
                assert ratio >= min_ratio, (
                    f'{backend}: mixed EPS ({mixed:.0f}) dropped to '
                    f'{ratio:.0%} of baseline ({base:.0f}), '
                    f'threshold is {min_ratio:.0%}'
                )
    finally:
        for gen in generators:
            if gen.is_running:
                gen.stop()
        for consumer in consumers:
            await consumer.teardown()
