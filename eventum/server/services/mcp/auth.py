"""Basic-auth ASGI middleware for the MCP HTTP mount.

API auth is dependency-based and is not inherited by mounted sub-apps,
so the MCP mount carries its own Basic-auth gate reusing the configured
server credentials.
"""

import base64
import secrets

from starlette.types import ASGIApp, Receive, Scope, Send

_UNAUTHORIZED_BODY = b'{"error": "Unauthorized"}'


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
            if scheme.lower() != 'basic':
                return False
            user, _, password = (
                base64.b64decode(encoded).decode().partition(':')
            )
        except ValueError, UnicodeDecodeError:
            return False
        return secrets.compare_digest(
            user, self._user
        ) and secrets.compare_digest(password, self._password)

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
