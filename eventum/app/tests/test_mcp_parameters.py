"""Tests for MCPParameters."""

import pytest
from pydantic import ValidationError

from eventum.app.models.parameters.server import (
    MCPParameters,
    ServerParameters,
)


def test_mcp_parameters_defaults() -> None:
    """MCP is disabled, read-only, and mounted at /mcp by default."""
    params = MCPParameters()
    assert params.enabled is False
    assert params.allow_write is False
    assert params.path == '/mcp'


def test_mcp_parameters_custom_path() -> None:
    """A custom mount path is accepted."""
    assert MCPParameters(path='/agent').path == '/agent'


def test_mcp_parameters_rejects_unknown_field() -> None:
    """Unknown fields are forbidden."""
    with pytest.raises(ValidationError):
        MCPParameters(unknown=True)  # type: ignore[call-arg]


def test_server_parameters_includes_mcp_defaults() -> None:
    """ServerParameters exposes nested MCP defaults."""
    assert ServerParameters().mcp.enabled is False
