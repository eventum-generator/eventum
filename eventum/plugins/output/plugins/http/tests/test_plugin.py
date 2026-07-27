import re
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import HttpUrl
from pytest_httpx import HTTPXMock

from eventum.plugins.output.fields import Format, JsonFormatterConfig
from eventum.plugins.output.plugins.http.config import HttpOutputPluginConfig
from eventum.plugins.output.plugins.http.plugin import HttpOutputPlugin

_BASE_PATH = Path('/generators/demo')
_SSL_CONTEXT_FACTORY = (
    'eventum.plugins.output.plugins.http.plugin.create_ssl_context'
)


@pytest.fixture
def tls_config():
    return HttpOutputPluginConfig(
        url='https://localhost:8000/endpoint',  # type: ignore[arg-type]
        verify=True,
        ca_cert='certs/ca.pem',  # type: ignore[arg-type]
        client_cert='certs/client.pem',  # type: ignore[arg-type]
        client_cert_key='certs/client-key.pem',  # type: ignore[arg-type]
    )


@pytest.mark.asyncio
async def test_plugin_write(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        method='POST',
        url=re.compile(r'http://localhost:8000/.*'),
        status_code=201,
        text='Ok.',
    )

    config = HttpOutputPluginConfig(
        url=HttpUrl('http://localhost:8000/endpoint'),  # type: ignore
        headers={'Content-Type': 'application/json'},
        formatter=JsonFormatterConfig(format=Format.JSON, indent=0),
    )
    plugin = HttpOutputPlugin(config=config, params={'id': 1})

    await plugin.open()

    written = await plugin.write(
        events=['{"@timestamp": "2024-01-01T00:00:00.000Z", "value": 1}']
    )
    await plugin.close()

    requests = httpx_mock.get_requests()
    assert len(requests) == 1

    rq = requests[0]
    assert rq.method == 'POST'
    assert str(rq.url) == 'http://localhost:8000/endpoint'
    assert rq.read().decode() == (
        '{"@timestamp": "2024-01-01T00:00:00.000Z", "value": 1}'
    )
    assert written == 1


@pytest.mark.asyncio
async def test_plugin_wrong_code(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        method='POST',
        url=re.compile(r'http://localhost:8000/.*'),
        status_code=200,
        text='Ok.',
    )

    config = HttpOutputPluginConfig(
        url=HttpUrl('http://localhost:8000/endpoint'),  # type: ignore
        headers={'Content-Type': 'application/json'},
        formatter=JsonFormatterConfig(format=Format.JSON, indent=0),
    )
    plugin = HttpOutputPlugin(config=config, params={'id': 1})

    await plugin.open()

    written = await plugin.write(
        events=['{"@timestamp": "2024-01-01T00:00:00.000Z", "value": 1}']
    )
    await plugin.close()

    requests = httpx_mock.get_requests()
    assert len(requests) == 1

    rq = requests[0]
    assert rq.method == 'POST'
    assert str(rq.url) == 'http://localhost:8000/endpoint'
    assert rq.read().decode() == (
        '{"@timestamp": "2024-01-01T00:00:00.000Z", "value": 1}'
    )
    assert written == 0


def test_plugin_certificate_paths_resolved(tls_config):
    with patch(_SSL_CONTEXT_FACTORY) as create_context:
        HttpOutputPlugin(
            config=tls_config,
            params={'id': 1, 'base_path': _BASE_PATH},
        )

    options = create_context.call_args.kwargs
    assert options['verify'] is True
    assert options['ca_cert'] == _BASE_PATH / 'certs/ca.pem'
    assert options['client_cert'] == _BASE_PATH / 'certs/client.pem'
    assert options['client_key'] == _BASE_PATH / 'certs/client-key.pem'
