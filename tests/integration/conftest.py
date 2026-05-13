"""Fixtures for integration tests.

Provides service readiness checks, per-test plugin and consumer instances
with automatic setup/teardown of backend resources.
"""

import os
import socket
import time

import httpx
import pytest
import pytest_asyncio

# - Connection configuration (env-based for CI / local flexibility) --

OPENSEARCH_URL = os.environ.get('OPENSEARCH_URL', 'http://localhost:9200')
CLICKHOUSE_HOST = os.environ.get('CLICKHOUSE_HOST', 'localhost')
CLICKHOUSE_PORT = int(os.environ.get('CLICKHOUSE_PORT', '8123'))
KAFKA_BOOTSTRAP = os.environ.get('KAFKA_BOOTSTRAP', 'localhost:9094')


# - Service readiness helpers --


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
    r = httpx.get(
        f'{OPENSEARCH_URL}/_cluster/health',
        timeout=5,
        headers={'Accept-Encoding': ''},
    )
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


# - Session-scoped service readiness fixtures --


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


# - Shared utility fixtures --


@pytest.fixture()
def event_factory():
    """Create a fresh EventFactory for each test."""
    from tests.integration.event_factory import EventFactory

    return EventFactory()


# - OpenSearch fixtures --


@pytest_asyncio.fixture()
async def opensearch_consumer(opensearch_url):
    """Create an OpenSearch consumer with unique index, clean up after."""
    from tests.integration.backends.opensearch import OpenSearchConsumer

    consumer = OpenSearchConsumer(
        base_url=opensearch_url,
    )
    await consumer.setup()
    yield consumer
    await consumer.teardown()


@pytest_asyncio.fixture()
async def opensearch_plugin(opensearch_consumer):
    """Create and open an OpenSearch output plugin targeting the test index."""
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
        index=opensearch_consumer.index,
        verify=False,
    )
    plugin = OpensearchOutputPlugin(config=config, params={'id': 1})
    await plugin.open()
    yield plugin
    await plugin.close()


# - ClickHouse fixtures --


@pytest_asyncio.fixture()
async def clickhouse_consumer(clickhouse_dsn):
    """Create a ClickHouse consumer with unique table, clean up after."""
    from tests.integration.backends.clickhouse import ClickHouseConsumer

    host, port = clickhouse_dsn
    consumer = ClickHouseConsumer(host=host, port=port)
    await consumer.setup()
    yield consumer
    await consumer.teardown()


@pytest_asyncio.fixture()
async def clickhouse_plugin(clickhouse_consumer):
    """Create and open a ClickHouse output plugin targeting the test table."""
    from eventum.plugins.output.plugins.clickhouse.config import (
        ClickhouseOutputPluginConfig,
    )
    from eventum.plugins.output.plugins.clickhouse.plugin import (
        ClickhouseOutputPlugin,
    )

    config = ClickhouseOutputPluginConfig(
        host=CLICKHOUSE_HOST,
        port=CLICKHOUSE_PORT,
        database=clickhouse_consumer.database,
        table=clickhouse_consumer.table,
    )
    plugin = ClickhouseOutputPlugin(config=config, params={'id': 1})
    await plugin.open()
    yield plugin
    await plugin.close()


# - Kafka fixtures --


@pytest_asyncio.fixture()
async def kafka_consumer(kafka_bootstrap):
    """Create a Kafka consumer with unique topic."""
    from tests.integration.backends.kafka import KafkaConsumer

    consumer = KafkaConsumer(bootstrap_servers=kafka_bootstrap)
    await consumer.setup()
    yield consumer
    await consumer.teardown()


@pytest_asyncio.fixture()
async def kafka_plugin(kafka_consumer):
    """Create and open a Kafka output plugin targeting the test topic."""
    from eventum.plugins.output.plugins.kafka.config import (
        KafkaOutputPluginConfig,
    )
    from eventum.plugins.output.plugins.kafka.plugin import KafkaOutputPlugin

    config = KafkaOutputPluginConfig(
        bootstrap_servers=[KAFKA_BOOTSTRAP],
        topic=kafka_consumer.topic,
    )
    plugin = KafkaOutputPlugin(config=config, params={'id': 1})
    await plugin.open()
    yield plugin
    await plugin.close()
