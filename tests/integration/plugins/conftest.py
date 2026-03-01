"""Plugin-level fixtures for integration tests.

Provides per-test plugin and consumer instances with automatic
setup/teardown of backend resources (indices, tables, topics, servers).
"""

import pytest
import pytest_asyncio

from tests.integration.conftest import (
    CLICKHOUSE_HOST,
    CLICKHOUSE_PORT,
    KAFKA_BOOTSTRAP,
    OPENSEARCH_URL,
)

# -- OpenSearch fixtures --


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


# -- ClickHouse fixtures --


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


# -- Kafka fixtures --


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


# -- TCP fixtures --


@pytest_asyncio.fixture()
async def tcp_consumer():
    """Start an in-process TCP echo server."""
    from tests.integration.backends.tcp import TcpConsumer

    consumer = TcpConsumer(host='127.0.0.1', port=0)
    await consumer.setup()
    yield consumer
    await consumer.teardown()


@pytest_asyncio.fixture()
async def tcp_plugin(tcp_consumer):
    """Create and open a TCP output plugin targeting the test server."""
    from eventum.plugins.output.plugins.tcp.config import TcpOutputPluginConfig
    from eventum.plugins.output.plugins.tcp.plugin import TcpOutputPlugin

    config = TcpOutputPluginConfig(
        host=tcp_consumer.host,
        port=tcp_consumer.port,
    )
    plugin = TcpOutputPlugin(config=config, params={'id': 1})
    await plugin.open()
    yield plugin
    await plugin.close()
