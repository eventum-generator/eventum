"""Tests for the Startup service scenario operations."""

from pathlib import Path

import pytest
import yaml

from eventum.app.models.parameters.log import LogParameters
from eventum.app.models.parameters.path import PathParameters
from eventum.app.models.parameters.server import ServerParameters
from eventum.app.models.settings import Settings
from eventum.app.startup import (
    ScenarioConflictError,
    ScenarioNotFoundError,
    Startup,
    StartupNotFoundError,
)
from eventum.core.parameters import GenerationParameters

_TWO_GENERATORS = (
    '- id: gen-1\n'
    '  path: gen-1/generator.yml\n'
    '  scenarios:\n'
    '    - alpha\n'
    '    - beta\n'
    '- id: gen-2\n'
    '  path: gen-2/generator.yml\n'
    '  scenarios:\n'
    '    - beta\n'
)

_ONE_UNTAGGED = '- id: gen-1\n  path: gen-1/generator.yml\n'


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
    """Build Startup wired to the fixture Settings."""
    return Startup(
        file_path=settings.path.startup,
        generators_dir=settings.path.generators_dir,
        generation_parameters=settings.generation,
    )


def _write(settings: Settings, content: str) -> None:
    settings.path.startup.write_text(content)


def _dump(settings: Settings) -> list[dict]:
    return yaml.safe_load(settings.path.startup.read_text())


def test_list_scenarios_aggregates_and_sorts(
    startup: Startup, settings: Settings
) -> None:
    """Distinct scenario names are returned sorted across entries."""
    _write(settings, _TWO_GENERATORS)

    assert startup.list_scenarios() == ['alpha', 'beta']


def test_list_scenarios_empty_when_no_tags(
    startup: Startup, settings: Settings
) -> None:
    """A file with no scenario tags yields an empty list."""
    _write(settings, _ONE_UNTAGGED)

    assert startup.list_scenarios() == []


def test_get_scenario_generators_in_file_order(
    startup: Startup, settings: Settings
) -> None:
    """Ids of generators in a scenario are returned in file order."""
    _write(settings, _TWO_GENERATORS)

    assert startup.get_scenario_generators('beta') == ['gen-1', 'gen-2']
    assert startup.get_scenario_generators('alpha') == ['gen-1']


def test_get_scenario_generators_empty_for_unknown(
    startup: Startup, settings: Settings
) -> None:
    """An unknown scenario yields no generator ids."""
    _write(settings, _TWO_GENERATORS)

    assert startup.get_scenario_generators('missing') == []


def test_tag_scenario_adds_and_persists(
    startup: Startup, settings: Settings
) -> None:
    """Tagging adds the scenario to the entry and persists it."""
    _write(settings, _ONE_UNTAGGED)

    startup.tag_scenario('gen-1', 'alpha')

    assert _dump(settings)[0]['scenarios'] == ['alpha']


def test_tag_scenario_unknown_generator_raises(
    startup: Startup, settings: Settings
) -> None:
    """Tagging an absent generator raises StartupNotFoundError."""
    _write(settings, _ONE_UNTAGGED)

    with pytest.raises(StartupNotFoundError) as exc:
        startup.tag_scenario('missing', 'alpha')

    assert exc.value.context['value'] == 'missing'


def test_tag_scenario_already_tagged_raises_conflict(
    startup: Startup, settings: Settings
) -> None:
    """Re-tagging raises ScenarioConflictError carrying id and name."""
    _write(settings, _TWO_GENERATORS)

    with pytest.raises(ScenarioConflictError) as exc:
        startup.tag_scenario('gen-1', 'alpha')

    assert exc.value.context['value'] == 'gen-1'
    assert exc.value.context['name'] == 'alpha'


def test_tag_scenario_preserves_other_entries(
    startup: Startup, settings: Settings
) -> None:
    """Tagging one entry leaves the others untouched."""
    _write(settings, _TWO_GENERATORS)

    startup.tag_scenario('gen-1', 'gamma')

    dumped = _dump(settings)
    assert dumped[0]['scenarios'] == ['alpha', 'beta', 'gamma']
    assert dumped[1]['id'] == 'gen-2'
    assert dumped[1]['scenarios'] == ['beta']


def test_untag_scenario_removes_tag(
    startup: Startup, settings: Settings
) -> None:
    """Untagging removes only the named scenario from the entry."""
    _write(settings, _TWO_GENERATORS)

    startup.untag_scenario('gen-1', 'alpha')

    assert _dump(settings)[0]['scenarios'] == ['beta']


def test_untag_scenario_drops_empty_scenarios_key(
    startup: Startup, settings: Settings
) -> None:
    """Removing the last tag drops the scenarios key entirely."""
    _write(
        settings,
        '- id: gen-1\n  path: gen-1/generator.yml\n  scenarios:\n    - solo\n',
    )

    startup.untag_scenario('gen-1', 'solo')

    assert 'scenarios' not in _dump(settings)[0]


def test_untag_scenario_missing_membership_raises(
    startup: Startup, settings: Settings
) -> None:
    """Untagging a generator not in the scenario raises."""
    _write(settings, _TWO_GENERATORS)

    with pytest.raises(ScenarioNotFoundError):
        startup.untag_scenario('gen-2', 'alpha')


def test_untag_scenario_unknown_generator_raises(
    startup: Startup, settings: Settings
) -> None:
    """Untagging an absent generator raises."""
    _write(settings, _TWO_GENERATORS)

    with pytest.raises(ScenarioNotFoundError):
        startup.untag_scenario('missing', 'alpha')


def test_delete_scenario_removes_from_all_and_returns_ids(
    startup: Startup, settings: Settings
) -> None:
    """Deleting a scenario untags every member and returns their ids."""
    _write(settings, _TWO_GENERATORS)

    affected = startup.delete_scenario('beta')

    assert affected == ['gen-1', 'gen-2']
    dumped = _dump(settings)
    assert dumped[0]['scenarios'] == ['alpha']
    assert 'scenarios' not in dumped[1]


def test_delete_scenario_unknown_raises_and_keeps_file(
    startup: Startup, settings: Settings
) -> None:
    """Deleting an absent scenario raises and leaves the file intact."""
    _write(settings, _TWO_GENERATORS)

    with pytest.raises(ScenarioNotFoundError) as exc:
        startup.delete_scenario('missing')

    assert exc.value.context['name'] == 'missing'
    assert _dump(settings) == yaml.safe_load(_TWO_GENERATORS)


def test_rename_scenario_rewrites_tag_and_returns_ids(
    startup: Startup, settings: Settings
) -> None:
    """Renaming rewrites the tag in every member and returns their ids."""
    _write(settings, _TWO_GENERATORS)

    affected = startup.rename_scenario('beta', 'delta')

    assert affected == ['gen-1', 'gen-2']
    dumped = _dump(settings)
    assert dumped[0]['scenarios'] == ['alpha', 'delta']
    assert dumped[1]['scenarios'] == ['delta']


def test_rename_scenario_preserves_tag_position(
    startup: Startup, settings: Settings
) -> None:
    """The renamed tag keeps its position in the entry list."""
    _write(
        settings,
        '- id: gen-1\n'
        '  path: gen-1/generator.yml\n'
        '  scenarios:\n'
        '    - alpha\n'
        '    - beta\n'
        '    - gamma\n',
    )

    startup.rename_scenario('beta', 'delta')

    assert _dump(settings)[0]['scenarios'] == ['alpha', 'delta', 'gamma']


def test_rename_scenario_unknown_raises_and_keeps_file(
    startup: Startup, settings: Settings
) -> None:
    """Renaming an absent scenario raises and leaves the file intact."""
    _write(settings, _TWO_GENERATORS)

    with pytest.raises(ScenarioNotFoundError) as exc:
        startup.rename_scenario('missing', 'delta')

    assert exc.value.context['name'] == 'missing'
    assert _dump(settings) == yaml.safe_load(_TWO_GENERATORS)


def test_rename_scenario_taken_name_raises_and_keeps_file(
    startup: Startup, settings: Settings
) -> None:
    """Renaming onto an existing scenario raises and keeps the file."""
    _write(settings, _TWO_GENERATORS)

    with pytest.raises(ScenarioConflictError) as exc:
        startup.rename_scenario('alpha', 'beta')

    assert exc.value.context['name'] == 'beta'
    assert _dump(settings) == yaml.safe_load(_TWO_GENERATORS)


def test_rename_scenario_to_same_name_raises_conflict(
    startup: Startup, settings: Settings
) -> None:
    """Renaming a scenario to its current name is a conflict."""
    _write(settings, _TWO_GENERATORS)

    with pytest.raises(ScenarioConflictError):
        startup.rename_scenario('alpha', 'alpha')

    assert _dump(settings) == yaml.safe_load(_TWO_GENERATORS)


def test_rename_scenario_preserves_other_entry_fields(
    startup: Startup, settings: Settings
) -> None:
    """Entries keep their other fields when a tag is rewritten."""
    _write(
        settings,
        '- id: gen-1\n'
        '  path: gen-1/generator.yml\n'
        '  autostart: false\n'
        '  scenarios:\n'
        '    - alpha\n',
    )

    startup.rename_scenario('alpha', 'delta')

    entry = _dump(settings)[0]
    assert entry == {
        'id': 'gen-1',
        'path': 'gen-1/generator.yml',
        'autostart': False,
        'scenarios': ['delta'],
    }
