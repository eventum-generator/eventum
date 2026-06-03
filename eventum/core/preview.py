"""Stateless preview and validation of generator configurations.

Loads a generator config from disk and either validates it (load +
initialize every plugin) or produces a bounded sample of events.
Plugins and their template state are discarded each call; this module
never uses the stateful api preview storage.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

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
    plugins = [p for p in initialized.input if not p.is_interactive]

    if not plugins:
        return []

    if len(plugins) == 1:
        source: IdentifiedTimestampsPluginAdapter | InputPluginsMerger = (
            IdentifiedTimestampsPluginAdapter(plugin=plugins[0])
        )
    else:
        source = InputPluginsMerger(plugins=plugins)

    iterator = source.iterate(size=size, skip_past=skip_past)

    try:
        batch = next(iterator)
    except StopIteration:
        return []

    # batch is a structured numpy array with fields 'timestamp'
    # (datetime64[us]) and 'id' (uint16). numpy's .item() is typed as
    # Any, so narrow each element to datetime explicitly.
    timestamps: list[datetime] = []
    for row in batch:
        timestamp: datetime = row['timestamp'].item()
        timestamps.append(timestamp)

    return timestamps
