"""Stateless preview and validation of generator configurations.

Loads a generator config from disk and either validates it (load +
initialize every plugin), produces a bounded sample of events, or
aggregates a bounded sample of input timestamps into a histogram.
Plugins and their template state are discarded each call; this module
never uses the stateful api preview storage.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import numpy as np

from eventum.core.config_loader import load
from eventum.core.parameters import GeneratorParameters
from eventum.core.plugins_initializer import InitializedPlugins, init_plugins
from eventum.plugins.event.base.plugin import EventPlugin, ProduceParams
from eventum.plugins.event.exceptions import (
    PluginEventsExhaustedError,
    PluginProduceError,
)
from eventum.plugins.input.adapters import IdentifiedTimestampsPluginAdapter
from eventum.plugins.input.merger import InputPluginsMerger
from eventum.plugins.input.protocols import IdentifiedTimestamps

if TYPE_CHECKING:
    from numpy.typing import NDArray

_AUTO_SPANS_US = np.array(
    [
        1,  # 1s
        5,  # 5s
        10,  # 10s
        15,  # 15s
        30,  # 30s
        60,  # 1m
        300,  # 5m
        600,  # 10m
        900,  # 15m
        1800,  # 30m
        3600,  # 1h
        7200,  # 2h
        14400,  # 4h
        21600,  # 6h
        43200,  # 12h
        86400,  # 1d
        604800,  # 7d
        2592000,  # 30d
    ],
    dtype='timedelta64[s]',
).astype('timedelta64[us]')

_OPTIMAL_SPANS_COUNT = 30

_MAX_FULLY_RETURNED_TIMESTAMPS_SAMPLE_SIZE = 100


@dataclass(frozen=True)
class ProduceError:
    """A produce error for a single requested timestamp.

    Attributes
    ----------
    index : int
        Zero-based index of the timestamp in the produce params list.

    message : str
        Error message.

    context : dict[str, Any]
        Structured error context from the plugin.

    """

    index: int
    message: str
    context: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SampleEvents:
    """Result of a bounded produce run.

    Attributes
    ----------
    events : list[str]
        Successfully produced event strings.

    errors : list[ProduceError]
        Per-index produce errors (exhaustion excluded).

    exhausted : bool
        Whether the event plugin signalled exhaustion before all
        timestamps were consumed.

    """

    events: list[str]
    errors: list[ProduceError]
    exhausted: bool


@dataclass(frozen=True)
class TimestampsAggregate:
    """Transport-neutral result of timestamp histogram aggregation.

    Attributes
    ----------
    span_edges : list[datetime]
        Timestamps representing the left edge of each histogram bucket.

    span_counts : dict[int, list[int]]
        Count of timestamps per bucket for each plugin id.

    total : int
        Total count of timestamps in the sample.

    first : list[datetime] | None
        First 50 timestamps when sample exceeds the full-return limit.

    last : list[datetime] | None
        Last 50 timestamps when sample exceeds the full-return limit.

    timestamps : list[datetime] | None
        All timestamps when sample fits within the full-return limit.

    """

    span_edges: list[datetime]
    span_counts: dict[int, list[int]]
    total: int
    first: list[datetime] | None
    last: list[datetime] | None
    timestamps: list[datetime] | None


def _load_initialized(
    path: Path,
    params: dict[str, Any],
) -> InitializedPlugins:
    """Load and initialize all plugins for a generator config.

    Parameters
    ----------
    path : Path
        Absolute path to the generator configuration file.

    params : dict[str, Any]
        Parameter substitutions for the config template.

    Returns
    -------
    InitializedPlugins
        Initialized input, event, and output plugins.

    Raises
    ------
    ConfigurationLoadError
        If the config cannot be loaded, parsed, or name-validated.

    InitializationError
        If any plugin's nested config is invalid.

    """
    config = load(path, params)
    gen_params = GeneratorParameters(id='preview', path=path)
    return init_plugins(
        input=config.input,
        event=config.event,
        output=config.output,
        params=gen_params,
    )


def validate_generator(path: Path, params: dict[str, Any]) -> None:
    """Validate a generator by loading and initializing every plugin.

    Parameters
    ----------
    path : Path
        Absolute path to the generator configuration file.

    params : dict[str, Any]
        Parameter substitutions for the config template.

    Raises
    ------
    ConfigurationLoadError
        If the config cannot be loaded, parsed, or name-validated.

    InitializationError
        If any plugin's nested config is invalid.

    """
    _load_initialized(path, params)


def produce_events_with_plugin(
    plugin: EventPlugin,
    params_list: Sequence[ProduceParams],
) -> SampleEvents:
    """Run an event plugin over a sequence of produce params.

    Collects produced events, per-index errors, and whether the plugin
    signalled exhaustion before all params were consumed.

    Parameters
    ----------
    plugin : EventPlugin
        Initialized event plugin to produce from.

    params_list : Sequence[ProduceParams]
        Ordered sequence of timestamp/tags pairs to produce.

    Returns
    -------
    SampleEvents
        Collected events, errors, and exhaustion flag.

    """
    events: list[str] = []
    errors: list[ProduceError] = []
    exhausted = False

    for i, params in enumerate(params_list):
        try:
            events.extend(plugin.produce(params=params))
        except PluginProduceError as e:
            errors.append(
                ProduceError(
                    index=i,
                    message=str(e),
                    context=e.context,
                ),
            )
        except PluginEventsExhaustedError:
            exhausted = True
            break

    return SampleEvents(events=events, errors=errors, exhausted=exhausted)


def aggregate(
    timestamps: IdentifiedTimestamps,
    span: timedelta | None,
) -> TimestampsAggregate:
    """Compute a histogram over identified timestamps.

    The single authoritative implementation of the bucketing logic.

    Parameters
    ----------
    timestamps : IdentifiedTimestamps
        Record array with fields 'timestamp' (datetime64[us]) and
        'id' (uint16).

    span : timedelta | None
        Bucket width. None triggers auto-span selection.

    Returns
    -------
    TimestampsAggregate
        Histogram counts and sample timestamps.

    """
    plugin_ids = timestamps['id']
    ts = timestamps['timestamp']

    if ts.size == 0:
        return TimestampsAggregate(
            span_edges=[],
            span_counts={},
            total=0,
            first=None,
            last=None,
            timestamps=[],
        )

    if span is None:
        span_td64 = _calculate_auto_span(
            earliest_ts=ts.min(),
            latest_ts=ts.max(),
            timestamps_count=ts.size,
            optimal_spans_count=_OPTIMAL_SPANS_COUNT,
        )
    else:
        span_td64 = np.timedelta64(span, 'us')

    origin = np.datetime64('1970-01-01', 'us')

    timestamp_spans = (ts - origin) // span_td64
    min_span, max_span = timestamp_spans.min(), timestamp_spans.max()
    all_spans: NDArray = np.arange(min_span, max_span + 1)

    span_edges: NDArray = all_spans * span_td64 + origin

    counts, _, _ = np.histogram2d(
        timestamp_spans - min_span,
        plugin_ids,
        bins=(all_spans.size, plugin_ids.max()),
        range=[[0, all_spans.size], [1, plugin_ids.max() + 1]],
    )
    span_counts = {
        plugin_id: plugin_counts.tolist()
        for plugin_id, plugin_counts in enumerate(counts.T, start=1)
    }

    if ts.size <= _MAX_FULLY_RETURNED_TIMESTAMPS_SAMPLE_SIZE:
        first = None
        last = None
        all_ts = cast('list[datetime]', ts.tolist())
    else:
        first = cast('list[datetime]', ts[:50].tolist())
        last = cast('list[datetime]', ts[-50:].tolist())
        all_ts = None

    return TimestampsAggregate(
        span_edges=cast('list[datetime]', span_edges.tolist()),
        span_counts=span_counts,
        total=ts.size,
        first=first,
        last=last,
        timestamps=all_ts,
    )


def _calculate_auto_span(
    earliest_ts: np.datetime64,
    latest_ts: np.datetime64,
    timestamps_count: int,
    optimal_spans_count: int,
) -> np.timedelta64:
    """Calculate optimal bucket width for a time distribution.

    Parameters
    ----------
    earliest_ts : np.datetime64
        Earliest timestamp in the sample.

    latest_ts : np.datetime64
        Latest timestamp in the sample.

    timestamps_count : int
        Total count of timestamps.

    optimal_spans_count : int
        Target number of buckets.

    Returns
    -------
    np.timedelta64
        Selected span, aligned to the nearest nice value that does not
        exceed the computed optimal span.

    """
    optimal_span = np.timedelta64(
        (latest_ts - earliest_ts) / min(optimal_spans_count, timestamps_count),
        'us',
    )

    indexes = np.where(optimal_span >= _AUTO_SPANS_US)[0]
    index = indexes[-1] if indexes.size > 0 else 0
    return _AUTO_SPANS_US[index]


def _take_raw_batch(
    initialized: InitializedPlugins,
    *,
    size: int,
    skip_past: bool,
) -> IdentifiedTimestamps | None:
    """Return the first batch from non-interactive input plugins.

    Parameters
    ----------
    initialized : InitializedPlugins
        Initialized plugins container.

    size : int
        Maximum number of timestamps to retrieve.

    skip_past : bool
        Whether to skip past timestamps before yielding.

    Returns
    -------
    IdentifiedTimestamps | None
        Raw structured array, or None if no non-interactive plugins
        exist or the iterator is empty.

    """
    plugins = [p for p in initialized.input if not p.is_interactive]

    if not plugins:
        return None

    if len(plugins) == 1:
        source: IdentifiedTimestampsPluginAdapter | InputPluginsMerger = (
            IdentifiedTimestampsPluginAdapter(plugin=plugins[0])
        )
    else:
        source = InputPluginsMerger(plugins=plugins)

    iterator = source.iterate(size=size, skip_past=skip_past)

    try:
        return next(iterator)
    except StopIteration:
        return None


def produce_sample_events(
    path: Path,
    count: int,
    params: dict[str, Any],
    *,
    skip_past: bool = True,
) -> SampleEvents:
    """Load a generator and produce up to `count` sample events.

    Initializes all plugins from the config at `path`, generates up
    to `count` timestamps from the non-interactive input plugins, and
    produces events for them. Plugins are discarded after the call.

    Parameters
    ----------
    path : Path
        Absolute path to the generator configuration file.

    count : int
        Maximum number of timestamps to generate and produce from.

    params : dict[str, Any]
        Parameter substitutions for the config template.

    skip_past : bool, default=True
        Whether to skip timestamps that are in the past before
        generating. Set to False for static date ranges.

    Returns
    -------
    SampleEvents
        Collected events, per-index errors, and exhaustion flag.

    Raises
    ------
    ConfigurationLoadError
        If the config cannot be loaded, parsed, or name-validated.

    InitializationError
        If any plugin's nested config is invalid.

    """
    initialized = _load_initialized(path, params)
    timestamps = _take_timestamps(initialized, size=count, skip_past=skip_past)

    params_list: list[ProduceParams] = [
        {'timestamp': ts, 'tags': ()} for ts in timestamps
    ]

    return produce_events_with_plugin(initialized.event, params_list)


def aggregate_sample_timestamps(
    path: Path,
    size: int,
    params: dict[str, Any],
    *,
    skip_past: bool = True,
    span: timedelta | None = None,
) -> TimestampsAggregate:
    """Load a generator and aggregate up to `size` sample timestamps.

    Parameters
    ----------
    path : Path
        Absolute path to the generator configuration file.

    size : int
        Maximum number of timestamps to generate.

    params : dict[str, Any]
        Parameter substitutions for the config template.

    skip_past : bool, default=True
        Whether to skip timestamps that are in the past before
        generating. Set to False for static date ranges.

    span : timedelta | None, default=None
        Histogram bucket width. None triggers auto-span selection.

    Returns
    -------
    TimestampsAggregate
        Histogram counts and sample timestamps.

    Raises
    ------
    ConfigurationLoadError
        If the config cannot be loaded, parsed, or name-validated.

    InitializationError
        If any plugin's nested config is invalid.

    """
    initialized = _load_initialized(path, params)
    batch = _take_raw_batch(initialized, size=size, skip_past=skip_past)

    if batch is None:
        empty: IdentifiedTimestamps = np.array(
            [], dtype=[('timestamp', 'datetime64[us]'), ('id', 'uint16')]
        )
        return aggregate(empty, span)

    return aggregate(batch, span)


def _take_timestamps(
    initialized: InitializedPlugins,
    *,
    size: int,
    skip_past: bool,
) -> list[datetime]:
    """Extract up to `size` timestamps from non-interactive input plugins.

    Parameters
    ----------
    initialized : InitializedPlugins
        Initialized plugins container.

    size : int
        Maximum number of timestamps to retrieve.

    skip_past : bool
        Whether to skip past timestamps before yielding.

    Returns
    -------
    list[datetime]
        List of naive UTC datetime objects.

    """
    batch = _take_raw_batch(initialized, size=size, skip_past=skip_past)

    if batch is None:
        return []

    # batch is a structured numpy array with fields 'timestamp'
    # (datetime64[us]) and 'id' (uint16). numpy's .item() is typed as
    # Any, so narrow each element to datetime explicitly.
    timestamps: list[datetime] = []
    for row in batch:
        timestamp: datetime = row['timestamp'].item()
        timestamps.append(timestamp)

    return timestamps
