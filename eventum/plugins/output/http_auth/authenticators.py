"""Authenticators for http based output plugins."""

from __future__ import annotations

import asyncio
import math
import time
from abc import ABC, abstractmethod
from base64 import b64encode
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Generic,
    NamedTuple,
    TypedDict,
    TypeVar,
    override,
)

import httpx

from eventum.exceptions import ContextualError
from eventum.plugins.output.http_auth.config import (
    AuthType,
    BaseHttpAuthConfig,
    BasicHttpAuthConfig,
    BearerHttpAuthConfig,
    ClientAuthMethod,
    HttpAuthConfigT,
    OAuth2ClientCredentialsHttpAuthConfig,
    is_header_value,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

EXPIRY_LEEWAY_SECONDS = 30.0
"""Seconds a token is considered expired before it actually is."""

MIN_REJECTED_TOKEN_AGE_SECONDS = 5.0
"""Minimal age of a token that a rejected request may discard.

A token minted moments ago and refused is refused for what it is, not
for its age, so replacing it would only ask for the same refusal.
"""

FAILED_ACQUISITION_HOLD_SECONDS = 5.0
"""Time a failure of a token endpoint is answered with.

Without it an endpoint refusing the credentials would be asked once
per event.
"""

TOKEN_REQUEST_TIMEOUT_SECONDS = 30.0
"""Timeout of a token request.

The requests of a plugin wait for the token being taken, so the budget
of a token exchange is not the budget of shipping a batch of events.
"""


class AuthenticationError(ContextualError):
    """Credentials cannot be turned into request headers."""


def basic_auth_header(username: str, password: str) -> str:
    """Build the header of HTTP basic authentication.

    Parameters
    ----------
    username : str
        Username to authenticate with.

    password : str
        Password of the user.

    Returns
    -------
    str
        Value of the `Authorization` header.

    """
    credentials = f'{username}:{password}'.encode()

    return f'Basic {b64encode(credentials).decode()}'


class AcquiredToken(NamedTuple):
    """Token taken from an endpoint.

    Attributes
    ----------
    value : str
        Token itself.

    lifetime : float
        Seconds the token can be used for, `math.inf` when the
        endpoint states no usable life for it.

    """

    value: str
    lifetime: float


class HttpAuthenticatorParams(TypedDict):
    """Parameters for HTTP authenticator.

    Attributes
    ----------
    client : httpx.AsyncClient
        Client the data requests travel, used for the requests the
        authenticator performs on its own.

    """

    client: httpx.AsyncClient


T = TypeVar('T', bound=BaseHttpAuthConfig)


class HttpAuthenticator(ABC, Generic[T]):
    """Base authenticator turning credentials into request headers.

    Other Parameters
    ----------------
    auth_type : AuthType | None, default=None
        Authentication type to bind authenticator class to. Left unset
        by an abstract authenticator that a concrete one is built on.

    """

    _registered_authenticators: ClassVar[
        dict[AuthType, type[HttpAuthenticator[Any]]]
    ] = {}

    def __init_subclass__(
        cls,
        auth_type: AuthType | None = None,
        **kwargs: Any,
    ) -> None:
        if auth_type is None:
            return super().__init_subclass__(**kwargs)

        registered = HttpAuthenticator._registered_authenticators
        if auth_type in registered:
            msg = (
                f'Authenticator {registered[auth_type]} is already '
                f'registered for auth type `{auth_type}`'
            )
            raise ValueError(msg)

        registered[auth_type] = cls

        return super().__init_subclass__(**kwargs)

    def __init__(self, config: T, params: HttpAuthenticatorParams) -> None:
        """Initialize authenticator.

        Parameters
        ----------
        config : T
            Authentication config.

        params : HttpAuthenticatorParams
            Authenticator params.

        """
        self._config = config
        self._params = params

    @classmethod
    def get_authenticator(
        cls,
        auth_type: AuthType,
    ) -> type[HttpAuthenticator[Any]]:
        """Get authenticator class bound to the authentication type.

        Parameters
        ----------
        auth_type : AuthType
            Authentication type.

        Returns
        -------
        type[HttpAuthenticator[Any]]
            Authenticator class.

        Raises
        ------
        ValueError
            If no authenticator is registered for the type.

        """
        try:
            return cls._registered_authenticators[auth_type]
        except KeyError:
            msg = f'No authenticator for auth type `{auth_type}`'
            raise ValueError(msg) from None

    async def open(self) -> None:
        """Acquire whatever the first request needs.

        Raises
        ------
        AuthenticationError
            If credentials cannot be acquired.

        """
        return

    async def close(self) -> None:
        """Release whatever was acquired."""
        return

    @abstractmethod
    async def headers(self) -> Mapping[str, str]:
        """Get authentication headers of a single request.

        Returns
        -------
        Mapping[str, str]
            Headers to add to the request.

        Raises
        ------
        AuthenticationError
            If credentials cannot be acquired.

        """
        ...

    async def handle_unauthorized(
        self,
        sent: Mapping[str, str],  # noqa: ARG002
    ) -> bool:
        """Handle a request rejected as unauthorized.

        Parameters
        ----------
        sent : Mapping[str, str]
            Authentication headers the rejected request carried, as
            they were returned by `headers`.

        Returns
        -------
        bool
            Whether repeating the request is worth it.

        """
        return False


class BasicHttpAuthenticator(
    HttpAuthenticator[BasicHttpAuthConfig],
    auth_type=AuthType.BASIC,
):
    """Authenticator sending static basic credentials."""

    @override
    def __init__(
        self,
        config: BasicHttpAuthConfig,
        params: HttpAuthenticatorParams,
    ) -> None:
        super().__init__(config, params)

        self._headers = {
            'Authorization': basic_auth_header(
                config.username,
                config.password or '',
            ),
        }

    @override
    async def headers(self) -> Mapping[str, str]:
        return self._headers


class BearerHttpAuthenticator(
    HttpAuthenticator[BearerHttpAuthConfig],
    auth_type=AuthType.BEARER,
):
    """Authenticator sending a static bearer token."""

    @override
    def __init__(
        self,
        config: BearerHttpAuthConfig,
        params: HttpAuthenticatorParams,
    ) -> None:
        super().__init__(config, params)

        self._headers = {'Authorization': f'Bearer {config.token}'}

    @override
    async def headers(self) -> Mapping[str, str]:
        return self._headers


class TokenHttpAuthenticator(HttpAuthenticator[T]):
    """Authenticator holding a token it takes and renews itself.

    Notes
    -----
    Everything a renewable credential needs lives here: one lock over
    the cached token, renewal ahead of the expiry it was given, the
    hold on an endpoint that just refused, and the answer to a request
    the destination rejected. A method built on this supplies only the
    exchange that mints the token.

    """

    @override
    def __init__(self, config: T, params: HttpAuthenticatorParams) -> None:
        super().__init__(config, params)

        self._lock = asyncio.Lock()
        self._token: str | None = None
        self._obtained_at = 0.0
        self._expires_at = 0.0
        self._attempted_at = -math.inf
        self._failure: tuple[str, dict[str, Any]] | None = None

    @override
    async def open(self) -> None:
        async with self._lock:
            await self._take_token()

    @override
    async def headers(self) -> Mapping[str, str]:
        async with self._lock:
            if self._token is None or time.monotonic() >= self._expires_at:
                await self._take_token()

            token = self._token

        return {'Authorization': f'Bearer {token}'}

    @override
    async def handle_unauthorized(self, sent: Mapping[str, str]) -> bool:
        async with self._lock:
            if self._token is None:
                return True

            # the rejection may name a token that was already
            # replaced, and the request deserves the current one
            if sent.get('Authorization') != f'Bearer {self._token}':
                return True

            age = time.monotonic() - self._obtained_at
            if age < MIN_REJECTED_TOKEN_AGE_SECONDS:
                return False

            self._token = None

        return True

    @abstractmethod
    async def _fetch_token(self) -> AcquiredToken:
        """Take a token from wherever this method takes it from.

        Returns
        -------
        AcquiredToken
            Token and the seconds it can be used for.

        Raises
        ------
        AuthenticationError
            If the token cannot be taken.

        Notes
        -----
        Called with `self._lock` held, so the attempts are single
        file and no two of them reach the endpoint at once.

        """
        ...

    async def _take_token(self) -> None:
        """Take a token, holding back from a failing endpoint.

        Raises
        ------
        AuthenticationError
            If the token cannot be taken, or a recent attempt to take
            it already failed.

        Notes
        -----
        The caller must hold `self._lock`, which is what makes the
        attempts single file.

        """
        waited = time.monotonic() - self._attempted_at

        if (
            self._failure is not None
            and waited < FAILED_ACQUISITION_HOLD_SECONDS
        ):
            msg, context = self._failure
            raise AuthenticationError(msg, context=context)

        try:
            token = await self._fetch_token()
        except AuthenticationError as e:
            self._failure = (str(e), e.context)
            raise
        else:
            # the age of the token is the age of the token, so a
            # failed attempt does not make the cached one look fresh
            self._obtained_at = time.monotonic()
            self._failure = None
            self._token = token.value
            self._expires_at = self._obtained_at + token.lifetime
        finally:
            # the attempt is stamped where it ends, not where it
            # starts: an endpoint that takes longer to fail than the
            # hold would otherwise be asked again at once
            self._attempted_at = time.monotonic()


class OAuth2ClientCredentialsHttpAuthenticator(
    TokenHttpAuthenticator[OAuth2ClientCredentialsHttpAuthConfig],
    auth_type=AuthType.OAUTH2_CLIENT_CREDENTIALS,
):
    """Authenticator holding a token of the client credentials grant."""

    def _build_form(self) -> dict[str, str]:
        """Build form parameters of the token request."""
        config = self._config
        form = {'grant_type': 'client_credentials'}

        if config.client_auth_method is ClientAuthMethod.POST:
            form['client_id'] = config.client_id
            form['client_secret'] = config.client_secret

        if config.scopes:
            form['scope'] = ' '.join(config.scopes)

        if config.audience is not None:
            form['audience'] = config.audience

        if config.resource is not None:
            form['resource'] = config.resource

        form.update(config.extra_params)

        return form

    @override
    async def _fetch_token(self) -> AcquiredToken:
        config = self._config
        url = str(config.token_url)
        headers = {}

        if config.client_auth_method is ClientAuthMethod.BASIC:
            headers['Authorization'] = basic_auth_header(
                config.client_id,
                config.client_secret,
            )

        response = await request_token(
            client=self._params['client'],
            url=url,
            form=self._build_form(),
            headers=headers,
        )

        return parse_token_response(response=response, url=url)


async def request_token(
    client: httpx.AsyncClient,
    url: str,
    form: dict[str, str],
    headers: dict[str, str],
) -> httpx.Response:
    """Perform a token request of an OAuth2 grant.

    Parameters
    ----------
    client : httpx.AsyncClient
        Client to perform the request with.

    url : str
        URL of the token endpoint.

    form : dict[str, str]
        Form parameters of the grant.

    headers : dict[str, str]
        Headers of the request, the configured headers of a plugin
        are deliberately not among them.

    Returns
    -------
    httpx.Response
        Response of the endpoint, of any status code.

    Raises
    ------
    AuthenticationError
        If the endpoint cannot be reached.

    """
    try:
        return await client.post(
            url=url,
            data=form,
            headers=headers,
            timeout=httpx.Timeout(TOKEN_REQUEST_TIMEOUT_SECONDS),
        )
    except httpx.RequestError as e:
        msg = 'Failed to request access token'
        raise AuthenticationError(
            msg,
            context={'reason': str(e), 'url': url},
        ) from e


def parse_token_response(response: httpx.Response, url: str) -> AcquiredToken:
    """Read the token an OAuth2 endpoint answered with.

    Parameters
    ----------
    response : httpx.Response
        Response of the token endpoint.

    url : str
        URL of the token endpoint, reported with a failure.

    Returns
    -------
    AcquiredToken
        Token and the seconds it can be used for.

    Raises
    ------
    AuthenticationError
        If the response carries anything but a usable token.

    """
    if not response.is_success:
        msg = 'Token endpoint returned unsuccessful status code'
        raise AuthenticationError(
            msg,
            context={
                'http_status': response.status_code,
                'reason': response.text,
                'url': url,
            },
        )

    # a successful answer is exactly where a token lives, so nothing
    # of it reaches the context of an error
    context = {'http_status': response.status_code, 'url': url}

    try:
        payload = response.json()
    except ValueError:
        msg = 'Token endpoint returned invalid JSON'
        raise AuthenticationError(msg, context=context) from None

    token = payload.get('access_token') if isinstance(payload, dict) else None

    if not isinstance(token, str) or not token:
        msg = 'Token endpoint returned no access token'
        raise AuthenticationError(msg, context=context)

    if not is_header_value(token):
        # a token no header can carry fails at every request instead
        # of once, and without naming a cause; the same rule guards a
        # token written in the configuration
        msg = 'Token endpoint returned a token no header can carry'
        raise AuthenticationError(msg, context=context)

    return AcquiredToken(value=token, lifetime=_get_lifetime(payload))


def _get_lifetime(payload: dict[str, Any]) -> float:
    """Get seconds a token can be used for.

    Notes
    -----
    A missing, non numeric or non positive `expires_in` means the
    answer carries no expiry information, so the token is held until a
    request is rejected with it.

    """
    try:
        expires_in = float(payload['expires_in'])
    except KeyError, TypeError, ValueError:
        return math.inf

    if not math.isfinite(expires_in) or expires_in <= 0:
        return math.inf

    return max(expires_in - EXPIRY_LEEWAY_SECONDS, expires_in / 2)


def create_authenticator(
    config: HttpAuthConfigT,
    params: HttpAuthenticatorParams,
) -> HttpAuthenticator[Any]:
    """Create authenticator corresponding to the config.

    Parameters
    ----------
    config : HttpAuthConfigT
        Authentication config.

    params : HttpAuthenticatorParams
        Authenticator params.

    Returns
    -------
    HttpAuthenticator[Any]
        Authenticator bound to the type of the config.

    Raises
    ------
    ValueError
        If no authenticator is registered for the type.

    """
    AuthenticatorCls = HttpAuthenticator.get_authenticator(  # noqa: N806
        config.type,
    )

    return AuthenticatorCls(config, params=params)
