"""Tests for the secret-introspection tool."""

from pathlib import Path

import pytest

from eventum.mcp.context import FileAuthoringContext
from eventum.mcp.errors import ToolFailure
from eventum.mcp.tools import secrets


def _ctx(tmp_path: Path) -> FileAuthoringContext:
    return FileAuthoringContext(generators_dir=tmp_path, read_only=False)


def test_list_secret_names_sorted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Names from the keyring are returned sorted."""
    monkeypatch.setattr(secrets, 'list_secrets', lambda: ['b', 'a'])
    assert secrets.list_secret_names(_ctx(tmp_path)) == ['a', 'b']


def test_list_secret_names_empty(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No secrets yields an empty list."""
    monkeypatch.setattr(secrets, 'list_secrets', list)
    assert secrets.list_secret_names(_ctx(tmp_path)) == []


def test_list_secret_names_failure_is_tool_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A keyring read error becomes a path-free ToolFailure."""

    def _boom() -> list[str]:
        detail = 'cannot read /abs/keyring/cryptfile.cfg'
        raise OSError(detail)

    monkeypatch.setattr(secrets, 'list_secrets', _boom)
    result = secrets.list_secret_names(_ctx(tmp_path))
    assert isinstance(result, ToolFailure)
    assert result.error == 'Failed to read keyring'
    assert result.details == {}
