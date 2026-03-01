"""Shared fixtures for integration tests."""

import asyncio
import os
import socket
import time

import httpx
import pytest

# -- Connection configuration (env-based for CI / local flexibility) --

OPENSEARCH_URL = os.environ.get('OPENSEARCH_URL', 'http://localhost:9200')
CLICKHOUSE_HOST = os.environ.get('CLICKHOUSE_HOST', 'localhost')
CLICKHOUSE_PORT = int(os.environ.get('CLICKHOUSE_PORT', '8123'))
KAFKA_BOOTSTRAP = os.environ.get('KAFKA_BOOTSTRAP', 'localhost:9094')
LONGEVITY_DURATION = int(os.environ.get('EVENTUM_LONGEVITY_DURATION', '120'))


# -- Service readiness helpers --


def _wait_for_service(
    check_fn,
    name: str,
    timeout: float = 60,
    interval: float = 2,
) -> None:
    """Block until check_fn() succeeds or timeout."""
    deadline = time.monotonic() + timeout
    last_error = None

    while time.monotonic() < deadline:
        try:
            check_fn()
            return
        except Exception as e:
            last_error = e
            time.sleep(interval)

    pytest.fail(f'{name} not ready after {timeout}s: {last_error}')


def _check_opensearch() -> None:
    r = httpx.get(f'{OPENSEARCH_URL}/_cluster/health', timeout=5)
    r.raise_for_status()


def _check_clickhouse() -> None:
    r = httpx.get(
        f'http://{CLICKHOUSE_HOST}:{CLICKHOUSE_PORT}/ping',
        timeout=5,
    )
    r.raise_for_status()


def _check_kafka() -> None:
    s = socket.create_connection(
        (KAFKA_BOOTSTRAP.split(':')[0], int(KAFKA_BOOTSTRAP.split(':')[1])),
        timeout=5,
    )
    s.close()


# -- Session-scoped service readiness fixtures --


@pytest.fixture(scope='session')
def opensearch_url():
    """Return OpenSearch URL after verifying service is ready."""
    _wait_for_service(_check_opensearch, 'OpenSearch')
    return OPENSEARCH_URL


@pytest.fixture(scope='session')
def clickhouse_dsn():
    """Return (host, port) after verifying ClickHouse is ready."""
    _wait_for_service(_check_clickhouse, 'ClickHouse')
    return (CLICKHOUSE_HOST, CLICKHOUSE_PORT)


@pytest.fixture(scope='session')
def kafka_bootstrap():
    """Return bootstrap servers string after verifying Kafka is ready."""
    _wait_for_service(_check_kafka, 'Kafka')
    return KAFKA_BOOTSTRAP


# -- Shared utility fixtures --


@pytest.fixture()
def event_factory():
    """Create a fresh EventFactory for each test."""
    from tests.integration.event_factory import EventFactory

    return EventFactory()


@pytest.fixture()
def metrics_collector():
    """Create a fresh MetricsCollector for each test."""
    from tests.integration.metrics import MetricsCollector

    return MetricsCollector(warmup_seconds=5.0)


@pytest.fixture()
def longevity_duration():
    """Return configured longevity test duration in seconds."""
    return LONGEVITY_DURATION
