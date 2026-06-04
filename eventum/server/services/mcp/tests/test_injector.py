"""Tests for the MCP HTTP service injector."""

from pathlib import Path
from unittest.mock import MagicMock

from starlette.routing import Mount

from eventum.app.models.parameters.log import LogParameters
from eventum.app.models.parameters.path import PathParameters
from eventum.app.models.parameters.server import (
    MCPParameters,
    ServerParameters,
)
from eventum.app.models.settings import Settings
from eventum.core.parameters import GenerationParameters
from eventum.server.main import build_server_app
from eventum.server.services.mcp.injector import inject_service


def _settings(tmp_path: Path) -> Settings:
    (tmp_path / 'generators').mkdir()
    return Settings(
        server=ServerParameters(mcp=MCPParameters(enabled=True)),
        generation=GenerationParameters(),
        log=LogParameters(),
        path=PathParameters(
            logs=tmp_path / 'logs',
            startup=tmp_path / 'startup.yml',
            generators_dir=tmp_path / 'generators',
            keyring_cryptfile=tmp_path / 'keyring.cfg',
        ),
    )


def test_inject_mounts_and_registers_lifespan(tmp_path: Path) -> None:
    """The injector mounts at the configured path and registers a CM."""
    settings = _settings(tmp_path)
    app = build_server_app(
        enabled_services={},
        generator_manager=MagicMock(),
        settings=settings,
        instance_hooks=MagicMock(),  # type: ignore[arg-type]
    )

    inject_service(app, MagicMock(), settings)

    assert len(app.state.lifespan_cms) == 1
    mounts = [r for r in app.routes if isinstance(r, Mount)]
    assert any(m.path == '/mcp' for m in mounts)
