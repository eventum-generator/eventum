"""Tests for the server lifespan registry."""

import contextlib
from collections.abc import AsyncIterator
from unittest.mock import MagicMock

from starlette.testclient import TestClient

from eventum.server.main import build_server_app


def test_lifespan_runs_registered_cms() -> None:
    """Registered context managers enter and exit across the lifespan."""
    events: list[str] = []

    @contextlib.asynccontextmanager
    async def cm() -> AsyncIterator[None]:
        events.append('enter')
        yield
        events.append('exit')

    app = build_server_app(
        enabled_services={},
        generator_manager=MagicMock(),
        settings=MagicMock(),
        instance_hooks=MagicMock(),  # type: ignore[arg-type]
        startup=MagicMock(),
    )
    app.state.lifespan_cms.append(cm)

    with TestClient(app):
        assert events == ['enter']

    assert events == ['enter', 'exit']
