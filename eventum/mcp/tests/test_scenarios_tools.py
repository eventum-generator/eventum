"""Tests for the MCP scenario-management tools."""

from pathlib import Path
from unittest.mock import MagicMock

from eventum.app.startup import Startup
from eventum.core.parameters import GenerationParameters
from eventum.mcp.context import ServerLiveContext
from eventum.mcp.errors import ToolFailure
from eventum.mcp.tools.scenarios import (
    add_generator_to_scenario,
    delete_scenario,
    get_scenario,
    list_scenarios,
    remove_generator_from_scenario,
    rename_scenario,
)

_TWO = (
    '- id: gen-1\n  path: gen-1/generator.yml\n  scenarios:\n    - alpha\n'
    '- id: gen-2\n  path: gen-2/generator.yml\n'
)


def _ctx(tmp_path: Path, *, read_only: bool = False) -> ServerLiveContext:
    gens = tmp_path / 'generators'
    gens.mkdir(exist_ok=True)
    startup = Startup(
        file_path=tmp_path / 'startup.yml',
        generators_dir=gens,
        generation_parameters=GenerationParameters(),
    )
    return ServerLiveContext(
        generators_dir=gens,
        read_only=read_only,
        manager=MagicMock(),
        startup=startup,
        generation=GenerationParameters(),
        logs_dir=tmp_path,
        log_format='plain',
        settings=MagicMock(),
        hooks=MagicMock(),
    )


async def test_list_scenarios(tmp_path: Path) -> None:
    """Listing returns the scenario names from the startup file."""
    ctx = _ctx(tmp_path)
    (tmp_path / 'startup.yml').write_text(_TWO)

    assert await list_scenarios(ctx) == ['alpha']


async def test_get_scenario_returns_ids(tmp_path: Path) -> None:
    """Getting a scenario returns its generator ids."""
    ctx = _ctx(tmp_path)
    (tmp_path / 'startup.yml').write_text(_TWO)

    assert await get_scenario(ctx, 'alpha') == {
        'name': 'alpha',
        'generator_ids': ['gen-1'],
    }


async def test_get_scenario_unknown_is_failure(tmp_path: Path) -> None:
    """An unknown scenario returns a structured failure."""
    ctx = _ctx(tmp_path)
    (tmp_path / 'startup.yml').write_text(_TWO)

    result = await get_scenario(ctx, 'missing')

    assert isinstance(result, ToolFailure)
    assert result.details == {'name': 'missing'}


async def test_add_generator_to_scenario(tmp_path: Path) -> None:
    """Adding a generator tags it and persists the change."""
    ctx = _ctx(tmp_path)
    (tmp_path / 'startup.yml').write_text(_TWO)

    result = await add_generator_to_scenario(ctx, 'gen-2', 'alpha')

    assert result == {
        'generator_id': 'gen-2',
        'scenario': 'alpha',
        'added': True,
    }
    assert await get_scenario(ctx, 'alpha') == {
        'name': 'alpha',
        'generator_ids': ['gen-1', 'gen-2'],
    }


async def test_add_generator_read_only_blocked(tmp_path: Path) -> None:
    """A read-only server refuses to add a generator."""
    ctx = _ctx(tmp_path, read_only=True)
    (tmp_path / 'startup.yml').write_text(_TWO)

    result = await add_generator_to_scenario(ctx, 'gen-2', 'alpha')

    assert isinstance(result, ToolFailure)
    assert 'read-only' in result.error


async def test_add_generator_unknown_is_failure(tmp_path: Path) -> None:
    """Adding an absent generator forwards a scrubbed failure."""
    ctx = _ctx(tmp_path)
    (tmp_path / 'startup.yml').write_text(_TWO)

    result = await add_generator_to_scenario(ctx, 'missing', 'alpha')

    assert isinstance(result, ToolFailure)
    assert result.details.get('value') == 'missing'


async def test_add_generator_conflict_is_failure(tmp_path: Path) -> None:
    """Re-adding an already-tagged generator fails."""
    ctx = _ctx(tmp_path)
    (tmp_path / 'startup.yml').write_text(_TWO)

    result = await add_generator_to_scenario(ctx, 'gen-1', 'alpha')

    assert isinstance(result, ToolFailure)


async def test_remove_generator_from_scenario(tmp_path: Path) -> None:
    """Removing a generator untags it."""
    ctx = _ctx(tmp_path)
    (tmp_path / 'startup.yml').write_text(_TWO)

    result = await remove_generator_from_scenario(ctx, 'gen-1', 'alpha')

    assert result == {
        'generator_id': 'gen-1',
        'scenario': 'alpha',
        'removed': True,
    }
    assert await list_scenarios(ctx) == []


async def test_remove_generator_read_only_blocked(tmp_path: Path) -> None:
    """A read-only server refuses to remove a generator."""
    ctx = _ctx(tmp_path, read_only=True)
    (tmp_path / 'startup.yml').write_text(_TWO)

    result = await remove_generator_from_scenario(ctx, 'gen-1', 'alpha')

    assert isinstance(result, ToolFailure)


async def test_delete_scenario(tmp_path: Path) -> None:
    """Deleting a scenario untags every member and reports the ids."""
    ctx = _ctx(tmp_path)
    (tmp_path / 'startup.yml').write_text(_TWO)

    result = await delete_scenario(ctx, 'alpha')

    assert result == {
        'scenario': 'alpha',
        'deleted': True,
        'generator_ids': ['gen-1'],
    }
    assert await list_scenarios(ctx) == []


async def test_delete_scenario_read_only_blocked(tmp_path: Path) -> None:
    """A read-only server refuses to delete a scenario."""
    ctx = _ctx(tmp_path, read_only=True)
    (tmp_path / 'startup.yml').write_text(_TWO)

    result = await delete_scenario(ctx, 'alpha')

    assert isinstance(result, ToolFailure)


async def test_rename_scenario_rewrites_tag(tmp_path: Path) -> None:
    """Renaming rewrites the tag and returns the affected ids."""
    ctx = _ctx(tmp_path)
    (tmp_path / 'startup.yml').write_text(_TWO)

    result = await rename_scenario(ctx, 'alpha', 'delta')

    assert result == {
        'scenario': 'alpha',
        'new_name': 'delta',
        'renamed': True,
        'generator_ids': ['gen-1'],
    }
    assert await list_scenarios(ctx) == ['delta']


async def test_rename_scenario_unknown_is_failure(tmp_path: Path) -> None:
    """An unknown scenario returns a structured failure."""
    ctx = _ctx(tmp_path)
    (tmp_path / 'startup.yml').write_text(_TWO)

    result = await rename_scenario(ctx, 'missing', 'delta')

    assert isinstance(result, ToolFailure)
    assert result.details == {'name': 'missing'}


async def test_rename_scenario_taken_name_is_failure(tmp_path: Path) -> None:
    """Renaming onto an existing scenario is refused."""
    ctx = _ctx(tmp_path)
    (tmp_path / 'startup.yml').write_text(
        '- id: gen-1\n  path: gen-1/generator.yml\n  scenarios:\n'
        '    - alpha\n'
        '- id: gen-2\n  path: gen-2/generator.yml\n  scenarios:\n'
        '    - beta\n'
    )

    result = await rename_scenario(ctx, 'alpha', 'beta')

    assert isinstance(result, ToolFailure)
    assert result.details == {'name': 'beta'}
    assert await list_scenarios(ctx) == ['alpha', 'beta']


async def test_rename_scenario_read_only_is_failure(tmp_path: Path) -> None:
    """A read-only server refuses the rename."""
    ctx = _ctx(tmp_path, read_only=True)
    (tmp_path / 'startup.yml').write_text(_TWO)

    result = await rename_scenario(ctx, 'alpha', 'delta')

    assert isinstance(result, ToolFailure)
    assert await list_scenarios(ctx) == ['alpha']
