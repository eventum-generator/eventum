"""Tests for cross-object rename operations."""

from collections.abc import Iterator
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from eventum.app.manager import GeneratorManager
from eventum.app.renaming import (
    RenameBlockedError,
    RenameConflictError,
    RenameError,
    RenameNotFoundError,
    rename_instance,
    rename_project,
)
from eventum.app.startup import Startup
from eventum.core.parameters import GenerationParameters, GeneratorParameters


class _FakeGenerator:
    """Stand-in for Generator that starts no thread."""

    def __init__(self, params: GeneratorParameters) -> None:
        self.params = params
        self.is_initializing = False
        self.is_running = False
        self.is_stopping = False


@pytest.fixture
def generators_dir(tmp_path: Path) -> Path:
    """Base directory holding project directories."""
    path = tmp_path / 'generators'
    path.mkdir()
    return path


@pytest.fixture
def startup_file(tmp_path: Path) -> Path:
    """Path of the startup file."""
    return tmp_path / 'startup.yml'


@pytest.fixture
def startup(generators_dir: Path, startup_file: Path) -> Startup:
    """Startup service over an empty startup file."""
    startup_file.write_text('')
    return Startup(
        file_path=startup_file,
        generators_dir=generators_dir,
        generation_parameters=GenerationParameters(),
    )


@pytest.fixture
def manager() -> Iterator[GeneratorManager]:
    """Manager building fake generators instead of real ones."""
    with patch('eventum.app.manager.Generator', new=_FakeGenerator):
        yield GeneratorManager()


def _make_project(generators_dir: Path, name: str) -> None:
    """Create a project directory with a configuration file."""
    project_dir = generators_dir / name
    project_dir.mkdir()
    (project_dir / 'generator.yml').write_text('input: []\n')


def _params(
    generators_dir: Path, id: str, project: str
) -> GeneratorParameters:
    """Build generator parameters pointing at a project."""
    return GeneratorParameters(
        id=id,
        path=generators_dir / project / 'generator.yml',
    )


def _entries(startup_file: Path) -> list[dict]:
    """Read raw entries of the startup file."""
    return yaml.safe_load(startup_file.read_text()) or []


# --- rename_project ---


def test_rename_project_renames_dir_and_repoints_instances(
    manager: GeneratorManager,
    startup: Startup,
    generators_dir: Path,
    startup_file: Path,
) -> None:
    """The directory moves and every user of it follows."""
    _make_project(generators_dir, 'old')
    startup_file.write_text(
        '- id: gen-1\n  path: old/generator.yml\n'
        '- id: gen-2\n  path: other/generator.yml\n'
    )
    manager.add(_params(generators_dir, 'gen-1', 'old'))
    manager.add(_params(generators_dir, 'gen-2', 'other'))

    affected = rename_project(
        manager=manager,
        startup=startup,
        generators_dir=generators_dir,
        name='old',
        new_name='new',
    )

    assert affected == ['gen-1']
    assert (generators_dir / 'new' / 'generator.yml').is_file()
    assert not (generators_dir / 'old').exists()
    assert _entries(startup_file)[0]['path'] == 'new/generator.yml'
    assert manager.get_generator('gen-1').params.path == (
        generators_dir / 'new' / 'generator.yml'
    )
    assert manager.get_generator('gen-2').params.path == (
        generators_dir / 'other' / 'generator.yml'
    )


def test_rename_project_without_instances(
    manager: GeneratorManager,
    startup: Startup,
    generators_dir: Path,
) -> None:
    """A project nobody uses renames with an empty affected list."""
    _make_project(generators_dir, 'old')

    affected = rename_project(
        manager=manager,
        startup=startup,
        generators_dir=generators_dir,
        name='old',
        new_name='new',
    )

    assert affected == []
    assert (generators_dir / 'new').is_dir()


def test_rename_project_missing_raises(
    manager: GeneratorManager,
    startup: Startup,
    generators_dir: Path,
) -> None:
    """Renaming an absent project raises."""
    with pytest.raises(RenameNotFoundError):
        rename_project(
            manager=manager,
            startup=startup,
            generators_dir=generators_dir,
            name='absent',
            new_name='new',
        )


def test_rename_project_taken_name_raises(
    manager: GeneratorManager,
    startup: Startup,
    generators_dir: Path,
) -> None:
    """Renaming onto an existing project raises and changes nothing."""
    _make_project(generators_dir, 'old')
    _make_project(generators_dir, 'taken')

    with pytest.raises(RenameConflictError):
        rename_project(
            manager=manager,
            startup=startup,
            generators_dir=generators_dir,
            name='old',
            new_name='taken',
        )

    assert (generators_dir / 'old').is_dir()


def test_rename_project_active_instance_raises(
    manager: GeneratorManager,
    startup: Startup,
    generators_dir: Path,
) -> None:
    """An active instance blocks the rename and nothing changes."""
    _make_project(generators_dir, 'old')
    manager.add(_params(generators_dir, 'gen-1', 'old'))
    manager.get_generator('gen-1').is_running = True  # type: ignore[misc]

    with pytest.raises(RenameBlockedError) as exc:
        rename_project(
            manager=manager,
            startup=startup,
            generators_dir=generators_dir,
            name='old',
            new_name='new',
        )

    assert exc.value.context['generator_ids'] == ['gen-1']
    assert (generators_dir / 'old').is_dir()


def test_rename_project_escaping_name_raises(
    manager: GeneratorManager,
    startup: Startup,
    generators_dir: Path,
) -> None:
    """A new name outside the generators directory is refused."""
    _make_project(generators_dir, 'old')

    with pytest.raises(RenameError):
        rename_project(
            manager=manager,
            startup=startup,
            generators_dir=generators_dir,
            name='old',
            new_name='../escape',
        )

    assert (generators_dir / 'old').is_dir()


def test_rename_project_reverts_dir_when_startup_fails(
    manager: GeneratorManager,
    startup: Startup,
    generators_dir: Path,
    startup_file: Path,
) -> None:
    """A broken startup file leaves the directory under its old name."""
    _make_project(generators_dir, 'old')
    startup_file.write_text('- id: gen-1\n')

    with pytest.raises(RenameError):
        rename_project(
            manager=manager,
            startup=startup,
            generators_dir=generators_dir,
            name='old',
            new_name='new',
        )

    assert (generators_dir / 'old').is_dir()
    assert not (generators_dir / 'new').exists()


# --- rename_instance ---


def test_rename_instance_in_manager_and_startup(
    manager: GeneratorManager,
    startup: Startup,
    generators_dir: Path,
    startup_file: Path,
) -> None:
    """Both the managed generator and its entry are renamed."""
    startup_file.write_text(
        '- id: gen-1\n  path: proj/generator.yml\n  scenarios:\n    - alpha\n'
    )
    manager.add(_params(generators_dir, 'gen-1', 'proj'))

    rename_instance(
        manager=manager,
        startup=startup,
        id='gen-1',
        new_id='renamed',
    )

    assert manager.generator_ids == ['renamed']
    assert manager.get_generator('renamed').params.id == 'renamed'
    assert _entries(startup_file)[0] == {
        'id': 'renamed',
        'path': 'proj/generator.yml',
        'scenarios': ['alpha'],
    }


def test_rename_instance_in_startup_only(
    manager: GeneratorManager,
    startup: Startup,
    startup_file: Path,
) -> None:
    """An entry with no managed generator is renamed on its own."""
    startup_file.write_text('- id: gen-1\n  path: proj/generator.yml\n')

    rename_instance(
        manager=manager,
        startup=startup,
        id='gen-1',
        new_id='renamed',
    )

    assert _entries(startup_file)[0]['id'] == 'renamed'
    assert manager.generator_ids == []


def test_rename_instance_in_manager_only(
    manager: GeneratorManager,
    startup: Startup,
    generators_dir: Path,
    startup_file: Path,
) -> None:
    """A generator with no entry is renamed on its own."""
    manager.add(_params(generators_dir, 'gen-1', 'proj'))

    rename_instance(
        manager=manager,
        startup=startup,
        id='gen-1',
        new_id='renamed',
    )

    assert manager.generator_ids == ['renamed']
    assert _entries(startup_file) == []


def test_rename_instance_missing_raises(
    manager: GeneratorManager,
    startup: Startup,
) -> None:
    """Renaming an unknown instance raises."""
    with pytest.raises(RenameNotFoundError):
        rename_instance(
            manager=manager,
            startup=startup,
            id='absent',
            new_id='renamed',
        )


def test_rename_instance_taken_managed_id_raises(
    manager: GeneratorManager,
    startup: Startup,
    generators_dir: Path,
) -> None:
    """A managed generator already holding the new id blocks rename."""
    manager.add(_params(generators_dir, 'gen-1', 'proj'))
    manager.add(_params(generators_dir, 'gen-2', 'proj'))

    with pytest.raises(RenameConflictError):
        rename_instance(
            manager=manager,
            startup=startup,
            id='gen-1',
            new_id='gen-2',
        )

    assert manager.generator_ids == ['gen-1', 'gen-2']


def test_rename_instance_taken_defined_id_raises(
    manager: GeneratorManager,
    startup: Startup,
    startup_file: Path,
) -> None:
    """An entry already holding the new id blocks rename."""
    original = (
        '- id: gen-1\n  path: proj/generator.yml\n'
        '- id: gen-2\n  path: proj/generator.yml\n'
    )
    startup_file.write_text(original)

    with pytest.raises(RenameConflictError):
        rename_instance(
            manager=manager,
            startup=startup,
            id='gen-1',
            new_id='gen-2',
        )

    assert startup_file.read_text() == original


def test_rename_instance_active_raises(
    manager: GeneratorManager,
    startup: Startup,
    generators_dir: Path,
    startup_file: Path,
) -> None:
    """An active instance cannot be renamed and nothing changes."""
    startup_file.write_text('- id: gen-1\n  path: proj/generator.yml\n')
    manager.add(_params(generators_dir, 'gen-1', 'proj'))
    manager.get_generator('gen-1').is_initializing = True  # type: ignore[misc]

    with pytest.raises(RenameBlockedError):
        rename_instance(
            manager=manager,
            startup=startup,
            id='gen-1',
            new_id='renamed',
        )

    assert manager.generator_ids == ['gen-1']
    assert _entries(startup_file)[0]['id'] == 'gen-1'
