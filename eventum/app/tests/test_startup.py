"""Tests for the Startup module."""

from pathlib import Path

import pytest
import yaml

from eventum.app.models.parameters.log import LogParameters
from eventum.app.models.parameters.path import PathParameters
from eventum.app.models.parameters.server import ServerParameters
from eventum.app.models.settings import Settings
from eventum.app.models.startup import StartupGeneratorParameters
from eventum.app.startup import (
    Startup,
    StartupConflictError,
    StartupFileError,
    StartupFormatError,
    StartupNotFoundError,
)
from eventum.core.parameters import GenerationParameters


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """Build a minimal Settings pointing at tmp_path."""
    (tmp_path / 'generators').mkdir()
    return Settings(
        server=ServerParameters(),
        generation=GenerationParameters(),
        log=LogParameters(),
        path=PathParameters(
            logs=tmp_path / 'logs',
            startup=tmp_path / 'startup.yml',
            generators_dir=tmp_path / 'generators',
            keyring_cryptfile=tmp_path / 'keyring.cfg',
        ),
    )


@pytest.fixture
def startup(settings: Settings) -> Startup:
    """Build Startup bound to the fixture Settings."""
    return Startup(settings=settings)


def _write_startup(settings: Settings, content: str) -> None:
    settings.path.startup.write_text(content)


def _read_startup(settings: Settings) -> str:
    return settings.path.startup.read_text()


def test_get_all_returns_empty_list_for_empty_file(
    startup: Startup,
    settings: Settings,
) -> None:
    """Empty startup file yields empty parameters list."""
    _write_startup(settings, '')

    result = startup.get_all()

    assert result.root == ()  # noqa: S101


def test_get_all_normalizes_relative_paths_to_absolute(
    startup: Startup,
    settings: Settings,
) -> None:
    """Relative paths in the file are returned absolute."""
    _write_startup(
        settings,
        '- id: gen-1\n  path: gen-1/generator.yml\n',
    )

    result = startup.get_all()

    assert len(result.root) == 1  # noqa: S101
    params = result.root[0]
    assert params.id == 'gen-1'  # noqa: S101
    assert params.path == settings.path.generators_dir / 'gen-1/generator.yml'  # noqa: S101
    assert params.path.is_absolute()  # noqa: S101


def test_get_all_keeps_absolute_paths_as_is(
    startup: Startup,
    settings: Settings,
    tmp_path: Path,
) -> None:
    """Absolute paths in the file pass through unchanged."""
    absolute = tmp_path / 'outside' / 'gen.yml'
    _write_startup(
        settings,
        f'- id: gen-1\n  path: {absolute}\n',
    )

    result = startup.get_all()

    assert result.root[0].path == absolute  # noqa: S101


def test_get_all_applies_generation_defaults(
    startup: Startup,
    settings: Settings,
) -> None:
    """Missing fields fall back to settings.generation defaults."""
    _write_startup(
        settings,
        '- id: gen-1\n  path: gen-1/generator.yml\n',
    )

    result = startup.get_all()

    params = result.root[0]
    assert params.timezone == settings.generation.timezone  # noqa: S101
    assert params.keep_order == settings.generation.keep_order  # noqa: S101


def test_get_all_raises_file_error_when_file_missing(
    startup: Startup,
) -> None:
    """Missing startup file raises StartupFileError."""
    with pytest.raises(StartupFileError) as exc:
        startup.get_all()

    assert 'file_path' in exc.value.context  # noqa: S101
    assert 'reason' in exc.value.context  # noqa: S101


def test_get_all_raises_format_error_on_invalid_yaml(
    startup: Startup,
    settings: Settings,
) -> None:
    """Malformed YAML raises StartupFormatError."""
    _write_startup(settings, '- id: gen-1\n  path: [unclosed')

    with pytest.raises(StartupFormatError) as exc:
        startup.get_all()

    assert exc.value.context['file_path'] == str(settings.path.startup)  # noqa: S101


def test_get_all_raises_format_error_when_top_level_not_list(
    startup: Startup,
    settings: Settings,
) -> None:
    """Top-level mapping instead of list raises StartupFormatError."""
    _write_startup(settings, 'id: gen-1\npath: gen-1/generator.yml\n')

    with pytest.raises(StartupFormatError):
        startup.get_all()


def test_get_all_raises_format_error_on_validation_failure(
    startup: Startup,
    settings: Settings,
) -> None:
    """Missing required fields raise StartupFormatError."""
    _write_startup(settings, '- path: gen-1/generator.yml\n')

    with pytest.raises(StartupFormatError) as exc:
        startup.get_all()

    assert 'reason' in exc.value.context  # noqa: S101


def test_get_returns_entry_by_id(
    startup: Startup,
    settings: Settings,
) -> None:
    """Existing id returns the matching entry."""
    _write_startup(
        settings,
        '- id: gen-1\n  path: gen-1/generator.yml\n'
        '- id: gen-2\n  path: gen-2/generator.yml\n',
    )

    result = startup.get('gen-2')

    assert result.id == 'gen-2'  # noqa: S101
    assert result.path == settings.path.generators_dir / 'gen-2/generator.yml'  # noqa: S101


def test_get_raises_not_found_for_unknown_id(
    startup: Startup,
    settings: Settings,
) -> None:
    """Unknown id raises StartupNotFoundError."""
    _write_startup(settings, '- id: gen-1\n  path: gen-1/generator.yml\n')

    with pytest.raises(StartupNotFoundError) as exc:
        startup.get('missing')

    assert exc.value.context['value'] == 'missing'  # noqa: S101


def test_add_appends_entry_with_id_first(
    startup: Startup,
    settings: Settings,
) -> None:
    """New entry is appended with 'id' as the first key."""
    _write_startup(settings, '- id: gen-1\n  path: gen-1/generator.yml\n')

    new = StartupGeneratorParameters(
        id='gen-2',
        path=Path('gen-2/generator.yml'),
    )
    startup.add(new)

    dumped = yaml.safe_load(_read_startup(settings))
    assert len(dumped) == 2  # noqa: S101, PLR2004
    assert next(iter(dumped[1].keys())) == 'id'  # noqa: S101
    assert dumped[1]['id'] == 'gen-2'  # noqa: S101


def test_add_normalizes_relative_input_path_to_absolute(
    startup: Startup,
    settings: Settings,
) -> None:
    """Relative input path is stored as absolute."""
    _write_startup(settings, '[]\n')

    new = StartupGeneratorParameters(
        id='gen-1',
        path=Path('gen-1/generator.yml'),
    )
    startup.add(new)

    dumped = yaml.safe_load(_read_startup(settings))
    expected = settings.path.generators_dir / 'gen-1/generator.yml'
    assert dumped[0]['path'] == str(expected)  # noqa: S101


def test_add_raises_conflict_on_duplicate_id(
    startup: Startup,
    settings: Settings,
) -> None:
    """Adding a duplicate id raises StartupConflictError."""
    _write_startup(settings, '- id: gen-1\n  path: gen-1/generator.yml\n')

    new = StartupGeneratorParameters(
        id='gen-1',
        path=Path('gen-1/other.yml'),
    )
    with pytest.raises(StartupConflictError) as exc:
        startup.add(new)

    assert exc.value.context['value'] == 'gen-1'  # noqa: S101


def test_update_replaces_entry_and_preserves_other_entries(
    startup: Startup,
    settings: Settings,
) -> None:
    """Updating one entry leaves others byte-identical."""
    original = (
        '- id: gen-1\n'
        '  path: gen-1/generator.yml\n'
        '- id: gen-2\n'
        '  path: gen-2/generator.yml\n'
        '  timezone: Europe/Moscow\n'
    )
    _write_startup(settings, original)

    updated = StartupGeneratorParameters(
        id='gen-1',
        path=Path('gen-1/new.yml'),
    )
    startup.update(updated)

    dumped = yaml.safe_load(_read_startup(settings))
    assert dumped[0]['id'] == 'gen-1'  # noqa: S101
    assert dumped[0]['path'].endswith('gen-1/new.yml')  # noqa: S101
    assert dumped[1] == {  # noqa: S101
        'id': 'gen-2',
        'path': 'gen-2/generator.yml',
        'timezone': 'Europe/Moscow',
    }


def test_update_raises_not_found_for_unknown_id(
    startup: Startup,
    settings: Settings,
) -> None:
    """Updating unknown id raises StartupNotFoundError."""
    _write_startup(settings, '- id: gen-1\n  path: gen-1/generator.yml\n')

    params = StartupGeneratorParameters(
        id='missing',
        path=Path('missing/generator.yml'),
    )
    with pytest.raises(StartupNotFoundError):
        startup.update(params)


def test_delete_removes_entry(
    startup: Startup,
    settings: Settings,
) -> None:
    """Delete removes the target and keeps others."""
    _write_startup(
        settings,
        '- id: gen-1\n  path: gen-1/generator.yml\n'
        '- id: gen-2\n  path: gen-2/generator.yml\n',
    )

    startup.delete('gen-1')

    dumped = yaml.safe_load(_read_startup(settings))
    assert len(dumped) == 1  # noqa: S101
    assert dumped[0]['id'] == 'gen-2'  # noqa: S101


def test_delete_raises_not_found_for_unknown_id(
    startup: Startup,
    settings: Settings,
) -> None:
    """Deleting unknown id raises StartupNotFoundError."""
    _write_startup(settings, '- id: gen-1\n  path: gen-1/generator.yml\n')

    with pytest.raises(StartupNotFoundError):
        startup.delete('missing')


def test_bulk_delete_removes_existing_ids_and_returns_them(
    startup: Startup,
    settings: Settings,
) -> None:
    """Bulk delete returns ids that were present and removes them."""
    _write_startup(
        settings,
        '- id: gen-1\n  path: gen-1/generator.yml\n'
        '- id: gen-2\n  path: gen-2/generator.yml\n'
        '- id: gen-3\n  path: gen-3/generator.yml\n',
    )

    deleted = startup.bulk_delete(['gen-1', 'gen-3', 'missing'])

    assert deleted == ['gen-1', 'gen-3']  # noqa: S101
    dumped = yaml.safe_load(_read_startup(settings))
    assert [entry['id'] for entry in dumped] == ['gen-2']  # noqa: S101


def test_bulk_delete_empty_input_is_noop(
    startup: Startup,
    settings: Settings,
) -> None:
    """Empty ids iterable keeps the file intact."""
    original = '- id: gen-1\n  path: gen-1/generator.yml\n'
    _write_startup(settings, original)

    deleted = startup.bulk_delete([])

    assert deleted == []  # noqa: S101
    dumped = yaml.safe_load(_read_startup(settings))
    assert len(dumped) == 1  # noqa: S101
    assert dumped[0]['id'] == 'gen-1'  # noqa: S101


def test_mutations_refuse_to_touch_invalid_file(
    startup: Startup,
    settings: Settings,
) -> None:
    """Mutations raise StartupFormatError if the file is invalid,
    instead of silently propagating corrupt state.
    """
    # Missing required `id` in the second entry makes the file invalid.
    _write_startup(
        settings,
        '- id: gen-1\n  path: gen-1/generator.yml\n'
        '- path: gen-2/generator.yml\n',
    )

    new = StartupGeneratorParameters(
        id='gen-3',
        path=Path('gen-3/generator.yml'),
    )

    with pytest.raises(StartupFormatError):
        startup.add(new)

    with pytest.raises(StartupFormatError):
        startup.update(new)

    with pytest.raises(StartupFormatError):
        startup.delete('gen-1')

    with pytest.raises(StartupFormatError):
        startup.bulk_delete(['gen-1'])
