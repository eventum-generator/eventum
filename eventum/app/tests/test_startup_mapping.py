"""Tests for the startup entry mapper."""

from pathlib import Path

import pytest

from eventum.app.startup import StartupGeneratorParameters
from eventum.app.startup.mapping import (
    RawEntriesValidationError,
    StartupEntryMapper,
)
from eventum.core.parameters import GenerationParameters


def _build_mapper(
    *,
    generators_dir: Path,
    timezone: str = 'UTC',
) -> StartupEntryMapper:
    return StartupEntryMapper(
        generators_dir=generators_dir,
        generation_parameters=GenerationParameters(timezone=timezone),
    )


# --- parse: defaults / merge ---


def test_parse_applies_defaults_to_missing_fields(tmp_path: Path) -> None:
    """Defaults from base parameters are merged into each entry."""
    mapper = _build_mapper(generators_dir=tmp_path, timezone='UTC')

    result = mapper.parse([{'id': 'gen1', 'path': 'config.yml'}])

    assert len(result.root) == 1  # noqa: S101
    assert result.root[0].id == 'gen1'  # noqa: S101
    assert result.root[0].timezone == 'UTC'  # noqa: S101


def test_parse_per_entry_value_overrides_default(tmp_path: Path) -> None:
    """Per-entry value wins over the base default."""
    mapper = _build_mapper(generators_dir=tmp_path, timezone='UTC')

    result = mapper.parse(
        [{'id': 'gen1', 'path': 'config.yml', 'timezone': 'US/Eastern'}],
    )

    assert result.root[0].timezone == 'US/Eastern'  # noqa: S101


def test_parse_empty_input_yields_empty_result(tmp_path: Path) -> None:
    """Empty input list parses to an empty params list."""
    mapper = _build_mapper(generators_dir=tmp_path)

    result = mapper.parse([])

    assert len(result.root) == 0  # noqa: S101


def test_parse_nested_override_replaces_only_leaf(tmp_path: Path) -> None:
    """Nested override touches only the leaf field."""
    mapper = _build_mapper(generators_dir=tmp_path, timezone='UTC')

    result = mapper.parse(
        [
            {
                'id': 'gen1',
                'path': 'config.yml',
                'batch': {'size': 500},
            },
        ],
    )

    assert result.root[0].batch.size == 500  # noqa: S101, PLR2004


def test_parse_independent_merge_for_multiple_entries(
    tmp_path: Path,
) -> None:
    """Each entry is independently merged with the base."""
    mapper = _build_mapper(generators_dir=tmp_path, timezone='UTC')

    result = mapper.parse(
        [
            {'id': 'gen1', 'path': 'config1.yml'},
            {'id': 'gen2', 'path': 'config2.yml', 'live_mode': False},
        ],
    )

    assert len(result.root) == 2  # noqa: S101, PLR2004
    assert result.root[0].id == 'gen1'  # noqa: S101
    assert result.root[0].live_mode is True  # noqa: S101
    assert result.root[1].id == 'gen2'  # noqa: S101
    assert result.root[1].live_mode is False  # noqa: S101


def test_parse_preserves_scenarios_field(tmp_path: Path) -> None:
    """Scenarios survive the merge round-trip."""
    mapper = _build_mapper(generators_dir=tmp_path, timezone='UTC')

    result = mapper.parse(
        [
            {
                'id': 'gen1',
                'path': 'config.yml',
                'scenarios': ['s1', 's2', 's3'],
            },
            {'id': 'gen2', 'path': 'config2.yml'},
        ],
    )

    assert result.root[0].scenarios == ['s1', 's2', 's3']  # noqa: S101
    assert result.root[1].scenarios == []  # noqa: S101


# --- parse: errors ---


def test_parse_missing_id_raises_validation_error(tmp_path: Path) -> None:
    """Missing required `id` raises RawEntriesValidationError."""
    mapper = _build_mapper(generators_dir=tmp_path)

    with pytest.raises(RawEntriesValidationError) as exc:
        mapper.parse([{'path': 'config.yml'}])

    assert 'reason' in exc.value.context  # noqa: S101


# --- parse: path normalization ---


def test_parse_normalizes_relative_path_to_absolute(tmp_path: Path) -> None:
    """Relative entry path is resolved against generators_dir."""
    mapper = _build_mapper(generators_dir=tmp_path)

    result = mapper.parse([{'id': 'gen1', 'path': 'gen1/generator.yml'}])

    assert result.root[0].path == tmp_path / 'gen1/generator.yml'  # noqa: S101
    assert result.root[0].path.is_absolute()  # noqa: S101


def test_parse_keeps_absolute_path_as_is(tmp_path: Path) -> None:
    """Absolute entry path passes through unchanged."""
    mapper = _build_mapper(generators_dir=tmp_path)
    absolute = tmp_path / 'outside' / 'gen.yml'

    result = mapper.parse([{'id': 'gen1', 'path': str(absolute)}])

    assert result.root[0].path == absolute  # noqa: S101


# --- serialize ---


def test_serialize_places_id_first_and_omits_unset(
    tmp_path: Path,
) -> None:
    """Serialize emits id first; unset fields are omitted."""
    mapper = _build_mapper(generators_dir=tmp_path)

    raw = mapper.serialize(
        StartupGeneratorParameters(
            id='gen1',
            path=Path('gen1/generator.yml'),
        ),
    )

    assert next(iter(raw.keys())) == 'id'  # noqa: S101
    assert raw['id'] == 'gen1'  # noqa: S101
    assert 'autostart' not in raw  # noqa: S101


def test_serialize_normalizes_relative_path_to_absolute(
    tmp_path: Path,
) -> None:
    """Relative path on input becomes absolute on output."""
    mapper = _build_mapper(generators_dir=tmp_path)

    raw = mapper.serialize(
        StartupGeneratorParameters(
            id='gen1',
            path=Path('gen1/generator.yml'),
        ),
    )

    assert raw['path'] == str(tmp_path / 'gen1/generator.yml')  # noqa: S101
