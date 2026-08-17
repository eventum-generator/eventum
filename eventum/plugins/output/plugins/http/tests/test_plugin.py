import asyncio
import json
import re
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import httpx
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
_CLIENT_FACTORY = 'eventum.plugins.output.plugins.http.plugin.create_client'

_ENDPOINT = 'http://localhost:8000/endpoint'
_CONCURRENCY = 4
_EVENTS_COUNT = 20
_SERVER_ERRORS_COUNT = 3
_UNAVAILABLE_ERRORS_COUNT = 1


def _numbered_events(count: int) -> list[str]:
    """Build events holding their own ordinal number."""
    return [f'{{"value": {number}}}' for number in range(count)]


def _config(**kwargs: Any) -> HttpOutputPluginConfig:
    """Build config sending each event as a separate request."""
    return HttpOutputPluginConfig(
        url=HttpUrl(_ENDPOINT),  # type: ignore[call-arg]
        formatter=JsonFormatterConfig(format=Format.JSON, indent=0),
        **kwargs,
    )


@pytest.mark.asyncio
async def test_plugin_bounds_concurrent_requests(httpx_mock: HTTPXMock):
    in_flight = 0
    peak_in_flight = 0

    async def respond(_request: httpx.Request) -> httpx.Response:
        nonlocal in_flight, peak_in_flight

        in_flight += 1
        peak_in_flight = max(peak_in_flight, in_flight)
        await asyncio.sleep(0.01)
        in_flight -= 1

        return httpx.Response(status_code=201)

    httpx_mock.add_callback(
        respond,
        method='POST',
        url=_ENDPOINT,
        is_reusable=True,
    )

    plugin = HttpOutputPlugin(
        config=_config(concurrency=_CONCURRENCY),
        params={'id': 1},
    )

    await plugin.open()
    written = await plugin.write(events=_numbered_events(_EVENTS_COUNT))
    await plugin.close()

    assert len(httpx_mock.get_requests()) == _EVENTS_COUNT
    assert written == _EVENTS_COUNT
    assert peak_in_flight == _CONCURRENCY


@pytest.mark.asyncio
async def test_plugin_sizes_connection_pool_by_concurrency():
    plugin = HttpOutputPlugin(
        config=_config(concurrency=_CONCURRENCY),
        params={'id': 1},
    )

    with patch(_CLIENT_FACTORY) as create_client:
        await plugin.open()

    assert create_client.call_args.kwargs['max_connections'] == _CONCURRENCY


@pytest.mark.asyncio
async def test_plugin_reports_failures_grouped_by_status(
    httpx_mock: HTTPXMock,
):
    def respond(request: httpx.Request) -> httpx.Response:
        value = json.loads(request.read())['value']

        if value < _SERVER_ERRORS_COUNT:
            return httpx.Response(status_code=500, text='Storage is down.')

        if value < _SERVER_ERRORS_COUNT + _UNAVAILABLE_ERRORS_COUNT:
            return httpx.Response(status_code=503, text='Overloaded.')

        return httpx.Response(status_code=201)

    httpx_mock.add_callback(
        respond,
        method='POST',
        url=_ENDPOINT,
        is_reusable=True,
    )

    events_count = _SERVER_ERRORS_COUNT + _UNAVAILABLE_ERRORS_COUNT + 1
    failed_count = events_count - 1

    plugin = HttpOutputPlugin(config=_config(), params={'id': 1})
    logger = AsyncMock()

    with patch.object(plugin, '_logger', logger):
        await plugin.open()
        written = await plugin.write(events=_numbered_events(events_count))
        await plugin.close()

    assert written == 1
    assert plugin.write_failed == failed_count

    reported = {
        call.kwargs['http_status']: call.kwargs['count']
        for call in logger.aerror.call_args_list
    }
    assert reported == {
        500: _SERVER_ERRORS_COUNT,
        503: _UNAVAILABLE_ERRORS_COUNT,
    }


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
    assert plugin.write_failed == 1


@pytest.mark.asyncio
async def test_plugin_counts_rejected_events(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        method='POST',
        url=re.compile(r'http://localhost:8000/.*'),
        status_code=500,
        text='Upstream storage is unavailable.',
        is_reusable=True,
    )

    config = HttpOutputPluginConfig(
        url=HttpUrl('http://localhost:8000/endpoint'),  # type: ignore
        headers={'Content-Type': 'application/json'},
        formatter=JsonFormatterConfig(format=Format.JSON, indent=0),
    )
    plugin = HttpOutputPlugin(config=config, params={'id': 1})

    await plugin.open()

    written = await plugin.write(
        events=[
            '{"@timestamp": "2024-01-01T00:00:00.000Z", "value": 1}',
            '{"@timestamp": "2024-01-01T00:00:01.000Z", "value": 2}',
            '{"@timestamp": "2024-01-01T00:00:02.000Z", "value": 3}',
        ]
    )
    await plugin.close()

    assert len(httpx_mock.get_requests()) == 3
    assert written == 0
    assert plugin.written == 0
    assert plugin.write_failed == 3


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
