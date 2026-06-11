"""Shared fixtures for MCP service tests."""

from pathlib import Path

import pytest

from eventum.app.models.parameters.log import LogParameters
from eventum.app.models.parameters.path import PathParameters
from eventum.app.models.parameters.server import (
    MCPParameters,
    ServerParameters,
)
from eventum.app.models.settings import Settings
from eventum.core.parameters import GenerationParameters


@pytest.fixture
def mcp_settings(tmp_path: Path) -> Settings:
    """Return MCP-enabled Settings rooted under tmp_path."""
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
