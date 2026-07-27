import re
from pathlib import Path
from unittest.mock import patch

import pytest
from pytest_httpx import HTTPXMock

from eventum.plugins.output.plugins.opensearch.config import (
    OpensearchOutputPluginConfig,
)
from eventum.plugins.output.plugins.opensearch.plugin import (
    OpensearchOutputPlugin,
)

pytest_plugins = ('pytest_asyncio',)

_BASE_PATH = Path('/generators/demo')
_SSL_CONTEXT_FACTORY = (
    'eventum.plugins.output.plugins.opensearch.plugin.create_ssl_context'
)


@pytest.fixture
def config():
    return OpensearchOutputPluginConfig(
        hosts=['https://localhost:9200'],  # type: ignore[arg-type]
        username='admin',
        password='pass',
        index='test_index',
        verify=False,
    )


@pytest.fixture
def tls_config():
    return OpensearchOutputPluginConfig(
        hosts=['https://localhost:9200'],  # type: ignore[arg-type]
        username='admin',
        password='pass',
        index='test_index',
        verify=True,
        ca_cert='certs/ca.pem',  # type: ignore[arg-type]
        client_cert='certs/client.pem',  # type: ignore[arg-type]
        client_cert_key='certs/client-key.pem',  # type: ignore[arg-type]
    )


@pytest.fixture
def write_response():
    return {
        '_index': 'test_index',
        '_id': 'pIQetY8B-vfSDQ_FAHhq',
        '_version': 1,
        'result': 'created',
        '_shards': {'total': 1, 'successful': 1, 'failed': 0},
        '_seq_no': 0,
        '_primary_term': 1,
    }


@pytest.fixture
def write_many_response():
    return {
        'took': 53,
        'errors': False,
        'items': [
            {
                'index': {
                    '_index': 'test_index',
                    '_id': 'QYQmtY8B-vfSDQ_Fw4u9',
                    '_version': 1,
                    'result': 'created',
                    '_shards': {'total': 1, 'successful': 1, 'failed': 0},
                    '_seq_no': 0,
                    '_primary_term': 17,
                    'status': 201,
                }
            }
        ],
    }


@pytest.mark.asyncio
async def test_opensearch_write(httpx_mock: HTTPXMock, config, write_response):
    httpx_mock.add_response(
        method='POST',
        url=re.compile(r'https://localhost:9200/.*'),
        status_code=201,
        json=write_response,
    )

    plugin = OpensearchOutputPlugin(config=config, params={'id': 1})
    await plugin.open()

    written = await plugin.write(
        events=['{"@timestamp": "2024-01-01T00:00:00.000Z", "value": 1}']
    )
    await plugin.close()

    requests = httpx_mock.get_requests()
    assert len(requests) == 1

    rq = requests[0]
    assert rq.method == 'POST'
    assert str(rq.url) == 'https://localhost:9200/test_index/_doc'
    assert rq.read().decode() == (
        '{"@timestamp": "2024-01-01T00:00:00.000Z", "value": 1}'
    )
    assert written == 1


@pytest.mark.asyncio
async def test_opensearch_write_many(
    httpx_mock: HTTPXMock, config, write_many_response
):
    httpx_mock.add_response(
        method='POST',
        url=re.compile(r'https://localhost:9200/.*'),
        status_code=200,
        json=write_many_response,
    )

    plugin = OpensearchOutputPlugin(config=config, params={'id': 1})
    await plugin.open()

    written = await plugin.write(
        [
            '{"@timestamp": "2024-01-01T00:00:00.000Z", "value": 1}',
            '{"@timestamp": "2024-01-01T00:00:01.000Z", "value": 2}',
        ]
    )
    await plugin.close()

    requests = httpx_mock.get_requests()
    assert len(requests) == 1

    rq = requests[0]
    assert rq.method == 'POST'
    assert str(rq.url) == 'https://localhost:9200/_bulk'
    assert rq.read().decode() == (
        '{"index": {"_index": "test_index"}}\n'
        '{"@timestamp": "2024-01-01T00:00:00.000Z", "value": 1}\n'
        '{"index": {"_index": "test_index"}}\n'
        '{"@timestamp": "2024-01-01T00:00:01.000Z", "value": 2}\n'
    )
    assert written == 2


@pytest.mark.asyncio
@pytest.mark.httpx_mock(assert_all_responses_were_requested=False)
async def test_opensearch_invalid_data(
    httpx_mock: HTTPXMock, config, write_response
):
    httpx_mock.add_response(
        method='POST',
        url=re.compile(r'https://localhost:9200/.*'),
        status_code=201,
        json=write_response,
    )

    plugin = OpensearchOutputPlugin(config=config, params={'id': 1})
    await plugin.open()

    written = await plugin.write(
        ['{"@timestamp": "2024-01-01T00:00:00.000Z", "val CORRUPTED...']
    )

    await plugin.close()

    requests = httpx_mock.get_requests()
    assert len(requests) == 0

    assert written == 0


@pytest.mark.asyncio
async def test_opensearch_write_many_partially_corrupted(
    httpx_mock: HTTPXMock, config, write_response
):
    httpx_mock.add_response(
        method='POST',
        url=re.compile(r'https://localhost:9200/.*'),
        status_code=201,
        json=write_response,
    )

    plugin = OpensearchOutputPlugin(config=config, params={'id': 1})
    await plugin.open()

    written = await plugin.write(
        [
            '{"@timestamp": "2024-01-01T00:00:00.000Z", "value": 1}',
            '{"@timestamp": "2024-01-01T00:00:00.000Z", "val CORRUPTED...',
        ]
    )
    await plugin.close()

    requests = httpx_mock.get_requests()
    assert len(requests) == 1

    rq = requests[0]
    assert rq.method == 'POST'
    assert str(rq.url) == 'https://localhost:9200/test_index/_doc'
    assert rq.read().decode() == (
        '{"@timestamp": "2024-01-01T00:00:00.000Z", "value": 1}'
    )
    assert written == 1


def test_opensearch_certificate_paths_resolved(tls_config):
    with patch(_SSL_CONTEXT_FACTORY) as create_context:
        OpensearchOutputPlugin(
            config=tls_config,
            params={'id': 1, 'base_path': _BASE_PATH},
        )

    options = create_context.call_args.kwargs
    assert options['verify'] is True
    assert options['ca_cert'] == _BASE_PATH / 'certs/ca.pem'
    assert options['client_cert'] == _BASE_PATH / 'certs/client.pem'
    assert options['client_key'] == _BASE_PATH / 'certs/client-key.pem'
