"""Tests for streaming a log file to a WebSocket."""

import asyncio
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest
from fastapi import WebSocket, WebSocketDisconnect, status
from fastapi.exceptions import WebSocketException

from eventum.api.utils.log_streaming import (
    _watch_disconnect,
    stream_log_file_to_websocket,
)


class _FakeWebSocket:
    """Minimal WebSocket fake driving the streaming helper.

    ``receive`` yields any ``pre_messages`` first, then a disconnect
    dict (Starlette semantics) after ``disconnect_after`` seconds.
    ``send_text`` records chunks, or raises ``send_error`` if set.
    """

    def __init__(
        self,
        *,
        disconnect_after: float,
        send_error: Exception | None = None,
        state: str = 'CONNECTED',
        pre_messages: tuple[dict[str, Any], ...] = (),
    ) -> None:
        self.sent: list[str] = []
        self._disconnect_after = disconnect_after
        self._send_error = send_error
        self.client_state = SimpleNamespace(name=state)
        self._pre = list(pre_messages)

    async def receive(self) -> dict[str, Any]:
        if self._pre:
            return self._pre.pop(0)
        await asyncio.sleep(self._disconnect_after)
        self.client_state = SimpleNamespace(name='DISCONNECTED')
        return {'type': 'websocket.disconnect', 'code': 1012}

    async def send_text(self, data: str) -> None:
        if self._send_error is not None:
            raise self._send_error
        self.sent.append(data)


async def test_stops_when_disconnected_while_idle(tmp_path: Path) -> None:
    """An idle stream ends promptly once the peer disconnects.

    Regression guard: the disconnect arrives between reads, so it is
    seen only because a concurrent receive watches for it.
    """
    log = tmp_path / 'log.txt'
    log.write_text('')
    ws = _FakeWebSocket(disconnect_after=0.1)

    await asyncio.wait_for(
        stream_log_file_to_websocket(
            websocket=cast('WebSocket', ws), path=log, end_offset=0
        ),
        timeout=1.0,
    )

    assert ws.sent == []


async def test_forwards_content_then_stops(tmp_path: Path) -> None:
    """Existing tail content is forwarded before the disconnect."""
    log = tmp_path / 'log.txt'
    log.write_text('hello world')
    ws = _FakeWebSocket(disconnect_after=0.2)

    await asyncio.wait_for(
        stream_log_file_to_websocket(
            websocket=cast('WebSocket', ws), path=log, end_offset=5
        ),
        timeout=1.0,
    )

    assert ''.join(ws.sent) == 'world'


async def test_send_disconnect_breaks_cleanly(tmp_path: Path) -> None:
    """A disconnect surfaced on send ends the stream without error."""
    log = tmp_path / 'log.txt'
    log.write_text('hello world')
    ws = _FakeWebSocket(
        disconnect_after=10.0, send_error=WebSocketDisconnect(1006)
    )

    await asyncio.wait_for(
        stream_log_file_to_websocket(
            websocket=cast('WebSocket', ws), path=log, end_offset=5
        ),
        timeout=1.0,
    )

    assert ws.sent == []


async def test_send_runtime_error_breaks_cleanly(tmp_path: Path) -> None:
    """A post-close send RuntimeError ends the stream without error.

    On shutdown the watcher's disconnect can race ahead of an in-flight
    send, making the ASGI server raise a bare RuntimeError; the helper
    must treat it as a disconnect, not re-raise it.
    """
    log = tmp_path / 'log.txt'
    log.write_text('hello world')
    ws = _FakeWebSocket(
        disconnect_after=10.0,
        send_error=RuntimeError('Unexpected ASGI message'),
    )

    await asyncio.wait_for(
        stream_log_file_to_websocket(
            websocket=cast('WebSocket', ws), path=log, end_offset=5
        ),
        timeout=1.0,
    )

    assert ws.sent == []


async def test_watcher_ignores_non_disconnect_messages() -> None:
    """The watcher waits for a disconnect, ignoring other messages."""
    stop = asyncio.Event()
    ws = _FakeWebSocket(
        disconnect_after=0.3,
        pre_messages=({'type': 'websocket.receive', 'text': 'ping'},),
    )

    task = asyncio.create_task(_watch_disconnect(cast('WebSocket', ws), stop))
    await asyncio.sleep(0.05)
    assert not stop.is_set()

    await asyncio.wait_for(task, timeout=1.0)
    assert stop.is_set()


async def test_os_error_raises_ws_exception_when_connected(
    tmp_path: Path,
) -> None:
    """An unreadable file raises a WS error while still connected."""
    missing = tmp_path / 'does-not-exist.txt'
    ws = _FakeWebSocket(disconnect_after=10.0)

    with pytest.raises(WebSocketException) as exc:
        await asyncio.wait_for(
            stream_log_file_to_websocket(
                websocket=cast('WebSocket', ws), path=missing, end_offset=0
            ),
            timeout=1.0,
        )

    assert exc.value.code == status.WS_1011_INTERNAL_ERROR


async def test_os_error_swallowed_when_disconnected(tmp_path: Path) -> None:
    """A read failure after the peer left is swallowed, not raised."""
    missing = tmp_path / 'does-not-exist.txt'
    ws = _FakeWebSocket(disconnect_after=10.0, state='DISCONNECTED')

    await asyncio.wait_for(
        stream_log_file_to_websocket(
            websocket=cast('WebSocket', ws), path=missing, end_offset=0
        ),
        timeout=1.0,
    )

    assert ws.sent == []
