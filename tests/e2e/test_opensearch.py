"""End-to-end tests for Eventum → OpenSearch pipeline.

Each test launches ``eventum generate`` as a subprocess targeting a real
OpenSearch instance, then reads events back via the OpenSearch consumer
and verifies count, integrity, and content hashes.
"""

import pytest

from tests.e2e.conftest import (
    GENERATORS_DIR,
    run_eventum_generate,
    run_eventum_with_signal,
)
from tests.integration.conftest import OPENSEARCH_URL
from tests.integration.verification import EventVerifier

pytestmark = [pytest.mark.e2e, pytest.mark.asyncio]

CONFIG_PATH = GENERATORS_DIR / 'opensearch' / 'generator.yml'


def _build_params(consumer, event_count: int) -> dict:
    """Build CLI --params dict targeting the consumer's index."""
    return {
        'event_count': str(event_count),
        'opensearch_url': OPENSEARCH_URL,
        'index': consumer.index,
    }


async def test_generate_and_verify(
    opensearch_consumer, batch_id, gen_id,
):
    """Generate 1000 events and verify full integrity via EventVerifier."""
    event_count = 1000
    consumer = opensearch_consumer
    await consumer.setup()

    try:
        result = await run_eventum_generate(
            config_path=CONFIG_PATH,
            gen_id=gen_id,
            params=_build_params(consumer, event_count),
            env_override={'EVENTUM_TEST_BATCH_ID': batch_id},
        )

        assert result.returncode == 0, (
            f'eventum generate failed (rc={result.returncode}):\n'
            f'{result.stderr[-2000:]}'
        )

        await consumer.wait_for_count(event_count, timeout=30)
        events = await consumer.consume_all()

        verifier = EventVerifier(batch_id, event_count)
        vr = verifier.verify(events)
        assert vr.is_perfect, vr.summary()
    finally:
        await consumer.teardown()


async def test_large_event_count(
    opensearch_consumer, batch_id, gen_id,
):
    """Generate 10 000 events and verify all arrive."""
    event_count = 10_000
    consumer = opensearch_consumer
    await consumer.setup()

    try:
        result = await run_eventum_generate(
            config_path=CONFIG_PATH,
            gen_id=gen_id,
            params=_build_params(consumer, event_count),
            env_override={'EVENTUM_TEST_BATCH_ID': batch_id},
        )

        assert result.returncode == 0, (
            f'eventum generate failed (rc={result.returncode}):\n'
            f'{result.stderr[-2000:]}'
        )

        await consumer.wait_for_count(event_count, timeout=60)
        events = await consumer.consume_all(timeout=30)

        verifier = EventVerifier(batch_id, event_count)
        vr = verifier.verify(events)
        assert vr.is_perfect, vr.summary()
    finally:
        await consumer.teardown()


async def test_parameter_substitution(
    opensearch_consumer, batch_id, gen_id,
):
    """Verify --params JSON is correctly substituted into config."""
    event_count = 500
    consumer = opensearch_consumer
    await consumer.setup()

    try:
        result = await run_eventum_generate(
            config_path=CONFIG_PATH,
            gen_id=gen_id,
            params=_build_params(consumer, event_count),
            env_override={'EVENTUM_TEST_BATCH_ID': batch_id},
        )

        assert result.returncode == 0
        await consumer.wait_for_count(event_count, timeout=30)
        actual = await consumer.count()
        assert actual == event_count, (
            f'Expected exactly {event_count} events, got {actual}'
        )
    finally:
        await consumer.teardown()


async def test_graceful_shutdown(
    opensearch_consumer, batch_id, gen_id,
):
    """Send SIGTERM during generation and verify partial delivery."""
    event_count = 1_000_000
    consumer = opensearch_consumer
    await consumer.setup()

    try:
        result = await run_eventum_with_signal(
            config_path=CONFIG_PATH,
            gen_id=gen_id,
            params=_build_params(consumer, event_count),
            signal_delay=3.0,
            timeout=30,
            env_override={'EVENTUM_TEST_BATCH_ID': batch_id},
        )

        assert result.returncode == 143, (
            f'Expected exit code 143 (SIGTERM), got {result.returncode}'
        )

        actual = await consumer.count()
        assert actual > 0, 'Expected some events to be delivered before SIGTERM'
        assert actual < event_count, (
            'Expected fewer events than requested (shutdown was early)'
        )
    finally:
        await consumer.teardown()


async def test_event_integrity_hashes(
    opensearch_consumer, batch_id, gen_id,
):
    """Verify SHA-256 content hashes on every received event."""
    event_count = 2000
    consumer = opensearch_consumer
    await consumer.setup()

    try:
        result = await run_eventum_generate(
            config_path=CONFIG_PATH,
            gen_id=gen_id,
            params=_build_params(consumer, event_count),
            env_override={'EVENTUM_TEST_BATCH_ID': batch_id},
        )

        assert result.returncode == 0
        await consumer.wait_for_count(event_count, timeout=30)
        events = await consumer.consume_all()

        verifier = EventVerifier(batch_id, event_count)
        vr = verifier.verify(events)

        assert vr.hash_mismatches == 0, (
            f'{vr.hash_mismatches} events had hash mismatches'
        )
        assert vr.duplicates == 0, (
            f'{vr.duplicates} duplicate events detected'
        )
        assert len(vr.missing_sequence_ids) == 0, (
            f'{len(vr.missing_sequence_ids)} missing sequence IDs'
        )
    finally:
        await consumer.teardown()


async def test_sequential_runs(
    opensearch_consumer, gen_id,
):
    """Run the generator twice into the same index and verify both batches."""
    event_count = 500
    consumer = opensearch_consumer
    await consumer.setup()

    batch_id_1 = 'batch_seq_1_' + gen_id
    batch_id_2 = 'batch_seq_2_' + gen_id

    try:
        # First run
        r1 = await run_eventum_generate(
            config_path=CONFIG_PATH,
            gen_id=gen_id,
            params=_build_params(consumer, event_count),
            env_override={'EVENTUM_TEST_BATCH_ID': batch_id_1},
        )
        assert r1.returncode == 0

        # Second run into the same index
        r2 = await run_eventum_generate(
            config_path=CONFIG_PATH,
            gen_id=gen_id,
            params=_build_params(consumer, event_count),
            env_override={'EVENTUM_TEST_BATCH_ID': batch_id_2},
        )
        assert r2.returncode == 0

        await consumer.wait_for_count(
            event_count * 2, timeout=30,
        )
        events = await consumer.consume_all()

        # Verify each batch independently
        vr1 = EventVerifier(batch_id_1, event_count).verify(events)
        vr2 = EventVerifier(batch_id_2, event_count).verify(events)

        assert vr1.total_received == event_count, (
            f'Batch 1: expected {event_count}, got {vr1.total_received}'
        )
        assert vr2.total_received == event_count, (
            f'Batch 2: expected {event_count}, got {vr2.total_received}'
        )
    finally:
        await consumer.teardown()
