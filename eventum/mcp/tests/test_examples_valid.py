"""Tests that the bundled worked-example generators are valid."""

import shutil
from importlib.resources import files
from pathlib import Path

from eventum.core import preview

_SAMPLE_COUNT = 3


def _copy_example(tmp_path: Path) -> Path:
    src = files('eventum.mcp').joinpath('examples', 'web-access-log')
    dst = tmp_path / 'web-access-log'
    shutil.copytree(str(src), dst)
    return dst / 'generator.yml'


def test_bundled_example_validates(tmp_path: Path) -> None:
    """validate_generator raises nothing for the bundled example."""
    cfg = _copy_example(tmp_path)
    preview.validate_generator(cfg, {})


def test_bundled_example_previews_events(tmp_path: Path) -> None:
    """produce_sample_events returns the requested events with no errors."""
    cfg = _copy_example(tmp_path)
    result = preview.produce_sample_events(cfg, _SAMPLE_COUNT, {})
    assert len(result.events) == _SAMPLE_COUNT
    assert result.errors == []
