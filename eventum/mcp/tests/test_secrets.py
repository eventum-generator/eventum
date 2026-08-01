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


def _write_config(generators_dir: Path, name: str, content: str) -> None:
    config_path = generators_dir / name / 'generator.yml'
    config_path.parent.mkdir(parents=True)
    config_path.write_text(content)


async def test_list_secret_references_reports_projects(
    tmp_path: Path,
) -> None:
    """Projects whose config reads the secret are listed, sorted."""
    _write_config(tmp_path, 'gen-b', 'token: ${secrets.api_key}\n')
    _write_config(tmp_path, 'gen-a', 'token: ${secrets.api_key}\n')
    _write_config(tmp_path, 'gen-c', 'token: ${secrets.other}\n')

    result = await secrets.list_secret_references(_ctx(tmp_path), 'api_key')

    assert result == ['gen-a', 'gen-b']


async def test_list_secret_references_none(tmp_path: Path) -> None:
    """No referencing project yields an empty list."""
    assert (
        await secrets.list_secret_references(_ctx(tmp_path), 'api_key') == []
    )
