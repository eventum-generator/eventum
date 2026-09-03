"""Tests for http authenticators."""

import asyncio
import math
from typing import Any, Literal, override
from urllib.parse import parse_qs

import httpx
import pytest
from pytest_httpx import HTTPXMock

from eventum.plugins.output.http_auth import authenticators
from eventum.plugins.output.http_auth.authenticators import (
    AcquiredToken,
    AuthenticationError,
    BasicHttpAuthenticator,
    BearerHttpAuthenticator,
    HttpAuthenticator,
    HttpAuthenticatorParams,
    OAuth2ClientCredentialsHttpAuthenticator,
    TokenHttpAuthenticator,
    create_authenticator,
)
from eventum.plugins.output.http_auth.config import (
    AuthType,
    BaseHttpAuthConfig,
    BasicHttpAuthConfig,
    BearerHttpAuthConfig,
    ClientAuthMethod,
    OAuth2ClientCredentialsHttpAuthConfig,
)


@pytest.fixture
def client() -> HttpAuthenticatorParams:
    """Return the params the authenticators are given."""
    return HttpAuthenticatorParams(client=httpx.AsyncClient())


def _httpx_basic_header(username: str, password: str) -> str:
    """Return the header httpx sends for the same credentials."""
    flow = httpx.BasicAuth(username, password).auth_flow(
        httpx.Request('GET', 'http://localhost'),
    )
    return next(flow).headers['Authorization']


@pytest.mark.asyncio
async def test_basic_header_matches_httpx(
    client: HttpAuthenticatorParams,
) -> None:
    """Basic credentials are encoded the way httpx encodes them."""
    authenticator = create_authenticator(
        config=BasicHttpAuthConfig(
            type=AuthType.BASIC,
            username='user',
            password='pass',  # noqa: S106
        ),
        params=client,
    )

    await authenticator.open()
    headers = await authenticator.headers()

    assert isinstance(authenticator, BasicHttpAuthenticator)
    assert headers['Authorization'] == _httpx_basic_header('user', 'pass')


@pytest.mark.asyncio
async def test_basic_without_password_uses_empty_one(
    client: HttpAuthenticatorParams,
) -> None:
    """A username alone authenticates with an empty password."""
    authenticator = create_authenticator(
        config=BasicHttpAuthConfig(type=AuthType.BASIC, username='user'),
        params=client,
    )

    headers = await authenticator.headers()

    assert headers['Authorization'] == _httpx_basic_header('user', '')


@pytest.mark.asyncio
async def test_bearer_sets_authorization_header(
    client: HttpAuthenticatorParams,
) -> None:
    """A static token is sent as a bearer credential."""
    authenticator = create_authenticator(
        config=BearerHttpAuthConfig(type=AuthType.BEARER, token='abc'),  # noqa: S106
        params=client,
    )

    await authenticator.open()
    headers = await authenticator.headers()

    assert isinstance(authenticator, BearerHttpAuthenticator)
    assert headers['Authorization'] == 'Bearer abc'


@pytest.mark.asyncio
async def test_static_authenticators_do_not_retry(
    client: HttpAuthenticatorParams,
) -> None:
    """A static credential cannot be renewed, so no retry is asked."""
    authenticator = create_authenticator(
        config=BearerHttpAuthConfig(type=AuthType.BEARER, token='abc'),  # noqa: S106
        params=client,
    )

    assert await authenticator.handle_unauthorized({}) is False


def test_registry_resolves_every_auth_type() -> None:
    """Every declared type of authentication has an implementation."""
    for auth_type in AuthType:
        assert HttpAuthenticator.get_authenticator(auth_type) is not None


def test_registry_rejects_duplicate_registration() -> None:
    """Two implementations cannot claim one type of authentication."""
    with pytest.raises(ValueError, match='already registered'):

        class _Duplicate(  # type: ignore[misc]
            HttpAuthenticator[BearerHttpAuthConfig],
            auth_type=AuthType.BEARER,
        ):
            async def headers(self) -> dict[str, str]:
                return {}


_TOKEN_URL = 'https://login.example.com/token'  # noqa: S105
_REFRESHED_TOKEN_REQUESTS = 3
_REPLACED_TOKEN_REQUESTS = 2
_BAD_REQUEST = 400
_LIFE_MINUS_LEEWAY = 70.0
_HALVED_LIFE = 10.0


def _oauth2_config(**kwargs: Any) -> OAuth2ClientCredentialsHttpAuthConfig:
    """Build an oauth2 config pointing at the mocked token endpoint."""
    return OAuth2ClientCredentialsHttpAuthConfig(
        type=AuthType.OAUTH2_CLIENT_CREDENTIALS,
        token_url=_TOKEN_URL,  # type: ignore[arg-type]
        client_id='id',
        client_secret='secret',  # noqa: S106
        **kwargs,
    )


@pytest.mark.asyncio
async def test_oauth2_sends_client_credentials_grant(
    client: HttpAuthenticatorParams,
    httpx_mock: HTTPXMock,
) -> None:
    """Every parameter of the grant lands in the form of the request."""
    httpx_mock.add_response(
        method='POST',
        url=_TOKEN_URL,
        json={'access_token': 'tok', 'expires_in': 3600},
    )

    authenticator = create_authenticator(
        config=_oauth2_config(
            scopes=['https://monitor.azure.com//.default'],
            audience='api://events',
            resource='https://monitor.azure.com/',
            extra_params={'tenant': 'contoso'},
        ),
        params=client,
    )
    await authenticator.open()

    request = httpx_mock.get_requests()[0]
    body = dict(
        pair.split('=', 1) for pair in request.read().decode().split('&')
    )

    assert request.headers['Content-Type'] == (
        'application/x-www-form-urlencoded'
    )
    assert body['grant_type'] == 'client_credentials'
    assert body['client_id'] == 'id'
    assert body['client_secret'] == 'secret'  # noqa: S105
    assert body['scope'] == 'https%3A%2F%2Fmonitor.azure.com%2F%2F.default'
    assert body['audience'] == 'api%3A%2F%2Fevents'
    assert body['tenant'] == 'contoso'

    # credentials in the body and in the header at once are refused by
    # a server that follows the grant
    assert 'Authorization' not in request.headers
    assert (await authenticator.headers())['Authorization'] == 'Bearer tok'


@pytest.mark.asyncio
async def test_oauth2_basic_client_auth_uses_header(
    client: HttpAuthenticatorParams,
    httpx_mock: HTTPXMock,
) -> None:
    """Client credentials may be presented as a basic header."""
    httpx_mock.add_response(
        method='POST',
        url=_TOKEN_URL,
        json={'access_token': 'tok', 'expires_in': 3600},
    )

    authenticator = create_authenticator(
        config=_oauth2_config(client_auth_method=ClientAuthMethod.BASIC),
        params=client,
    )
    await authenticator.open()

    request = httpx_mock.get_requests()[0]

    assert request.headers['Authorization'] == _httpx_basic_header(
        'id',
        'secret',
    )
    body = request.read().decode()
    assert 'client_secret' not in body
    assert 'client_id' not in body


@pytest.mark.asyncio
async def test_oauth2_caches_token_until_expiry(
    client: HttpAuthenticatorParams,
    httpx_mock: HTTPXMock,
) -> None:
    """A token that is still valid is reused."""
    httpx_mock.add_response(
        method='POST',
        url=_TOKEN_URL,
        json={'access_token': 'tok', 'expires_in': 3600},
    )

    authenticator = create_authenticator(_oauth2_config(), client)
    await authenticator.open()

    for _ in range(5):
        headers = await authenticator.headers()
        assert headers['Authorization'] == 'Bearer tok'

    assert len(httpx_mock.get_requests()) == 1


@pytest.mark.asyncio
async def test_oauth2_refreshes_expired_token(
    client: HttpAuthenticatorParams,
    httpx_mock: HTTPXMock,
) -> None:
    """An expired token is replaced before the request is sent."""
    httpx_mock.add_response(
        method='POST',
        url=_TOKEN_URL,
        json={'access_token': 'tok', 'expires_in': 0.001},
        is_reusable=True,
    )

    authenticator = create_authenticator(_oauth2_config(), client)
    await authenticator.open()
    await asyncio.sleep(0.01)
    await authenticator.headers()
    await asyncio.sleep(0.01)
    await authenticator.headers()

    assert len(httpx_mock.get_requests()) == _REFRESHED_TOKEN_REQUESTS


@pytest.mark.asyncio
async def test_oauth2_requests_token_once_for_concurrent_callers(
    client: HttpAuthenticatorParams,
    httpx_mock: HTTPXMock,
) -> None:
    """Callers finding a cold cache wait for one token request."""

    async def respond(_request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(0.01)
        return httpx.Response(
            status_code=200,
            json={'access_token': 'tok', 'expires_in': 3600},
        )

    httpx_mock.add_callback(
        respond,
        method='POST',
        url=_TOKEN_URL,
        is_reusable=True,
    )

    authenticator = create_authenticator(_oauth2_config(), client)
    await asyncio.gather(*[authenticator.headers() for _ in range(20)])

    assert len(httpx_mock.get_requests()) == 1


@pytest.mark.asyncio
async def test_oauth2_throttles_forced_refresh(
    client: HttpAuthenticatorParams,
    httpx_mock: HTTPXMock,
) -> None:
    """A token minted seconds ago is not discarded on a rejection."""
    httpx_mock.add_response(
        method='POST',
        url=_TOKEN_URL,
        json={'access_token': 'tok', 'expires_in': 3600},
        is_reusable=True,
    )

    authenticator = create_authenticator(_oauth2_config(), client)
    await authenticator.open()
    sent = await authenticator.headers()

    assert await authenticator.handle_unauthorized(sent) is False

    # the token is kept, so the next request carries it instead of
    # taking another one
    assert await authenticator.headers() == sent
    assert len(httpx_mock.get_requests()) == 1


@pytest.mark.asyncio
async def test_oauth2_drops_token_when_refresh_is_allowed(
    client: HttpAuthenticatorParams,
    httpx_mock: HTTPXMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An aged token rejected by the server is replaced."""
    httpx_mock.add_response(
        method='POST',
        url=_TOKEN_URL,
        json={'access_token': 'tok', 'expires_in': 3600},
        is_reusable=True,
    )
    monkeypatch.setattr(
        authenticators,
        'MIN_REJECTED_TOKEN_AGE_SECONDS',
        0.0,
    )

    authenticator = create_authenticator(_oauth2_config(), client)
    await authenticator.open()
    sent = await authenticator.headers()

    assert await authenticator.handle_unauthorized(sent) is True

    await authenticator.headers()

    assert len(httpx_mock.get_requests()) == _REPLACED_TOKEN_REQUESTS


@pytest.mark.asyncio
async def test_oauth2_reports_token_endpoint_error(
    client: HttpAuthenticatorParams,
    httpx_mock: HTTPXMock,
) -> None:
    """A refusal of the token endpoint is reported with its answer."""
    httpx_mock.add_response(
        method='POST',
        url=_TOKEN_URL,
        status_code=400,
        text='invalid_client',
    )

    authenticator = create_authenticator(_oauth2_config(), client)

    with pytest.raises(AuthenticationError) as info:
        await authenticator.open()

    assert info.value.context['http_status'] == _BAD_REQUEST
    assert info.value.context['url'] == _TOKEN_URL
    assert info.value.context['reason'] == 'invalid_client'


@pytest.mark.asyncio
async def test_oauth2_hides_payload_of_unexpected_response(
    client: HttpAuthenticatorParams,
    httpx_mock: HTTPXMock,
) -> None:
    """A successful answer without a token never reaches the context."""
    httpx_mock.add_response(
        method='POST',
        url=_TOKEN_URL,
        json={'id_token': 'leaked-secret-value'},
    )

    authenticator = create_authenticator(_oauth2_config(), client)

    with pytest.raises(AuthenticationError) as info:
        await authenticator.open()

    assert 'leaked-secret-value' not in str(info.value.context)


@pytest.mark.asyncio
async def test_oauth2_reports_unreachable_token_endpoint(
    client: HttpAuthenticatorParams,
    httpx_mock: HTTPXMock,
) -> None:
    """An unreachable token endpoint is reported as an error."""
    httpx_mock.add_exception(
        httpx.ConnectError('Connection refused'),
        method='POST',
        url=_TOKEN_URL,
    )

    authenticator = create_authenticator(_oauth2_config(), client)

    with pytest.raises(AuthenticationError) as info:
        await authenticator.open()

    assert info.value.context['url'] == _TOKEN_URL


@pytest.mark.asyncio
async def test_oauth2_retries_a_token_that_was_already_replaced(
    client: HttpAuthenticatorParams,
    httpx_mock: HTTPXMock,
) -> None:
    """A rejection naming a superseded token is worth a retry."""
    httpx_mock.add_response(
        method='POST',
        url=_TOKEN_URL,
        json={'access_token': 'tok', 'expires_in': 3600},
    )

    authenticator = create_authenticator(_oauth2_config(), client)
    await authenticator.open()

    # the request was sent before the token it carried was replaced,
    # so the throttle of a freshly taken token must not hold it back
    stale = {'Authorization': 'Bearer superseded'}

    assert await authenticator.handle_unauthorized(stale) is True

    # the cache is ahead of the rejection, so it is kept as it is
    assert (await authenticator.headers())['Authorization'] == 'Bearer tok'
    assert len(httpx_mock.get_requests()) == 1


@pytest.mark.asyncio
async def test_oauth2_holds_back_from_a_failing_endpoint(
    client: HttpAuthenticatorParams,
    httpx_mock: HTTPXMock,
) -> None:
    """A refusing token endpoint is not asked once per request."""
    httpx_mock.add_response(
        method='POST',
        url=_TOKEN_URL,
        status_code=_BAD_REQUEST,
        text='invalid_client',
        is_reusable=True,
    )

    authenticator = create_authenticator(_oauth2_config(), client)

    for _ in range(5):
        with pytest.raises(AuthenticationError) as info:
            await authenticator.headers()

        assert info.value.context['http_status'] == _BAD_REQUEST

    assert len(httpx_mock.get_requests()) == 1


@pytest.mark.asyncio
async def test_oauth2_asks_again_once_the_interval_passed(
    client: HttpAuthenticatorParams,
    httpx_mock: HTTPXMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The hold on a failing endpoint lasts the interval only."""
    httpx_mock.add_response(
        method='POST',
        url=_TOKEN_URL,
        status_code=_BAD_REQUEST,
        text='invalid_client',
        is_reusable=True,
    )
    monkeypatch.setattr(
        authenticators,
        'FAILED_ACQUISITION_HOLD_SECONDS',
        0.0,
    )

    authenticator = create_authenticator(_oauth2_config(), client)

    for _ in range(_REPLACED_TOKEN_REQUESTS):
        with pytest.raises(AuthenticationError):
            await authenticator.headers()

    assert len(httpx_mock.get_requests()) == _REPLACED_TOKEN_REQUESTS


@pytest.mark.asyncio
async def test_oauth2_renews_ahead_of_the_stated_expiry(
    client: HttpAuthenticatorParams,
    httpx_mock: HTTPXMock,
) -> None:
    """A token is replaced before the endpoint stops accepting it."""
    httpx_mock.add_response(
        method='POST',
        url=_TOKEN_URL,
        json={'access_token': 'tok', 'expires_in': 100},
    )

    authenticator = create_authenticator(_oauth2_config(), client)
    await authenticator.open()

    assert isinstance(authenticator, OAuth2ClientCredentialsHttpAuthenticator)

    # 100 seconds of life, taken 30 seconds early
    lifetime = authenticator._expires_at - authenticator._obtained_at  # noqa: SLF001
    assert lifetime == _LIFE_MINUS_LEEWAY


@pytest.mark.asyncio
async def test_oauth2_halves_a_life_shorter_than_the_leeway(
    client: HttpAuthenticatorParams,
    httpx_mock: HTTPXMock,
) -> None:
    """A short lived token is not born already expired."""
    httpx_mock.add_response(
        method='POST',
        url=_TOKEN_URL,
        json={'access_token': 'tok', 'expires_in': 20},
    )

    authenticator = create_authenticator(_oauth2_config(), client)
    await authenticator.open()

    assert isinstance(authenticator, OAuth2ClientCredentialsHttpAuthenticator)

    # taking 30 seconds off a life of 20 would leave nothing
    lifetime = authenticator._expires_at - authenticator._obtained_at  # noqa: SLF001
    assert lifetime == _HALVED_LIFE


@pytest.mark.parametrize(
    'expires_in',
    [None, 'soon', -1, 0],
)
@pytest.mark.asyncio
async def test_oauth2_holds_a_token_of_unstated_life(
    client: HttpAuthenticatorParams,
    httpx_mock: HTTPXMock,
    expires_in: Any,
) -> None:
    """A life that says nothing usable leaves the token in place."""
    payload: dict[str, Any] = {'access_token': 'tok'}
    if expires_in is not None:
        payload['expires_in'] = expires_in

    httpx_mock.add_response(method='POST', url=_TOKEN_URL, json=payload)

    authenticator = create_authenticator(_oauth2_config(), client)
    await authenticator.open()

    assert isinstance(authenticator, OAuth2ClientCredentialsHttpAuthenticator)
    assert math.isinf(authenticator._expires_at)  # noqa: SLF001


@pytest.mark.asyncio
async def test_oauth2_reports_a_body_that_is_not_json(
    client: HttpAuthenticatorParams,
    httpx_mock: HTTPXMock,
) -> None:
    """A successful answer that is not JSON is reported as an error."""
    httpx_mock.add_response(method='POST', url=_TOKEN_URL, text='<html/>')

    authenticator = create_authenticator(_oauth2_config(), client)

    with pytest.raises(AuthenticationError, match='invalid JSON'):
        await authenticator.open()


@pytest.mark.asyncio
async def test_oauth2_rejects_a_token_outside_ascii(
    client: HttpAuthenticatorParams,
    httpx_mock: HTTPXMock,
) -> None:
    """A token no header can carry is reported once, not per request."""
    httpx_mock.add_response(
        method='POST',
        url=_TOKEN_URL,
        json={'access_token': 'tok\u0435n', 'expires_in': 3600},
    )

    authenticator = create_authenticator(_oauth2_config(), client)

    with pytest.raises(AuthenticationError, match='no header can carry') as e:
        await authenticator.open()

    assert 'tok\u0435n' not in str(e.value.context)


@pytest.mark.asyncio
async def test_oauth2_joins_scopes_with_a_space(
    client: HttpAuthenticatorParams,
    httpx_mock: HTTPXMock,
) -> None:
    """Several scopes travel as one space separated parameter."""
    httpx_mock.add_response(
        method='POST',
        url=_TOKEN_URL,
        json={'access_token': 'tok', 'expires_in': 3600},
    )

    authenticator = create_authenticator(
        config=_oauth2_config(scopes=['openid', 'profile']),
        params=client,
    )
    await authenticator.open()

    body = parse_qs(httpx_mock.get_requests()[0].read().decode())

    assert body['scope'] == ['openid profile']


@pytest.mark.asyncio
async def test_oauth2_sends_the_named_grant_parameters(
    client: HttpAuthenticatorParams,
    httpx_mock: HTTPXMock,
) -> None:
    """Audience, resource and the extra parameters reach the endpoint."""
    httpx_mock.add_response(
        method='POST',
        url=_TOKEN_URL,
        json={'access_token': 'tok', 'expires_in': 3600},
    )

    authenticator = create_authenticator(
        config=_oauth2_config(
            audience='api://events',
            resource='https://monitor.azure.com/',
            extra_params={'tenant': 'contoso'},
        ),
        params=client,
    )
    await authenticator.open()

    body = parse_qs(httpx_mock.get_requests()[0].read().decode())

    assert body['audience'] == ['api://events']
    assert body['resource'] == ['https://monitor.azure.com/']
    assert body['tenant'] == ['contoso']


@pytest.mark.asyncio
async def test_oauth2_holds_a_token_of_a_life_that_is_not_a_number(
    client: HttpAuthenticatorParams,
    httpx_mock: HTTPXMock,
) -> None:
    """A life stated as NaN is no life to compare a clock against."""
    httpx_mock.add_response(
        method='POST',
        url=_TOKEN_URL,
        text='{"access_token": "tok", "expires_in": NaN}',
        headers={'Content-Type': 'application/json'},
    )

    authenticator = create_authenticator(_oauth2_config(), client)
    await authenticator.open()

    for _ in range(3):
        await authenticator.headers()

    assert len(httpx_mock.get_requests()) == 1


@pytest.mark.parametrize('token', ['tok en', 'tok\nen', 'token\n'])
@pytest.mark.asyncio
async def test_oauth2_rejects_a_token_no_header_can_carry(
    client: HttpAuthenticatorParams,
    httpx_mock: HTTPXMock,
    token: str,
) -> None:
    """A token holding a space or a line break is refused."""
    httpx_mock.add_response(
        method='POST',
        url=_TOKEN_URL,
        json={'access_token': token, 'expires_in': 3600},
    )

    authenticator = create_authenticator(_oauth2_config(), client)

    with pytest.raises(AuthenticationError, match='no header can carry'):
        await authenticator.open()


@pytest.mark.asyncio
async def test_oauth2_reports_a_body_that_is_not_an_object(
    client: HttpAuthenticatorParams,
    httpx_mock: HTTPXMock,
) -> None:
    """JSON that is not an object carries no token either."""
    httpx_mock.add_response(method='POST', url=_TOKEN_URL, json=[1, 2])

    authenticator = create_authenticator(_oauth2_config(), client)

    with pytest.raises(AuthenticationError, match='no access token'):
        await authenticator.open()


@pytest.mark.asyncio
async def test_oauth2_holds_back_from_an_endpoint_failing_slowly(
    client: HttpAuthenticatorParams,
    httpx_mock: HTTPXMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The hold counts from where an attempt ends, not where it starts."""

    async def respond(_request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(0.02)
        return httpx.Response(status_code=_BAD_REQUEST, text='invalid_client')

    httpx_mock.add_callback(
        respond,
        method='POST',
        url=_TOKEN_URL,
        is_reusable=True,
    )
    # an endpoint slower to fail than the interval would otherwise be
    # asked again by every request that waited for it
    monkeypatch.setattr(
        authenticators,
        'FAILED_ACQUISITION_HOLD_SECONDS',
        0.01,
    )

    authenticator = create_authenticator(_oauth2_config(), client)

    for _ in range(5):
        with pytest.raises(AuthenticationError):
            await authenticator.headers()

    assert len(httpx_mock.get_requests()) == 1


@pytest.mark.asyncio
async def test_oauth2_takes_a_token_once_the_endpoint_recovers(
    client: HttpAuthenticatorParams,
    httpx_mock: HTTPXMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A recovered endpoint is not answered with the old failure."""
    answers = iter(
        [httpx.Response(status_code=_BAD_REQUEST, text='invalid_client')],
    )
    httpx_mock.add_callback(
        lambda _request: next(
            answers,
            httpx.Response(
                status_code=200,
                json={'access_token': 'tok', 'expires_in': 0.001},
            ),
        ),
        method='POST',
        url=_TOKEN_URL,
        is_reusable=True,
    )
    monkeypatch.setattr(
        authenticators,
        'FAILED_ACQUISITION_HOLD_SECONDS',
        0.0,
    )

    authenticator = create_authenticator(_oauth2_config(), client)

    with pytest.raises(AuthenticationError):
        await authenticator.headers()

    await authenticator.headers()

    # the hold is lifted by the success, so the next renewal is not
    # answered with the failure that came before it
    monkeypatch.setattr(
        authenticators,
        'FAILED_ACQUISITION_HOLD_SECONDS',
        5.0,
    )
    await asyncio.sleep(0.01)

    assert (await authenticator.headers())['Authorization'] == 'Bearer tok'


class _KeyHttpAuthConfig(BaseHttpAuthConfig, frozen=True):
    """Config of a method built on the token lifecycle."""

    type: Literal[AuthType.BASIC] = AuthType.BASIC
    key: str = 'key'


class _KeyHttpAuthenticator(TokenHttpAuthenticator[_KeyHttpAuthConfig]):
    """Method supplying nothing but the exchange minting a token."""

    minted = 0

    @override
    async def _fetch_token(self) -> AcquiredToken:
        type(self).minted += 1
        return AcquiredToken(value=f'tok-{self.minted}', lifetime=0.001)


@pytest.mark.asyncio
async def test_a_method_built_on_the_lifecycle_inherits_it(
    client: HttpAuthenticatorParams,
) -> None:
    """A further method supplies the exchange and nothing else.

    The cache, the renewal ahead of the expiry, the single lock over
    them and the answer to a rejection are the reason this seam
    exists: a method that mints a token differently must not have to
    carry its own copy of them.
    """
    _KeyHttpAuthenticator.minted = 0
    authenticator = _KeyHttpAuthenticator(_KeyHttpAuthConfig(), client)

    await authenticator.open()
    sent = await authenticator.headers()

    assert sent == {'Authorization': 'Bearer tok-1'}

    # cached until it expires, then renewed
    assert await authenticator.headers() == sent
    await asyncio.sleep(0.01)
    assert await authenticator.headers() == {'Authorization': 'Bearer tok-2'}

    # a rejection naming a token just minted is not answered by
    # minting another one
    assert await authenticator.handle_unauthorized(sent) is True
    assert (
        await authenticator.handle_unauthorized(
            {'Authorization': 'Bearer tok-2'},
        )
        is False
    )


def test_an_abstract_method_claims_no_auth_type() -> None:
    """The lifecycle itself is not an answer to any auth type."""
    registered = HttpAuthenticator._registered_authenticators  # noqa: SLF001

    assert TokenHttpAuthenticator not in registered.values()
    assert _KeyHttpAuthenticator not in registered.values()
    assert registered[AuthType.BASIC] is BasicHttpAuthenticator
