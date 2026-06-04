"""End-to-end MCP Streamable-HTTP roundtrip over a live server.

Boots the server app (MCP enabled) under uvicorn in a thread on an
ephemeral port and drives it with the real MCP Streamable-HTTP client.
A successful ``initialize`` proves the session manager ran in the server
lifespan (SDK issue #1367 would otherwise raise "Task group is not
initialized").
"""

import socket
import threading
import time
from collections.abc import Iterator
from http import HTTPStatus
from pathlib import Path
from unittest.mock import MagicMock

import anyio
import httpx
import pytest
import uvicorn
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from eventum.app.manager import GeneratorManager
from eventum.app.models.parameters.log import LogParameters
from eventum.app.models.parameters.path import PathParameters
from eventum.app.models.parameters.server import (
    MCPParameters,
    ServerParameters,
)
from eventum.app.models.settings import Settings
from eventum.core.parameters import GenerationParameters
from eventum.server.main import build_server_app

# 12 authoring tools + 5 live-management tools.
_EXPECTED_TOOL_COUNT = 17
_STARTUP_TIMEOUT = 20.0
_POLL_INTERVAL = 0.05


def _free_port() -> int:
    sock = socket.socket()
    sock.bind(('127.0.0.1', 0))
    port = int(sock.getsockname()[1])
    sock.close()
    return port


def _settings(tmp_path: Path) -> Settings:
    (tmp_path / 'generators').mkdir()
    return Settings(
        server=ServerParameters(
            mcp=MCPParameters(enabled=True, allow_write=True),
        ),
        generation=GenerationParameters(),
        log=LogParameters(),
        path=PathParameters(
            logs=tmp_path / 'logs',
            startup=tmp_path / 'startup.yml',
            generators_dir=tmp_path / 'generators',
            keyring_cryptfile=tmp_path / 'keyring.cfg',
        ),
    )


@pytest.fixture
def base_url(tmp_path: Path) -> Iterator[str]:
    """Run the MCP-enabled server in a thread; yield its base URL."""
    app = build_server_app(
        enabled_services={'mcp': True},
        generator_manager=GeneratorManager(),
        settings=_settings(tmp_path),
        instance_hooks=MagicMock(),  # type: ignore[arg-type]
    )
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


def test_roundtrip_lists_all_tools(base_url: str) -> None:
    """An authenticated client sees both authoring and live tools."""

    async def drive() -> set[str]:
        url = base_url + '/mcp/'
        auth = httpx.BasicAuth('eventum', 'eventum')
        async with (
            streamablehttp_client(url, auth=auth) as (read, write, _),
            ClientSession(read, write) as session,
        ):
            with anyio.fail_after(_STARTUP_TIMEOUT):
                await session.initialize()
            tools = await session.list_tools()
            return {tool.name for tool in tools.tools}

    names = anyio.run(drive)
    assert len(names) == _EXPECTED_TOOL_COUNT
    assert 'preview_events' in names
    assert 'list_generators_live' in names


def test_roundtrip_calls_live_tool(base_url: str) -> None:
    """A live tool executes over HTTP against the real manager."""

    async def drive() -> bool:
        url = base_url + '/mcp/'
        auth = httpx.BasicAuth('eventum', 'eventum')
        async with (
            streamablehttp_client(url, auth=auth) as (read, write, _),
            ClientSession(read, write) as session,
        ):
            with anyio.fail_after(_STARTUP_TIMEOUT):
                await session.initialize()
            result = await session.call_tool('list_generators_live')
            return bool(result.isError)

    assert anyio.run(drive) is False


def test_unauthorized_without_credentials(base_url: str) -> None:
    """The mount rejects requests without Basic credentials."""
    resp = httpx.post(base_url + '/mcp/', json={}, timeout=_STARTUP_TIMEOUT)
    assert resp.status_code == HTTPStatus.UNAUTHORIZED
