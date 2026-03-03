"""Input plugin timestamp generation benchmarks.

Measures how fast each input plugin can generate timestamps.
Each test generates 5 million events with parametrized batch sizes.
The first batch from each generator is skipped as warmup.

Tests are pure CPU/memory operations — no Docker backends required.

All tests are marked ``@pytest.mark.performance``.
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
import yaml

from eventum.plugins.input.base.plugin import InputPluginParams
from eventum.plugins.input.plugins.cron.config import CronInputPluginConfig
from eventum.plugins.input.plugins.cron.plugin import CronInputPlugin
from eventum.plugins.input.plugins.linspace.config import (
    LinspaceInputPluginConfig,
)
from eventum.plugins.input.plugins.linspace.plugin import LinspaceInputPlugin
from eventum.plugins.input.plugins.static.config import StaticInputPluginConfig
from eventum.plugins.input.plugins.static.plugin import StaticInputPlugin
from eventum.plugins.input.plugins.time_patterns.config import (
    TimePatternsInputPluginConfig,
)
from eventum.plugins.input.plugins.time_patterns.plugin import (
    TimePatternsInputPlugin,
)
from eventum.plugins.input.plugins.timer.config import TimerInputPluginConfig
from eventum.plugins.input.plugins.timer.plugin import TimerInputPlugin
from eventum.plugins.input.plugins.timestamps.config import (
    TimestampsInputPluginConfig,
)
from eventum.plugins.input.plugins.timestamps.plugin import (
    TimestampsInputPlugin,
)
from tests.performance._helpers import PerfResult, print_report

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EVENT_COUNT = 5_000_000
BATCH_SIZES = [100, 1_000, 10_000]
BATCH_IDS = ['batch=100', 'batch=1K', 'batch=10K']
INPUT_PARAMS: InputPluginParams = {'id': 1, 'timezone': ZoneInfo('UTC')}

# Time pattern YAML for the time_patterns plugin benchmark.
_TIME_PATTERN_YAML = {
    'label': 'Benchmark pattern',
    'oscillator': {
        'start': 'now',
        'end': 'never',
        'period': 1,
        'unit': 'hours',
    },
    'multiplier': {
        'ratio': 10000,
    },
    'randomizer': {
        'deviation': 0.0,
        'direction': 'mixed',
    },
    'spreader': {
        'distribution': 'uniform',
        'parameters': {
            'low': 0.0,
            'high': 1.0,
        },
    },
}


# ---------------------------------------------------------------------------
# Static
# ---------------------------------------------------------------------------


@pytest.mark.performance
@pytest.mark.parametrize('batch_size', BATCH_SIZES, ids=BATCH_IDS)
def test_static(
    perf_result: PerfResult,
    batch_size: int,
) -> None:
    """Measure static plugin: bulk timestamp generation."""
    config = StaticInputPluginConfig(count=EVENT_COUNT + batch_size)
    plugin = StaticInputPlugin(config=config, params=INPUT_PARAMS)
    gen = plugin.generate(size=batch_size, skip_past=False)

    next(gen)  # warmup — skip first batch

    total = 0
    start = time.monotonic()
    for batch in gen:
        total += batch.size
    duration = time.monotonic() - start

    perf_result.duration_seconds = duration
    perf_result.total_events = total
    perf_result.metadata = {'plugin': 'static', 'batch_size': batch_size}
    print_report(
        'Static input',
        perf_result,
        params={'count': EVENT_COUNT, 'batch_size': batch_size},
    )
    assert total > 0


# ---------------------------------------------------------------------------
# Cron
# ---------------------------------------------------------------------------


@pytest.mark.performance
@pytest.mark.parametrize('batch_size', BATCH_SIZES, ids=BATCH_IDS)
def test_cron(
    perf_result: PerfResult,
    batch_size: int,
) -> None:
    """Measure cron plugin: croniter expression evaluation."""
    now = datetime.now(tz=ZoneInfo('UTC'))
    config = CronInputPluginConfig(
        expression='* * * * * *',
        count=1000,
        start=now,
        end=now + timedelta(days=365 * 6),
    )
    plugin = CronInputPlugin(config=config, params=INPUT_PARAMS)
    gen = plugin.generate(size=batch_size, skip_past=False)

    next(gen)  # warmup

    total = 0
    start = time.monotonic()
    for batch in gen:
        total += batch.size
        if total >= EVENT_COUNT:
            break
    duration = time.monotonic() - start

    perf_result.duration_seconds = duration
    perf_result.total_events = total
    perf_result.metadata = {'plugin': 'cron', 'batch_size': batch_size}
    print_report(
        'Cron input',
        perf_result,
        params={
            'expression': '* * * * * *',
            'count': 1000,
            'batch_size': batch_size,
        },
    )
    assert total > 0


# ---------------------------------------------------------------------------
# Linspace
# ---------------------------------------------------------------------------


@pytest.mark.performance
@pytest.mark.parametrize('batch_size', BATCH_SIZES, ids=BATCH_IDS)
def test_linspace(
    perf_result: PerfResult,
    batch_size: int,
) -> None:
    """Measure linspace plugin: numpy linspace generation."""
    now = datetime.now(tz=ZoneInfo('UTC'))
    config = LinspaceInputPluginConfig(
        start=now,
        end=now + timedelta(hours=1),
        count=EVENT_COUNT + batch_size,
        endpoint=True,
    )
    plugin = LinspaceInputPlugin(config=config, params=INPUT_PARAMS)
    gen = plugin.generate(size=batch_size, skip_past=False)

    next(gen)  # warmup

    total = 0
    start = time.monotonic()
    for batch in gen:
        total += batch.size
    duration = time.monotonic() - start

    perf_result.duration_seconds = duration
    perf_result.total_events = total
    perf_result.metadata = {'plugin': 'linspace', 'batch_size': batch_size}
    print_report(
        'Linspace input',
        perf_result,
        params={'count': EVENT_COUNT, 'batch_size': batch_size},
    )
    assert total > 0


# ---------------------------------------------------------------------------
# Timer
# ---------------------------------------------------------------------------


@pytest.mark.performance
@pytest.mark.parametrize('batch_size', BATCH_SIZES, ids=BATCH_IDS)
def test_timer(
    perf_result: PerfResult,
    batch_size: int,
) -> None:
    """Measure timer plugin: repeated interval generation."""
    config = TimerInputPluginConfig(
        seconds=0.1,
        count=100,
        repeat=10_000_000,
    )
    plugin = TimerInputPlugin(config=config, params=INPUT_PARAMS)
    gen = plugin.generate(size=batch_size, skip_past=False)

    next(gen)  # warmup

    total = 0
    start = time.monotonic()
    for batch in gen:
        total += batch.size
        if total >= EVENT_COUNT:
            break
    duration = time.monotonic() - start

    perf_result.duration_seconds = duration
    perf_result.total_events = total
    perf_result.metadata = {'plugin': 'timer', 'batch_size': batch_size}
    print_report(
        'Timer input',
        perf_result,
        params={
            'seconds': 0.1,
            'count': 100,
            'repeat': 10_000_000,
            'batch_size': batch_size,
        },
    )
    assert total > 0


# ---------------------------------------------------------------------------
# Timestamps
# ---------------------------------------------------------------------------


@pytest.mark.performance
@pytest.mark.parametrize('batch_size', BATCH_SIZES, ids=BATCH_IDS)
def test_timestamps(
    perf_result: PerfResult,
    batch_size: int,
) -> None:
    """Measure timestamps plugin: pre-defined timestamp list iteration."""
    base = datetime(2024, 1, 1, tzinfo=ZoneInfo('UTC'))
    source = [
        base + timedelta(seconds=i) for i in range(EVENT_COUNT + batch_size)
    ]

    config = TimestampsInputPluginConfig(source=source)
    plugin = TimestampsInputPlugin(config=config, params=INPUT_PARAMS)
    gen = plugin.generate(size=batch_size, skip_past=False)

    next(gen)  # warmup

    total = 0
    start = time.monotonic()
    for batch in gen:
        total += batch.size
    duration = time.monotonic() - start

    perf_result.duration_seconds = duration
    perf_result.total_events = total
    perf_result.metadata = {'plugin': 'timestamps', 'batch_size': batch_size}
    print_report(
        'Timestamps input',
        perf_result,
        params={'count': EVENT_COUNT, 'batch_size': batch_size},
    )
    assert total > 0


# ---------------------------------------------------------------------------
# Time patterns
# ---------------------------------------------------------------------------


@pytest.mark.performance
@pytest.mark.parametrize('batch_size', BATCH_SIZES, ids=BATCH_IDS)
def test_time_patterns(
    perf_result: PerfResult,
    batch_size: int,
    tmp_path: Path,
) -> None:
    """Measure time_patterns plugin: oscillator-based generation."""
    pattern_file = tmp_path / 'pattern.yml'
    pattern_file.write_text(yaml.dump(_TIME_PATTERN_YAML))

    config = TimePatternsInputPluginConfig(patterns=[pattern_file])
    plugin = TimePatternsInputPlugin(config=config, params=INPUT_PARAMS)
    gen = plugin.generate(size=batch_size, skip_past=False)

    next(gen)  # warmup

    total = 0
    start = time.monotonic()
    for batch in gen:
        total += batch.size
        if total >= EVENT_COUNT:
            break
    duration = time.monotonic() - start

    perf_result.duration_seconds = duration
    perf_result.total_events = total
    perf_result.metadata = {
        'plugin': 'time_patterns',
        'batch_size': batch_size,
    }
    print_report(
        'Time patterns input',
        perf_result,
        params={'period': '1h', 'ratio': 10000, 'batch_size': batch_size},
    )
    assert total > 0
