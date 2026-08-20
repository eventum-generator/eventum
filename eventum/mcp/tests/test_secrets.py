"""Tests for the secret-introspection tool."""

from pathlib import Path

import pytest

from eventum.app.repositories import Repository
from eventum.mcp.context import FileAuthoringContext
from eventum.mcp.errors import ToolFailure
from eventum.mcp.tools import secrets


def _ctx(tmp_path: Path) -> FileAuthoringContext:
    return FileAuthoringContext(
        generators_dir=tmp_path,
        read_only=False,
        repositories_file=tmp_path / 'repositories.yml',
    )


def _connect(
    context: FileAuthoringContext,
    name: str,
    secret: str,
) -> None:
    context.repositories.add(
        Repository(
            name=name,
            url=f'https://git.example.com/{name}.git',
            secret=secret,
        ),
        verify=False,
    )


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

    assert result == {'projects': ['gen-a', 'gen-b'], 'repositories': []}


async def test_list_secret_references_reports_repositories(
    tmp_path: Path,
) -> None:
    """Repositories authenticating with the secret are listed too."""
    context = _ctx(tmp_path)
    _connect(context, 'internal', 'api_key')
    _connect(context, 'other', 'another_key')

    result = await secrets.list_secret_references(context, 'api_key')

    assert result == {'projects': [], 'repositories': ['internal']}


async def test_list_secret_references_none(tmp_path: Path) -> None:
    """Nothing referring to the secret yields two empty lists."""
    result = await secrets.list_secret_references(_ctx(tmp_path), 'api_key')

    assert result == {'projects': [], 'repositories': []}


async def test_list_secret_references_unreadable_repositories(
    tmp_path: Path,
) -> None:
    """Repositories that cannot be read are reported, not answered as none."""
    context = _ctx(tmp_path)
    (tmp_path / 'repositories.yml').write_text('name: broken\n')

    result = await secrets.list_secret_references(context, 'api_key')

    assert isinstance(result, ToolFailure)
    assert result.error == 'Repositories file root is not a YAML list'
    # The list sits beside the generators directory, so what names it
    # is its own name and never the path to it.
    assert result.details['file_path'] == 'repositories.yml'
    assert 'projects' not in result.details
