"""Tests for the stateless preview service."""

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import pytest

from eventum.core.config_loader import ConfigurationLoadError
from eventum.core.preview import (
    SampleEvents,
    produce_events_with_plugin,
    validate_generator,
)
from eventum.plugins.event.base.plugin import ProduceParams

if TYPE_CHECKING:
    from eventum.plugins.event.base.plugin import EventPlugin


class _FakePlugin:
    def __init__(
        self,
        behavior: Callable[[Any], list[str]],
    ) -> None:
        self._behavior = behavior

    def produce(self, params: Any) -> list[str]:
        return self._behavior(params)


def test_produce_events_with_plugin_collects_events_and_errors() -> None:  # noqa: D103
    from eventum.plugins.event.exceptions import PluginProduceError

    calls: dict[str, int] = {'n': 0}

    def behavior(_params: Any) -> list[str]:
        calls['n'] += 1
        if calls['n'] == 2:  # noqa: PLR2004
            msg = 'boom'
            raise PluginProduceError(msg, context={'k': 'v'})
        return [f'event-{calls["n"]}']

    plugin = _FakePlugin(behavior)
    params_list: list[ProduceParams] = [
        {'timestamp': datetime(2026, 1, 1, tzinfo=UTC), 'tags': ()}
        for _ in range(3)
    ]

    result = produce_events_with_plugin(
        cast('EventPlugin', plugin), params_list
    )

    assert isinstance(result, SampleEvents)  # noqa: S101
    assert result.events == ['event-1', 'event-3']  # noqa: S101
    assert [e.index for e in result.errors] == [1]  # noqa: S101
    assert result.exhausted is False  # noqa: S101


def test_produce_events_with_plugin_stops_on_exhausted() -> None:  # noqa: D103
    from eventum.plugins.event.exceptions import PluginEventsExhaustedError

    calls: dict[str, int] = {'n': 0}

    def behavior(_params: Any) -> list[str]:
        calls['n'] += 1
        if calls['n'] == 2:  # noqa: PLR2004
            raise PluginEventsExhaustedError
        return ['event']

    plugin = _FakePlugin(behavior)
    params_list: list[ProduceParams] = [
        {'timestamp': datetime(2026, 1, 1, tzinfo=UTC), 'tags': ()}
        for _ in range(3)
    ]

    result = produce_events_with_plugin(
        cast('EventPlugin', plugin), params_list
    )

    assert result.exhausted is True  # noqa: S101
    assert len(result.events) == 1  # noqa: S101
    assert result.errors == []  # noqa: S101


def test_validate_generator_missing_file_raises(tmp_path: Path) -> None:  # noqa: D103
    with pytest.raises(ConfigurationLoadError):
        validate_generator(tmp_path / 'nope' / 'generator.yml', params={})


def test_aggregate_sample_timestamps_returns_counts(tmp_path: Path) -> None:  # noqa: D103
    from eventum.core.preview import (
        TimestampsAggregate,
        aggregate_sample_timestamps,
    )

    gen = tmp_path / 'g'
    gen.mkdir()

    config_text = (
        'input:\n'
        '  - linspace:\n'
        '      start: "2025-01-01 00:00:00"\n'
        '      end: "2025-01-01 01:00:00"\n'
        '      count: 10\n'
        'event:\n'
        '  script:\n'
        '    path: produce.py\n'
        'output:\n'
        '  - stdout:\n'
        '      stream: stderr\n'
    )
    (gen / 'generator.yml').write_text(config_text)
    (gen / 'produce.py').write_text(
        'def produce(params):\n    return [str(params["timestamp"])]\n',
    )

    agg = aggregate_sample_timestamps(
        gen / 'generator.yml',
        size=100,
        params={},
        skip_past=False,
    )
    assert isinstance(agg, TimestampsAggregate)  # noqa: S101
    assert agg.total >= 1  # noqa: S101


def test_produce_sample_events_end_to_end(tmp_path: Path) -> None:  # noqa: D103
    gen = tmp_path / 'g'
    gen.mkdir()

    script_path = gen / 'produce.py'
    script_path.write_text(
        'def produce(params):\n    return [str(params["timestamp"])]\n',
    )

    config_text = (
        'input:\n'
        '  - linspace:\n'
        '      start: "2025-01-01 00:00:00"\n'
        '      end: "2025-01-01 01:00:00"\n'
        '      count: 10\n'
        'event:\n'
        '  script:\n'
        '    path: produce.py\n'
        'output:\n'
        '  - stdout:\n'
        '      stream: stderr\n'
    )
    (gen / 'generator.yml').write_text(config_text)

    from eventum.core.preview import produce_sample_events

    result = produce_sample_events(
        gen / 'generator.yml',
        count=5,
        params={},
        skip_past=False,
    )

    assert result.events  # noqa: S101
    assert all(isinstance(e, str) for e in result.events)  # noqa: S101
    assert result.exhausted is False  # noqa: S101


def test_calculate_auto_span_small_range() -> None:  # noqa: D103
    import numpy as np

    from eventum.core.preview import _calculate_auto_span

    earliest = np.datetime64('2024-01-01T00:00:00', 'us')
    latest = np.datetime64('2024-01-01T00:00:10', 'us')
    span = _calculate_auto_span(earliest, latest, 10, 30)
    assert span <= np.timedelta64(10, 's')  # noqa: S101


def test_calculate_auto_span_24h_range() -> None:  # noqa: D103
    import numpy as np

    from eventum.core.preview import _calculate_auto_span

    earliest = np.datetime64('2024-01-01T00:00:00', 'us')
    latest = np.datetime64('2024-01-02T00:00:00', 'us')
    span = _calculate_auto_span(earliest, latest, 1000, 30)
    assert span >= np.timedelta64(1, 's')  # noqa: S101
    assert span <= np.timedelta64(24, 'h')  # noqa: S101
