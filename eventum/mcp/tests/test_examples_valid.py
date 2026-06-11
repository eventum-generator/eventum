"""Tests that the bundled worked-example generators are valid."""

import shutil
from importlib.resources import files
from pathlib import Path

import pytest

from eventum.core import preview
from eventum.mcp.resources.examples import BUNDLED

_SAMPLE_COUNT = 3
_EXAMPLE_NAMES = [entry['name'] for entry in BUNDLED]

# Examples whose input covers a fixed past date range; previewed with
# skip_past=False so the past timestamps are not skipped (otherwise the
# preview would be empty).
_STATIC_RANGE_EXAMPLES = {'latency-metrics', 'audit-backfill'}


def _copy_example(tmp_path: Path, name: str) -> Path:
    src = files('eventum.mcp').joinpath('examples', name)
    dst = tmp_path / name
    shutil.copytree(str(src), dst)
    return dst / 'generator.yml'


@pytest.mark.parametrize('name', _EXAMPLE_NAMES)
def test_bundled_example_validates(tmp_path: Path, name: str) -> None:
    """validate_generator raises nothing for each bundled example."""
    cfg = _copy_example(tmp_path, name)
    preview.validate_generator(cfg, {})


@pytest.mark.parametrize('name', _EXAMPLE_NAMES)
def test_bundled_example_previews_events(tmp_path: Path, name: str) -> None:
    """produce_sample_events returns the full sample with no errors.

    Asserts an exact count, not ``<=``: every bundled example is a
    single-template chance:1 generator that emits one event per tick
    and supplies at least ``_SAMPLE_COUNT`` ticks. A future example with
    chance < 1, multiple templates, or a dropping template would
    produce fewer events; relax to ``<=`` if one is added.
    """
    cfg = _copy_example(tmp_path, name)
    skip_past = name not in _STATIC_RANGE_EXAMPLES
    result = preview.produce_sample_events(
        cfg, _SAMPLE_COUNT, {}, skip_past=skip_past
    )
    assert len(result.events) == _SAMPLE_COUNT
    assert result.errors == []
