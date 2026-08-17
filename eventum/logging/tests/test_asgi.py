"""Tests for log attribution of served requests."""

import logging
from collections.abc import Iterator
from typing import Any

import pytest
import structlog
from fastapi import FastAPI
from starlette.testclient import TestClient

from eventum.logging.asgi import LogContextMiddleware
from eventum.logging.channels import LogContext, resolve_channel


class ChannelCapture(logging.Handler):
    """Handler that records the channel of every record it receives."""

    def __init__(self) -> None:
        """Initialize capture."""
        super().__init__()
        self.channels: dict[str, str] = {}

    def emit(self, record: logging.LogRecord) -> None:
        """Resolve and remember the channel of the record."""
        self.channels[record.name] = resolve_channel(record)


@pytest.fixture
def capture() -> Iterator[ChannelCapture]:
    """Capture channels of records passing the root logger."""
    root = logging.getLogger()
    handlers = root.handlers[:]
    level = root.level
    root.handlers.clear()

    handler = ChannelCapture()
    root.addHandler(handler)
    root.setLevel(logging.DEBUG)

    yield handler

    root.handlers.clear()
    root.handlers.extend(handlers)
    root.setLevel(level)
    structlog.contextvars.clear_contextvars()


def build_app(context: LogContext) -> FastAPI:
    """Build app that logs from an unmapped package on every request."""
    app = FastAPI()
    app.add_middleware(LogContextMiddleware, context=context)

    @app.get('/probe')
    def probe() -> dict[str, Any]:
        logging.getLogger('eventum.core.config_loader').warning('Loading')
        logging.getLogger('some_library').warning('Requesting')

        return dict(structlog.contextvars.get_contextvars())

    return app


def test_request_attributes_unmapped_packages(
    capture: ChannelCapture,
) -> None:
    """Records of a served request belong to the serving component."""
    with TestClient(build_app({'component': 'server'})) as client:
        assert client.get('/probe').status_code == 200

    assert capture.channels['eventum.core.config_loader'] == 'server'
    assert capture.channels['some_library'] == 'server'


def test_mounted_app_rebinds_the_context(
    capture: ChannelCapture,
) -> None:
    """A mounted app attributes its requests to its own context."""
    app = FastAPI()
    app.mount(
        '/mcp',
        LogContextMiddleware(
            build_app({'component': 'mcp'}),
            context={'component': 'mcp'},
        ),
    )
    app.add_middleware(LogContextMiddleware, context={'component': 'server'})

    with TestClient(app) as client:
        assert client.get('/mcp/probe').status_code == 200

    assert capture.channels['eventum.core.config_loader'] == 'mcp'
    assert capture.channels['some_library'] == 'mcp'


def test_request_names_the_client_it_came_from() -> None:
    """Every record of a request carries the address of the caller."""
    with TestClient(build_app({'component': 'server'})) as client:
        context = client.get('/probe').json()

    assert context['component'] == 'server'
    assert context['client_host'] == 'testclient'


def test_captured_context_attributes_requests_to_a_generator(
    capture: ChannelCapture,
) -> None:
    """A server run by a generator attributes its requests to it."""
    structlog.contextvars.bind_contextvars(generator_id='gen-1')
    app = build_app(structlog.contextvars.get_contextvars())
    structlog.contextvars.clear_contextvars()

    with TestClient(app) as client:
        assert client.get('/probe').status_code == 200

    assert capture.channels['eventum.core.config_loader'] == 'generator_gen-1'
    assert capture.channels['some_library'] == 'generator_gen-1'
