"""Basic-auth ASGI middleware for the MCP HTTP mount.

API auth is dependency-based and is not inherited by mounted sub-apps,
so the MCP mount carries its own Basic-auth gate reusing the configured
server credentials.
"""

from starlette.types import ASGIApp, Receive, Scope, Send

from eventum.security.auth import verify_basic_credentials

_UNAUTHORIZED_BODY = b'{"detail": "Unauthorized"}'


class BasicAuthMiddleware:
    """Require HTTP Basic auth matching the configured credentials."""

    def __init__(self, app: ASGIApp, *, user: str, password: str) -> None:
        """Wrap ``app``, requiring the given Basic credentials."""
        self._app = app
        self._user = user
        self._password = password

    async def __call__(
        self, scope: Scope, receive: Receive, send: Send
    ) -> None:
        """Pass authorized HTTP requests through; reject the rest."""
        if scope['type'] != 'http' or self._authorized(scope):
            await self._app(scope, receive, send)
            return
        await self._reject(send)

    def _authorized(self, scope: Scope) -> bool:
        headers = dict(scope['headers'])
        raw = headers.get(b'authorization')
        if raw is None:
            return False
        try:
            scheme, _, encoded = raw.decode().partition(' ')
        except UnicodeDecodeError:
            return False
        if scheme.lower() != 'basic':
            return False
        return (
            verify_basic_credentials(encoded, self._user, self._password)
            is not None
        )

    async def _reject(self, send: Send) -> None:
        await send(
            {
                'type': 'http.response.start',
                'status': 401,
                'headers': [
                    (b'www-authenticate', b'Basic realm="eventum-mcp"'),
                    (b'content-type', b'application/json'),
                ],
            }
        )
        await send({'type': 'http.response.body', 'body': _UNAUTHORIZED_BODY})
