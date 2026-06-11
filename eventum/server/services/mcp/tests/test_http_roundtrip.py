"""End-to-end MCP Streamable-HTTP roundtrip over a live server.

Boots the server app (MCP enabled) under uvicorn in a thread on an
ephemeral port and drives it with the real MCP Streamable-HTTP client.
A successful ``initialize`` proves the session manager ran in the server
lifespan (SDK issue #1367 would otherwise raise "Task group is not
initialized").

The UI-enabled fixture additionally proves the MCP mount stays
reachable and authenticated when the UI SPA catch-all route is
registered.
"""

import socket
import threading
import time
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
from http import HTTPStatus
from pathlib import Path
from unittest.mock import MagicMock

import anyio
import httpx
import pytest
import uvicorn
from fastapi import FastAPI
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.types import CallToolResult

from eventum.app.manager import GeneratorManager
from eventum.app.models.settings import Settings
from eventum.server.main import build_server_app
from eventum.server.services.ui import injector as ui_injector
from eventum.server.services.ui import routes as ui_routes

# 16 authoring tools + 9 live-management tools.
_EXPECTED_TOOL_COUNT = 25
_STARTUP_TIMEOUT = 20.0
_POLL_INTERVAL = 0.05


def _free_port() -> int:
    sock = socket.socket()
    sock.bind(('127.0.0.1', 0))
    port = int(sock.getsockname()[1])
    sock.close()
    return port


@contextmanager
def _serve(app: FastAPI) -> Iterator[str]:
    """Run the app under uvicorn in a thread; yield its base URL."""
    port = _free_port()
    config = uvicorn.Config(
        app,
        host='127.0.0.1',
        port=port,
        log_level='warning',
        lifespan='on',
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    start = time.monotonic()
    while not server.started:
        if time.monotonic() - start > _STARTUP_TIMEOUT:
            server.should_exit = True
            pytest.fail('server did not start in time')
        time.sleep(_POLL_INTERVAL)

    try:
        yield f'http://127.0.0.1:{port}'
    finally:
        server.should_exit = True
        thread.join(timeout=_STARTUP_TIMEOUT)


@asynccontextmanager
async def _client_session(base_url: str) -> AsyncIterator[ClientSession]:
    """Open an authenticated MCP session and run ``initialize``."""
    auth = httpx.BasicAuth('eventum', 'eventum')
    async with (
        httpx.AsyncClient(auth=auth) as client,
        streamable_http_client(base_url + '/mcp/', http_client=client) as (
            read,
            write,
            _,
        ),
        ClientSession(read, write) as session,
    ):
        with anyio.fail_after(_STARTUP_TIMEOUT):
            await session.initialize()
        yield session


@pytest.fixture
def base_url(mcp_settings: Settings) -> Iterator[str]:
    """Run the MCP-enabled server in a thread; yield its base URL."""
    app = build_server_app(
        enabled_services={'mcp': True},
        generator_manager=GeneratorManager(),
        settings=mcp_settings,
        instance_hooks=MagicMock(),  # type: ignore[arg-type]
        startup=MagicMock(),
    )
    with _serve(app) as url:
        yield url


@pytest.fixture
def ui_base_url(
    mcp_settings: Settings,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[str]:
    """Run the server with MCP and UI both enabled; yield its URL.

    The UI static directory is faked under ``tmp_path`` so the test
    does not depend on built frontend assets.
    """
    www_dir = tmp_path / 'www'
    (www_dir / 'assets').mkdir(parents=True)
    (www_dir / 'index.html').write_text('<html>studio</html>')
    (www_dir / 'assets' / 'app.js').write_text('// stub')

    monkeypatch.setattr(ui_routes, 'WWW_DIR', www_dir)
    monkeypatch.setattr(ui_injector, 'WWW_DIR', www_dir)
    monkeypatch.setattr(ui_injector, 'ASSETS_DIR', www_dir / 'assets')

    app = build_server_app(
        enabled_services={'mcp': True, 'ui': True},
        generator_manager=GeneratorManager(),
        settings=mcp_settings,
        instance_hooks=MagicMock(),  # type: ignore[arg-type]
        startup=MagicMock(),
    )
    with _serve(app) as url:
        yield url


def test_roundtrip_lists_all_tools(base_url: str) -> None:
    """An authenticated client sees both authoring and live tools."""

    async def drive() -> set[str]:
        async with _client_session(base_url) as session:
            tools = await session.list_tools()
            return {tool.name for tool in tools.tools}

    names = anyio.run(drive)
    assert len(names) == _EXPECTED_TOOL_COUNT
    assert 'preview_events' in names
    assert 'list_generators_live' in names


def test_roundtrip_calls_live_tool(base_url: str) -> None:
    """A live tool executes over HTTP against the real manager."""

    async def drive() -> CallToolResult:
        async with _client_session(base_url) as session:
            return await session.call_tool('list_generators_live')

    result = anyio.run(drive)
    assert result.isError is False
    # Fresh manager has no generators: the live tool returns an
    # empty listing, not just a non-error envelope.
    assert result.content == []


def test_unauthorized_without_credentials(base_url: str) -> None:
    """The mount rejects requests without Basic credentials."""
    resp = httpx.post(base_url + '/mcp/', json={}, timeout=_STARTUP_TIMEOUT)
    assert resp.status_code == HTTPStatus.UNAUTHORIZED


def test_mcp_auth_enforced_with_ui_enabled(ui_base_url: str) -> None:
    """The UI SPA catch-all does not shadow the MCP mount.

    With the UI enabled, unauthenticated requests to the endpoint
    must hit the Basic-auth gate instead of receiving index.html.
    """
    resp = httpx.get(ui_base_url + '/', timeout=_STARTUP_TIMEOUT)
    assert resp.status_code == HTTPStatus.OK
    assert resp.headers['content-type'].startswith('text/html')

    resp = httpx.get(ui_base_url + '/mcp/', timeout=_STARTUP_TIMEOUT)
    assert resp.status_code == HTTPStatus.UNAUTHORIZED

    resp = httpx.post(
        ui_base_url + '/mcp/',
        json={},
        timeout=_STARTUP_TIMEOUT,
    )
    assert resp.status_code == HTTPStatus.UNAUTHORIZED


def test_slashless_path_reaches_mcp_with_ui_enabled(
    ui_base_url: str,
) -> None:
    """The configured slashless path redirects to the MCP endpoint."""
    resp = httpx.get(
        ui_base_url + '/mcp',
        timeout=_STARTUP_TIMEOUT,
        follow_redirects=False,
    )
    assert resp.status_code == HTTPStatus.TEMPORARY_REDIRECT
    assert resp.headers['location'].endswith('/mcp/')

    resp = httpx.post(
        ui_base_url + '/mcp',
        json={},
        timeout=_STARTUP_TIMEOUT,
        follow_redirects=True,
    )
    assert resp.status_code == HTTPStatus.UNAUTHORIZED


def test_roundtrip_with_ui_enabled(ui_base_url: str) -> None:
    """An authenticated MCP session works while the UI is mounted."""

    async def drive() -> set[str]:
        async with _client_session(ui_base_url) as session:
            tools = await session.list_tools()
            return {tool.name for tool in tools.tools}

    names = anyio.run(drive)
    assert len(names) == _EXPECTED_TOOL_COUNT
