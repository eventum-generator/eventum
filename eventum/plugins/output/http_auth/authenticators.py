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
    TypedDict,
    TypeVar,
    override,
)

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

import httpx

EXPIRY_LEEWAY_SECONDS = 30.0
"""Seconds a token is considered expired before it actually is."""

MIN_FORCED_REFRESH_INTERVAL_SECONDS = 5.0
"""Interval the attempts to take a token are kept apart by.

It is the minimal age of a token that a rejected request may discard,
and the time a failure of the token endpoint is answered with before
it is asked again.
"""


class AuthenticationError(ContextualError):
    """Credentials cannot be turned into request headers."""


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
    auth_type : AuthType
        Authentication type to bind authenticator class to.

    """

    _registered_authenticators: ClassVar[
        dict[AuthType, type[HttpAuthenticator[Any]]]
    ] = {}

    def __init_subclass__(cls, auth_type: AuthType, **kwargs: Any) -> None:
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
            Headers the rejected request carried.

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

        credentials = f'{config.username}:{config.password or ""}'
        token = b64encode(credentials.encode()).decode()
        self._headers = {'Authorization': f'Basic {token}'}

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


class OAuth2ClientCredentialsHttpAuthenticator(
    HttpAuthenticator[OAuth2ClientCredentialsHttpAuthConfig],
    auth_type=AuthType.OAUTH2_CLIENT_CREDENTIALS,
):
    """Authenticator holding a token of the client credentials grant.

    Notes
    -----
    One lock guards the cached token, so concurrent requests that find
    it missing or expired produce a single token request.

    """

    @override
    def __init__(
        self,
        config: OAuth2ClientCredentialsHttpAuthConfig,
        params: HttpAuthenticatorParams,
    ) -> None:
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
            if age < MIN_FORCED_REFRESH_INTERVAL_SECONDS:
                return False

            self._token = None

        return True

    async def _take_token(self) -> None:
        """Take a token, holding back from a failing endpoint.

        Raises
        ------
        AuthenticationError
            If the token cannot be taken, or a recent attempt to take
            it already failed.

        Notes
        -----
        Without the interval between the attempts a token endpoint
        that refuses the credentials would be requested once per
        event.

        """
        waited = time.monotonic() - self._attempted_at

        if (
            self._failure is not None
            and waited < MIN_FORCED_REFRESH_INTERVAL_SECONDS
        ):
            msg, context = self._failure
            raise AuthenticationError(msg, context=context)

        try:
            await self._request_token()
        except AuthenticationError as e:
            self._failure = (str(e), e.context)
            raise
        else:
            self._failure = None
        finally:
            # the attempt is stamped where it ends, not where it
            # starts: an endpoint that takes longer to fail than the
            # interval would otherwise be asked again at once
            self._attempted_at = time.monotonic()

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

    async def _request_token(self) -> None:
        """Request a token and cache it with its expiry.

        Raises
        ------
        AuthenticationError
            If the token endpoint is unreachable or answers with
            anything but a token.

        """
        config = self._config
        url = str(config.token_url)

        client = self._params['client']
        form = self._build_form()

        try:
            # the client carries no auth of its own, so a request
            # sent without one goes out unauthenticated
            if config.client_auth_method is ClientAuthMethod.BASIC:
                response = await client.post(
                    url=url,
                    data=form,
                    auth=httpx.BasicAuth(
                        config.client_id,
                        config.client_secret,
                    ),
                )
            else:
                response = await client.post(url=url, data=form)
        except httpx.RequestError as e:
            msg = 'Failed to request access token'
            raise AuthenticationError(
                msg,
                context={'reason': str(e), 'url': url},
            ) from e

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

        # a successful answer is exactly where a token lives, so
        # nothing of it reaches the context of an error
        try:
            payload = response.json()
        except ValueError:
            msg = 'Token endpoint returned invalid JSON'
            raise AuthenticationError(
                msg,
                context={'http_status': response.status_code, 'url': url},
            ) from None

        token = (
            payload.get('access_token') if isinstance(payload, dict) else None
        )

        if not isinstance(token, str) or not token:
            msg = 'Token endpoint returned no access token'
            raise AuthenticationError(
                msg,
                context={'http_status': response.status_code, 'url': url},
            )

        if not is_header_value(token):
            # a token no header can carry fails at every request
            # instead of once, and without naming its cause; the same
            # rule guards a token written in the configuration
            msg = 'Token endpoint returned a token no header can carry'
            raise AuthenticationError(
                msg,
                context={'http_status': response.status_code, 'url': url},
            )

        self._token = token
        self._obtained_at = time.monotonic()
        self._expires_at = self._obtained_at + self._get_lifetime(payload)

    @staticmethod
    def _get_lifetime(payload: dict[str, Any]) -> float:
        """Get seconds the token can be used for.

        Notes
        -----
        A missing, non numeric or non positive `expires_in` means the
        answer carries no expiry information, so the token is held
        until a request is rejected with it.

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
    client: httpx.AsyncClient,
) -> HttpAuthenticator[Any]:
    """Create authenticator corresponding to the config.

    Parameters
    ----------
    config : HttpAuthConfigT
        Authentication config.

    client : httpx.AsyncClient
        Client the data requests travel.

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

    return AuthenticatorCls(
        config,
        params=HttpAuthenticatorParams(client=client),
    )
