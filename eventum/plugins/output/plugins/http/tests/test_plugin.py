import asyncio
import json
import re
from base64 import b64encode
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from pydantic import HttpUrl
from pytest_httpx import HTTPXMock

from eventum.plugins.output.exceptions import PluginOpenError
from eventum.plugins.output.fields import Format, JsonFormatterConfig
from eventum.plugins.output.http_auth import authenticators
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


_TOKEN_URL = 'https://login.example.com/token'  # noqa: S105
_UNAUTHORIZED = 401
_BAD_REQUEST = 400
_RETRIED_REQUESTS = 2
_BATCH_SIZE = 10


def _oauth2_auth() -> dict[str, Any]:
    """Build an auth section pointing at the mocked token endpoint."""
    return {
        'type': 'oauth2_client_credentials',
        'token_url': _TOKEN_URL,
        'client_id': 'id',
        'client_secret': 'secret',
    }


def _token_requests(httpx_mock: HTTPXMock) -> list[httpx.Request]:
    """Return the requests sent to the token endpoint."""
    return [
        request
        for request in httpx_mock.get_requests()
        if str(request.url) == _TOKEN_URL
    ]


@pytest.mark.asyncio
async def test_plugin_sends_basic_credentials(httpx_mock: HTTPXMock):
    httpx_mock.add_response(method='POST', url=_ENDPOINT, status_code=201)

    plugin = HttpOutputPlugin(
        config=_config(
            auth={'type': 'basic', 'username': 'user', 'password': 'pass'},
        ),
        params={'id': 1},
    )

    await plugin.open()
    await plugin.write(events=_numbered_events(1))
    await plugin.close()

    expected = b64encode(b'user:pass').decode()
    request = httpx_mock.get_requests()[0]
    assert request.headers['Authorization'] == f'Basic {expected}'


@pytest.mark.asyncio
async def test_plugin_sends_static_bearer_token(httpx_mock: HTTPXMock):
    httpx_mock.add_response(method='POST', url=_ENDPOINT, status_code=201)

    plugin = HttpOutputPlugin(
        config=_config(auth={'type': 'bearer', 'token': 'abc'}),
        params={'id': 1},
    )

    await plugin.open()
    await plugin.write(events=_numbered_events(1))
    await plugin.close()

    request = httpx_mock.get_requests()[0]
    assert request.headers['Authorization'] == 'Bearer abc'


@pytest.mark.asyncio
async def test_plugin_takes_token_once_for_a_batch(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        method='POST',
        url=_TOKEN_URL,
        json={'access_token': 'tok', 'expires_in': 3600},
    )
    httpx_mock.add_response(
        method='POST',
        url=_ENDPOINT,
        status_code=201,
        is_reusable=True,
    )

    plugin = HttpOutputPlugin(
        config=_config(auth=_oauth2_auth()),
        params={'id': 1},
    )

    await plugin.open()
    written = await plugin.write(events=_numbered_events(_BATCH_SIZE))
    await plugin.close()

    assert written == _BATCH_SIZE
    assert len(_token_requests(httpx_mock)) == 1


@pytest.mark.asyncio
async def test_plugin_refreshes_token_on_unauthorized(
    httpx_mock: HTTPXMock,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        authenticators,
        'MIN_REJECTED_TOKEN_AGE_SECONDS',
        0.0,
    )
    tokens = iter(['stale', 'fresh'])
    httpx_mock.add_callback(
        lambda _request: httpx.Response(
            status_code=200,
            json={'access_token': next(tokens), 'expires_in': 3600},
        ),
        method='POST',
        url=_TOKEN_URL,
        is_reusable=True,
    )
    httpx_mock.add_callback(
        lambda request: httpx.Response(
            status_code=(
                201
                if request.headers['Authorization'] == 'Bearer fresh'
                else _UNAUTHORIZED
            ),
        ),
        method='POST',
        url=_ENDPOINT,
        is_reusable=True,
    )

    plugin = HttpOutputPlugin(
        config=_config(auth=_oauth2_auth()),
        params={'id': 1},
    )

    await plugin.open()
    written = await plugin.write(events=_numbered_events(1))
    await plugin.close()

    assert written == 1
    assert plugin.write_failed == 0


@pytest.mark.asyncio
async def test_plugin_fails_after_one_refresh(
    httpx_mock: HTTPXMock,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        authenticators,
        'MIN_REJECTED_TOKEN_AGE_SECONDS',
        0.0,
    )
    httpx_mock.add_response(
        method='POST',
        url=_TOKEN_URL,
        json={'access_token': 'tok', 'expires_in': 3600},
        is_reusable=True,
    )
    httpx_mock.add_response(
        method='POST',
        url=_ENDPOINT,
        status_code=_UNAUTHORIZED,
        text='Unauthorized.',
        is_reusable=True,
    )

    plugin = HttpOutputPlugin(
        config=_config(auth=_oauth2_auth()),
        params={'id': 1},
    )

    await plugin.open()
    written = await plugin.write(events=_numbered_events(1))
    await plugin.close()

    endpoint_requests = [
        request
        for request in httpx_mock.get_requests()
        if str(request.url) == _ENDPOINT
    ]
    assert written == 0
    assert plugin.write_failed == 1
    assert len(endpoint_requests) == _RETRIED_REQUESTS


@pytest.mark.asyncio
async def test_plugin_does_not_retry_a_fresh_rejected_token(
    httpx_mock: HTTPXMock,
):
    httpx_mock.add_response(
        method='POST',
        url=_TOKEN_URL,
        json={'access_token': 'tok', 'expires_in': 3600},
        is_reusable=True,
    )
    httpx_mock.add_response(
        method='POST',
        url=_ENDPOINT,
        status_code=_UNAUTHORIZED,
        text='Unauthorized.',
        is_reusable=True,
    )

    plugin = HttpOutputPlugin(
        config=_config(auth=_oauth2_auth()),
        params={'id': 1},
    )

    await plugin.open()
    await plugin.write(events=_numbered_events(_RETRIED_REQUESTS))
    await plugin.close()

    endpoint_requests = [
        request
        for request in httpx_mock.get_requests()
        if str(request.url) == _ENDPOINT
    ]
    # neither event is retried, and the token they were rejected with
    # stays in place instead of being taken again for the second one
    assert len(endpoint_requests) == _RETRIED_REQUESTS
    assert len(_token_requests(httpx_mock)) == 1


@pytest.mark.asyncio
async def test_plugin_fails_to_open_without_a_token(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        method='POST',
        url=_TOKEN_URL,
        status_code=_BAD_REQUEST,
        text='invalid_client',
    )

    plugin = HttpOutputPlugin(
        config=_config(auth=_oauth2_auth()),
        params={'id': 1},
    )

    with pytest.raises(PluginOpenError) as info:
        await plugin.open()

    assert info.value.context['http_status'] == _BAD_REQUEST


@pytest.mark.asyncio
async def test_plugin_keeps_configured_headers_off_the_token_request(
    httpx_mock: HTTPXMock,
):
    httpx_mock.add_response(
        method='POST',
        url=_TOKEN_URL,
        json={'access_token': 'tok', 'expires_in': 3600},
    )
    httpx_mock.add_response(
        method='POST',
        url=_ENDPOINT,
        status_code=201,
        is_reusable=True,
    )

    plugin = HttpOutputPlugin(
        config=_config(
            headers={
                'Content-Type': 'application/json',
                'X-API-Key': 'ingest-secret',
            },
            auth=_oauth2_auth(),
        ),
        params={'id': 1},
    )

    await plugin.open()
    await plugin.write(events=_numbered_events(1))
    await plugin.close()

    token_request = _token_requests(httpx_mock)[0]
    data_request = next(
        request
        for request in httpx_mock.get_requests()
        if str(request.url) == _ENDPOINT
    )

    # the credential of the endpoint has no business reaching the
    # host the token comes from, and the form encoding of the grant
    # must not be overridden by the content type of the events
    assert 'x-api-key' not in token_request.headers
    assert token_request.headers['Content-Type'] == (
        'application/x-www-form-urlencoded'
    )
    assert data_request.headers['X-API-Key'] == 'ingest-secret'
    assert data_request.headers['Content-Type'] == 'application/json'


@pytest.mark.asyncio
async def test_plugin_leaves_configured_headers_untouched(
    httpx_mock: HTTPXMock,
):
    httpx_mock.add_response(method='POST', url=_ENDPOINT, status_code=201)

    config = _config(
        headers={'Content-Type': 'application/json'},
        auth={'type': 'bearer', 'token': 'abc'},
    )
    plugin = HttpOutputPlugin(config=config, params={'id': 1})

    await plugin.open()
    await plugin.write(events=_numbered_events(1))
    await plugin.close()

    # the credential is merged into the headers of every request, and
    # the configuration those are read from is shared with the API
    assert config.headers == {'Content-Type': 'application/json'}


@pytest.mark.asyncio
async def test_plugin_closes_the_client_when_it_cannot_authenticate(
    httpx_mock: HTTPXMock,
):
    httpx_mock.add_response(
        method='POST',
        url=_TOKEN_URL,
        status_code=_BAD_REQUEST,
        text='invalid_client',
    )

    plugin = HttpOutputPlugin(
        config=_config(auth=_oauth2_auth()),
        params={'id': 1},
    )

    with pytest.raises(PluginOpenError):
        await plugin.open()

    # `close` never reaches a plugin that failed to open, so the
    # client has to be released here or it is leaked
    assert plugin._client.is_closed  # noqa: SLF001


@pytest.mark.asyncio
async def test_plugin_counts_events_it_cannot_authenticate(
    httpx_mock: HTTPXMock,
):
    answers = iter(
        [
            httpx.Response(
                status_code=200,
                json={'access_token': 'tok', 'expires_in': 0.001},
            ),
        ],
    )
    httpx_mock.add_callback(
        lambda _request: next(
            answers,
            httpx.Response(status_code=_BAD_REQUEST, text='invalid_client'),
        ),
        method='POST',
        url=_TOKEN_URL,
        is_reusable=True,
    )

    plugin = HttpOutputPlugin(
        config=_config(auth=_oauth2_auth()),
        params={'id': 1},
    )

    await plugin.open()
    await asyncio.sleep(0.01)
    written = await plugin.write(events=_numbered_events(1))
    await plugin.close()

    assert written == 0
    assert plugin.write_failed == 1


@pytest.mark.asyncio
async def test_plugin_counts_a_rejection_without_credentials(
    httpx_mock: HTTPXMock,
):
    httpx_mock.add_response(
        method='POST',
        url=_ENDPOINT,
        status_code=_UNAUTHORIZED,
        text='Unauthorized.',
    )

    plugin = HttpOutputPlugin(config=_config(), params={'id': 1})

    await plugin.open()
    written = await plugin.write(events=_numbered_events(1))
    await plugin.close()

    # nothing can be renewed without an auth section, so the event
    # simply fails instead of asking an authenticator that is absent
    assert written == 0
    assert plugin.write_failed == 1
    assert len(httpx_mock.get_requests()) == 1


@pytest.mark.asyncio
async def test_plugin_takes_the_expected_status_over_a_rejection(
    httpx_mock: HTTPXMock,
):
    httpx_mock.add_response(
        method='POST',
        url=_TOKEN_URL,
        json={'access_token': 'tok', 'expires_in': 3600},
    )
    httpx_mock.add_response(
        method='POST',
        url=_ENDPOINT,
        status_code=_UNAUTHORIZED,
    )

    plugin = HttpOutputPlugin(
        config=_config(auth=_oauth2_auth(), success_code=_UNAUTHORIZED),
        params={'id': 1},
    )

    await plugin.open()
    written = await plugin.write(events=_numbered_events(1))
    await plugin.close()

    # an endpoint answering 401 on success is answering as configured,
    # so the credential is not questioned
    assert written == 1
    assert len(_token_requests(httpx_mock)) == 1


@pytest.mark.asyncio
async def test_plugin_closes_the_client_when_the_authenticator_fails():
    plugin = HttpOutputPlugin(
        config=_config(auth={'type': 'bearer', 'token': 'abc'}),
        params={'id': 1},
    )

    factory = 'eventum.plugins.output.plugins.http.plugin.create_authenticator'
    with (
        patch(factory, side_effect=ValueError('unknown')),
        pytest.raises(ValueError, match='unknown'),
    ):
        await plugin.open()

    # whatever the failure was, the client acquired a moment earlier
    # is released rather than left behind
    assert plugin._client.is_closed  # noqa: SLF001
