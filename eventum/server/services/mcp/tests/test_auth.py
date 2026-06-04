"""Tests for the MCP Basic-auth middleware."""

import base64
from http import HTTPStatus

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from eventum.server.services.mcp.auth import BasicAuthMiddleware


def _client() -> TestClient:
    async def ok(request: Request) -> PlainTextResponse:  # noqa: ARG001
        return PlainTextResponse('ok')

    inner = Starlette(routes=[Route('/', ok)])
    gated = BasicAuthMiddleware(inner, user='u', password='p')  # noqa: S106
    return TestClient(gated)


def test_missing_auth_returns_401() -> None:
    """A request with no credentials is rejected with 401."""
    resp = _client().get('/')
    assert resp.status_code == HTTPStatus.UNAUTHORIZED
    assert 'www-authenticate' in {k.lower() for k in resp.headers}


def test_wrong_auth_returns_401() -> None:
    """Wrong credentials are rejected."""
    resp = _client().get('/', auth=('u', 'wrong'))
    assert resp.status_code == HTTPStatus.UNAUTHORIZED


def test_correct_auth_passes() -> None:
    """Correct credentials reach the inner app."""
    resp = _client().get('/', auth=('u', 'p'))
    assert resp.status_code == HTTPStatus.OK
    assert resp.text == 'ok'


def test_non_ascii_credentials_return_401() -> None:
    """Non-ASCII Basic credentials are rejected, not crashed (500)."""
    token = base64.b64encode('usér:p'.encode()).decode()
    resp = _client().get('/', headers={'Authorization': f'Basic {token}'})
    assert resp.status_code == HTTPStatus.UNAUTHORIZED
