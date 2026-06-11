"""Tests for the MCP HTTP service injector."""

from http import HTTPStatus
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from starlette.routing import Mount
from starlette.testclient import TestClient

from eventum.app.models.settings import Settings
from eventum.server.main import build_server_app
from eventum.server.services.mcp.injector import inject_service


def _make_app(settings: Settings) -> FastAPI:
    return build_server_app(
        enabled_services={},
        generator_manager=MagicMock(),
        settings=settings,
        instance_hooks=MagicMock(),  # type: ignore[arg-type]
        startup=MagicMock(),
    )


def _with_allowed_hosts(settings: Settings, hosts: list[str]) -> Settings:
    mcp = settings.server.mcp.model_copy(update={'allowed_hosts': hosts})
    server = settings.server.model_copy(update={'mcp': mcp})
    return settings.model_copy(update={'server': server})


def test_inject_mounts_and_registers_lifespan(
    mcp_settings: Settings,
) -> None:
    """The injector mounts at the configured path and registers a CM."""
    settings = mcp_settings
    app = _make_app(settings)

    inject_service(app, MagicMock(), settings, MagicMock())

    assert len(app.state.lifespan_cms) == 1
    mounts = [r for r in app.routes if isinstance(r, Mount)]
    assert any(m.path == '/mcp' for m in mounts)


def test_inject_redirects_slashless_path(mcp_settings: Settings) -> None:
    """The configured slashless path redirects to the mount root."""
    app = _make_app(mcp_settings)

    inject_service(app, MagicMock(), mcp_settings, MagicMock())

    client = TestClient(app)
    response = client.post('/mcp', follow_redirects=False)
    assert response.status_code == HTTPStatus.TEMPORARY_REDIRECT
    assert response.headers['location'].endswith('/mcp/')


def test_inject_threads_config_filename_into_context(
    mcp_settings: Settings,
) -> None:
    """The configured generator config filename reaches the context."""
    path = mcp_settings.path.model_copy(
        update={'generator_config_filename': Path('custom.yml')},
    )
    settings = mcp_settings.model_copy(update={'path': path})
    app = _make_app(settings)

    with patch(
        'eventum.server.services.mcp.injector.build_server',
    ) as mock_build:
        inject_service(app, MagicMock(), settings, MagicMock())

    context = mock_build.call_args.args[0]
    assert context.config_filename == 'custom.yml'


def test_inject_disables_protection_without_hosts(
    mcp_settings: Settings,
) -> None:
    """Empty allowed hosts leave DNS-rebinding protection disabled."""
    app = _make_app(mcp_settings)

    with patch(
        'eventum.server.services.mcp.injector.build_server',
    ) as mock_build:
        inject_service(app, MagicMock(), mcp_settings, MagicMock())

    security = mock_build.return_value.settings.transport_security
    assert security.enable_dns_rebinding_protection is False
    assert security.allowed_hosts == []
    assert security.allowed_origins == []


def test_inject_derives_origins_from_allowed_hosts(
    mcp_settings: Settings,
) -> None:
    """Allowed hosts also produce a matching Origin allowlist.

    The SDK rejects every Origin-bearing request when protection is
    enabled with an empty origin allowlist, so the injector must
    derive origins from the configured hosts.
    """
    settings = _with_allowed_hosts(
        mcp_settings,
        ['localhost:9474', '127.0.0.1:*'],
    )
    app = _make_app(settings)

    with patch(
        'eventum.server.services.mcp.injector.build_server',
    ) as mock_build:
        inject_service(app, MagicMock(), settings, MagicMock())

    security = mock_build.return_value.settings.transport_security
    assert security.enable_dns_rebinding_protection is True
    assert security.allowed_hosts == ['localhost:9474', '127.0.0.1:*']
    assert security.allowed_origins == [
        'http://localhost:9474',
        'https://localhost:9474',
        'http://127.0.0.1:*',
        'https://127.0.0.1:*',
    ]
