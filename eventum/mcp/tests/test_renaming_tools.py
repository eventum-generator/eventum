"""Tests for the MCP project and generator rename tools."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from eventum.app.manager import GeneratorManager
from eventum.app.renaming import (
    RenameConflictError,
    RenameError,
    RenameNotFoundError,
)
from eventum.app.secrets import UpdatedReferences
from eventum.app.startup import Startup
from eventum.core.parameters import GenerationParameters, GeneratorParameters
from eventum.mcp.context import ServerLiveContext
from eventum.mcp.errors import ToolFailure
from eventum.mcp.tools import renaming
from eventum.mcp.tools.renaming import (
    rename_generator,
    rename_generator_config,
)


class _FakeGenerator:
    """Stand-in for Generator that starts no thread."""

    def __init__(self, params: GeneratorParameters) -> None:
        self.params = params
        self.is_initializing = False
        self.is_running = False
        self.is_stopping = False


def _ctx(
    tmp_path: Path,
    *,
    read_only: bool = False,
    manager: GeneratorManager | None = None,
) -> ServerLiveContext:
    gens = tmp_path / 'generators'
    gens.mkdir(exist_ok=True)
    startup_file = tmp_path / 'startup.yml'
    if not startup_file.exists():
        startup_file.write_text('')

    return ServerLiveContext(
        generators_dir=gens,
        read_only=read_only,
        manager=manager if manager is not None else MagicMock(),
        startup=Startup(
            file_path=startup_file,
            generators_dir=gens,
            generation_parameters=GenerationParameters(),
        ),
        generation=GenerationParameters(),
        logs_dir=tmp_path,
        log_format='plain',
        settings=MagicMock(),
        hooks=MagicMock(),
        repositories=MagicMock(),
    )


def _manager() -> GeneratorManager:
    with patch('eventum.app.manager.Generator', new=_FakeGenerator):
        return GeneratorManager()


def _add(manager: GeneratorManager, id: str, path: Path) -> None:
    with patch('eventum.app.manager.Generator', new=_FakeGenerator):
        manager.add(GeneratorParameters(id=id, path=path))


def _make_project(generators_dir: Path, name: str) -> Path:
    project_dir = generators_dir / name
    project_dir.mkdir()
    (project_dir / 'generator.yml').write_text('input: []\n')
    return project_dir


# --- rename_generator_config ---


async def test_rename_project_moves_dir_and_repoints(tmp_path: Path) -> None:
    """The directory moves and the generators using it follow."""
    manager = _manager()
    ctx = _ctx(tmp_path, manager=manager)
    _make_project(ctx.generators_dir, 'old')
    (tmp_path / 'startup.yml').write_text(
        '- id: gen-1\n  path: old/generator.yml\n'
    )
    _add(manager, 'gen-1', ctx.generators_dir / 'old' / 'generator.yml')

    result = await rename_generator_config(ctx, 'old', 'new')

    assert result == {
        'name': 'old',
        'new_name': 'new',
        'renamed': True,
        'generator_ids': ['gen-1'],
    }
    assert (ctx.generators_dir / 'new' / 'generator.yml').is_file()
    assert yaml.safe_load((tmp_path / 'startup.yml').read_text()) == [
        {'id': 'gen-1', 'path': 'new/generator.yml'}
    ]


async def test_rename_project_missing_is_failure(tmp_path: Path) -> None:
    """An absent project returns a structured failure."""
    result = await rename_generator_config(_ctx(tmp_path), 'absent', 'new')

    assert isinstance(result, ToolFailure)
    assert result.details == {'name': 'absent'}


async def test_rename_project_taken_name_is_failure(tmp_path: Path) -> None:
    """A taken target name returns a failure and keeps the project."""
    ctx = _ctx(tmp_path)
    _make_project(ctx.generators_dir, 'old')
    _make_project(ctx.generators_dir, 'taken')

    result = await rename_generator_config(ctx, 'old', 'taken')

    assert isinstance(result, ToolFailure)
    assert result.details == {'name': 'taken'}
    assert (ctx.generators_dir / 'old').is_dir()


async def test_rename_project_active_generator_is_failure(
    tmp_path: Path,
) -> None:
    """An active generator blocks the rename."""
    manager = _manager()
    ctx = _ctx(tmp_path, manager=manager)
    _make_project(ctx.generators_dir, 'old')
    _add(manager, 'gen-1', ctx.generators_dir / 'old' / 'generator.yml')
    manager.get_generator('gen-1').is_running = True  # type: ignore[misc]

    result = await rename_generator_config(ctx, 'old', 'new')

    assert isinstance(result, ToolFailure)
    assert (ctx.generators_dir / 'old').is_dir()


async def test_rename_project_read_only_is_failure(tmp_path: Path) -> None:
    """A read-only server refuses the rename."""
    ctx = _ctx(tmp_path, read_only=True)
    _make_project(ctx.generators_dir, 'old')

    result = await rename_generator_config(ctx, 'old', 'new')

    assert isinstance(result, ToolFailure)
    assert result.details == {'name': 'old'}
    assert (ctx.generators_dir / 'old').is_dir()


async def test_rename_project_escaping_name_carries_no_path(
    tmp_path: Path,
) -> None:
    """A path-escaping name fails without leaking an absolute path."""
    ctx = _ctx(tmp_path)
    _make_project(ctx.generators_dir, 'old')

    result = await rename_generator_config(ctx, 'old', '../escape')

    assert isinstance(result, ToolFailure)
    assert '/' not in result.error or not result.error.startswith('/')
    assert str(tmp_path) not in str(result.details)


# --- rename_generator ---


async def test_rename_generator_renames_both_sides(tmp_path: Path) -> None:
    """The runtime generator and its startup entry are renamed."""
    manager = _manager()
    ctx = _ctx(tmp_path, manager=manager)
    (tmp_path / 'startup.yml').write_text(
        '- id: gen-1\n  path: proj/generator.yml\n  scenarios:\n    - alpha\n'
    )
    _add(manager, 'gen-1', ctx.generators_dir / 'proj' / 'generator.yml')

    result = await rename_generator(ctx, 'gen-1', 'renamed')

    assert result == {'id': 'gen-1', 'new_id': 'renamed', 'renamed': True}
    assert manager.generator_ids == ['renamed']
    assert yaml.safe_load((tmp_path / 'startup.yml').read_text()) == [
        {
            'id': 'renamed',
            'path': 'proj/generator.yml',
            'scenarios': ['alpha'],
        }
    ]


async def test_rename_generator_missing_is_failure(tmp_path: Path) -> None:
    """An unknown generator returns a failure keyed as id."""
    result = await rename_generator(
        _ctx(tmp_path, manager=_manager()), 'x', 'y'
    )

    assert isinstance(result, ToolFailure)
    assert result.details == {'id': 'x'}


async def test_rename_generator_taken_id_is_failure(tmp_path: Path) -> None:
    """A taken id returns a failure and changes nothing."""
    manager = _manager()
    ctx = _ctx(tmp_path, manager=manager)
    _add(manager, 'gen-1', ctx.generators_dir / 'proj' / 'generator.yml')
    _add(manager, 'gen-2', ctx.generators_dir / 'proj' / 'generator.yml')

    result = await rename_generator(ctx, 'gen-1', 'gen-2')

    assert isinstance(result, ToolFailure)
    assert result.details == {'id': 'gen-1'}
    assert manager.generator_ids == ['gen-1', 'gen-2']


async def test_rename_generator_active_is_failure(tmp_path: Path) -> None:
    """An active generator cannot be renamed."""
    manager = _manager()
    ctx = _ctx(tmp_path, manager=manager)
    _add(manager, 'gen-1', ctx.generators_dir / 'proj' / 'generator.yml')
    manager.get_generator('gen-1').is_initializing = True  # type: ignore[misc]

    result = await rename_generator(ctx, 'gen-1', 'renamed')

    assert isinstance(result, ToolFailure)
    assert manager.generator_ids == ['gen-1']


async def test_rename_generator_read_only_is_failure(tmp_path: Path) -> None:
    """A read-only server refuses the rename."""
    manager = _manager()
    ctx = _ctx(tmp_path, read_only=True, manager=manager)
    _add(manager, 'gen-1', ctx.generators_dir / 'proj' / 'generator.yml')

    result = await rename_generator(ctx, 'gen-1', 'renamed')

    assert isinstance(result, ToolFailure)
    assert result.details == {'id': 'gen-1'}
    assert manager.generator_ids == ['gen-1']


# --- rename_secret ---


async def test_rename_secret_moves_value(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Renaming delegates to the service and reports what it touched."""
    calls: list[tuple[str, str]] = []

    def _rename(
        *,
        generators_dir: object,
        config_filename: object,
        repositories: object,
        name: str,
        new_name: str,
    ) -> UpdatedReferences:
        calls.append((name, new_name))
        return UpdatedReferences(
            projects=['web-nginx'], repositories=['internal']
        )

    monkeypatch.setattr(renaming, 'rename_secret', _rename)

    result = await renaming.rename_secret_name(_ctx(tmp_path), 'old', 'new')

    assert result == {
        'name': 'old',
        'new_name': 'new',
        'renamed': True,
        'projects': ['web-nginx'],
        'repositories': ['internal'],
    }
    assert calls == [('old', 'new')]


async def test_rename_secret_missing_is_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An absent secret returns a structured failure."""

    def _rename(
        *,
        generators_dir: object,
        config_filename: object,
        repositories: object,
        name: str,
        new_name: str,
    ) -> UpdatedReferences:
        raise RenameNotFoundError('Secret is missing', context={})

    monkeypatch.setattr(renaming, 'rename_secret', _rename)

    result = await renaming.rename_secret_name(_ctx(tmp_path), 'old', 'new')

    assert isinstance(result, ToolFailure)
    assert result.error == 'Secret not found'
    assert result.details == {'name': 'old'}


async def test_rename_secret_taken_name_is_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A taken target name returns a structured failure."""

    def _rename(
        *,
        generators_dir: object,
        config_filename: object,
        repositories: object,
        name: str,
        new_name: str,
    ) -> UpdatedReferences:
        raise RenameConflictError(
            'Secret with this name already exists',
            context={},
        )

    monkeypatch.setattr(renaming, 'rename_secret', _rename)

    result = await renaming.rename_secret_name(_ctx(tmp_path), 'old', 'new')

    assert isinstance(result, ToolFailure)
    assert result.error == 'Secret with this name already exists'
    assert result.details == {'name': 'new'}


async def test_rename_secret_names_the_repositories_holding_the_name(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A name a repository holds is refused, and the holder is named."""

    def _rename(
        *,
        generators_dir: object,
        config_filename: object,
        repositories: object,
        name: str,
        new_name: str,
    ) -> UpdatedReferences:
        raise RenameConflictError(
            'Repositories already authenticate with the new name',
            context={'secret': 'new', 'reason': 'github, mirror'},
        )

    monkeypatch.setattr(renaming, 'rename_secret', _rename)

    result = await renaming.rename_secret_name(_ctx(tmp_path), 'old', 'new')

    assert isinstance(result, ToolFailure)
    assert (
        result.error == 'Repositories already authenticate with the new name'
    )
    assert result.details == {'name': 'new', 'reason': 'github, mirror'}


async def test_rename_secret_keyring_error_carries_no_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failure names what happened without the reason behind it."""

    def _rename(
        *,
        generators_dir: object,
        config_filename: object,
        repositories: object,
        name: str,
        new_name: str,
    ) -> UpdatedReferences:
        raise RenameError(
            'Failed to rename secret',
            context={'reason': 'cannot write /abs/keyring/cryptfile.cfg'},
        )

    monkeypatch.setattr(renaming, 'rename_secret', _rename)

    result = await renaming.rename_secret_name(_ctx(tmp_path), 'old', 'new')

    assert isinstance(result, ToolFailure)
    assert result.error == 'Failed to rename secret'
    assert result.details == {'name': 'old'}


async def test_rename_secret_reports_repositories_left_behind(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A repointing that failed is named, so the agent can act on it."""

    def _rename(
        *,
        generators_dir: object,
        config_filename: object,
        repositories: object,
        name: str,
        new_name: str,
    ) -> UpdatedReferences:
        raise RenameError(
            'Repositories using the secret cannot be repointed',
            context={'file_path': '/abs/instance/repositories.yml'},
        )

    monkeypatch.setattr(renaming, 'rename_secret', _rename)

    result = await renaming.rename_secret_name(_ctx(tmp_path), 'old', 'new')

    assert isinstance(result, ToolFailure)
    assert result.error == 'Repositories using the secret cannot be repointed'
    assert result.details == {'name': 'old'}


async def test_rename_secret_read_only_is_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A read-only server refuses the rename, not touching the keyring."""

    def _rename(name: str, new_name: str) -> None:
        msg = 'must not be called'
        raise AssertionError(msg)

    monkeypatch.setattr(renaming, 'rename_secret', _rename)
    result = await renaming.rename_secret_name(
        _ctx(tmp_path, read_only=True), 'old', 'new'
    )

    assert isinstance(result, ToolFailure)
    assert result.details == {'name': 'old'}
