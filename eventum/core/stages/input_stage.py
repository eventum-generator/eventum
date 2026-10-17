"""Input stage of the pipeline - configures and executes input plugins."""

import queue as queue_mod
from threading import Event, Thread
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

import structlog

from eventum.logging.channels import bind_log_context, capture_log_context
from eventum.plugins.input.adapters import IdentifiedTimestampsPluginAdapter
from eventum.plugins.input.batcher import TimestampsBatcher
from eventum.plugins.input.exceptions import PluginGenerationError
from eventum.plugins.input.merger import InputPluginsMerger
from eventum.plugins.input.scheduler import BatchScheduler
from eventum.utils.throttler import Throttler

if TYPE_CHECKING:
    from collections.abc import Sequence

    from eventum.core.parameters import GeneratorParameters
    from eventum.core.queue import PipelineQueue
    from eventum.plugins.input.base.plugin import InputPlugin
    from eventum.plugins.input.protocols import (
        IdentifiedTimestamps,
        SupportsIdentifiedTimestampsIterate,
        SupportsIdentifiedTimestampsSizedIterate,
    )

logger = structlog.stdlib.get_logger()


class InputStage:
    """Configures and executes input plugins.

    Responsible for building the input pipeline
    (merger -> batcher -> scheduler) and producing timestamp
    batches into a downstream queue.

    Parameters
    ----------
    plugins : Sequence[InputPlugin]
        Input plugins to use.

    params : GeneratorParameters
        Generator parameters.

    """

    def __init__(
        self,
        plugins: Sequence[InputPlugin],
        params: GeneratorParameters,
    ) -> None:
        """Initialize input stage.

        Parameters
        ----------
        plugins : Sequence[InputPlugin]
            Input plugins to use.

        params : GeneratorParameters
            Generator parameters.

        """
        self._plugins = list(plugins)
        self._params = params
        self._timezone = ZoneInfo(self._params.timezone)

        self._input_tags = self._build_input_tags_map()

        self._sources: list[SupportsIdentifiedTimestampsIterate] = []

        self._stop_event: Event | None = None

    def _build_input_tags_map(self) -> dict[int, tuple[str, ...]]:
        """Build map of input plugin ID to tags.

        Returns
        -------
        dict[int, tuple[str, ...]]
            Tags map.

        """
        return {plugin.id: plugin.config.tags for plugin in self._plugins}

    def configure(self, stop_event: Event) -> None:
        """Build the input pipeline.

        All live_mode vs sample_mode branching is centralized here:
        merger -> batcher -> [scheduler].

        Non-interactive plugins are merged into one source ordered by
        time. Every interactive plugin is a source of its own, as it
        publishes timestamps the moment it is interacted with and has
        nothing to be ordered against.

        Parameters
        ----------
        stop_event : Event
            Event for signaling stop request.

        Raises
        ------
        ImproperlyConfiguredError
            If input plugins cannot be configured.

        """
        from eventum.core.executor import ImproperlyConfiguredError

        self._stop_event = stop_event
        self._sources = []

        non_interactive_plugins = [
            p for p in self._plugins if not p.is_interactive
        ]
        interactive_plugins = [p for p in self._plugins if p.is_interactive]

        if len(non_interactive_plugins) > 1:
            logger.debug('Merging input plugins')
            try:
                merged: SupportsIdentifiedTimestampsSizedIterate = (
                    InputPluginsMerger(plugins=non_interactive_plugins)
                )
            except ValueError as e:
                msg = 'Failed to merge input plugins'
                raise ImproperlyConfiguredError(
                    msg,
                    context={'reason': str(e)},
                ) from None

            self._sources.append(self._build_source(merged, lax=False))
        elif len(non_interactive_plugins) == 1:
            logger.debug('Adapting single input plugin')
            self._sources.append(
                self._build_source(
                    IdentifiedTimestampsPluginAdapter(
                        plugin=non_interactive_plugins[0],
                    ),
                    lax=False,
                ),
            )

        for plugin in interactive_plugins:
            logger.debug('Adapting interactive input plugin')
            self._sources.append(
                self._build_source(
                    IdentifiedTimestampsPluginAdapter(plugin=plugin),
                    lax=True,
                ),
            )

    def _build_source(
        self,
        source: SupportsIdentifiedTimestampsSizedIterate,
        *,
        lax: bool,
    ) -> SupportsIdentifiedTimestampsIterate:
        """Wrap a source of timestamps into batcher and, in live mode,
        scheduler.

        Parameters
        ----------
        source : SupportsIdentifiedTimestampsSizedIterate
            Source of timestamps.

        lax : bool
            Whether the batches of the source are only chunked rather
            than accumulated, as for interactive plugins.

        Returns
        -------
        SupportsIdentifiedTimestampsIterate
            Source of timestamp batches.

        Raises
        ------
        ImproperlyConfiguredError
            If the batcher cannot be initialized.

        """
        from eventum.core.executor import ImproperlyConfiguredError

        logger.debug('Wrapping to timestamps batcher')

        # delay bounds the delivery lag batching adds, and only
        # live mode delivers on a schedule to lag behind; without
        # size it is the only limit of the batch, so it still holds
        delay_applies = (
            self._params.live_mode or self._params.batch.size is None
        )

        try:
            batcher = TimestampsBatcher(
                source=source,
                batch_size=self._params.batch.size,
                batch_delay=(
                    self._params.batch.delay if delay_applies else None
                ),
                lax=lax,
            )
        except ValueError as e:
            msg = 'Failed to initialize batcher'
            raise ImproperlyConfiguredError(
                msg,
                context={'reason': str(e)},
            ) from None

        if not self._params.live_mode:
            return batcher

        logger.debug('Wrapping to batch scheduler')

        # interactive plugins publish timestamps as they come,
        # so their due batches are never merged
        return BatchScheduler(
            source=batcher,
            timezone=self._timezone,
            stop_event=self._stop_event,
            max_batch_size=None if lax else self._params.batch.size,
        )

    def execute(
        self,
        output: PipelineQueue[IdentifiedTimestamps],
        *,
        skip_past: bool,
    ) -> None:
        """Produce timestamp batches into the output queue.

        Parameters
        ----------
        output : PipelineQueue[IdentifiedTimestamps]
            Queue for produced timestamp batches.

        skip_past : bool
            Whether to skip past timestamps.

        """
        if not self._sources:
            logger.debug('No input sources configured')
            output.close()
            return

        throttler = Throttler(limit=1, period=10)

        logger.debug('Starting to produce to timestamps queue')
        try:
            if len(self._sources) == 1:
                self._run_source(
                    source=self._sources[0],
                    output=output,
                    skip_past=skip_past,
                    throttler=throttler,
                )
            else:
                self._run_sources_concurrently(
                    sources=self._sources,
                    output=output,
                    skip_past=skip_past,
                    throttler=throttler,
                )

            logger.debug('Finishing input plugins execution')
        finally:
            output.close()

    def _run_source(
        self,
        source: SupportsIdentifiedTimestampsIterate,
        output: PipelineQueue[IdentifiedTimestamps],
        *,
        skip_past: bool,
        throttler: Throttler,
    ) -> None:
        """Iterate a source to its end, logging how it ended.

        A source that fails ends alone - the others keep producing.

        Parameters
        ----------
        source : SupportsIdentifiedTimestampsIterate
            Source to iterate.

        output : PipelineQueue[IdentifiedTimestamps]
            Queue for produced timestamp batches.

        skip_past : bool
            Whether to skip past timestamps.

        throttler : Throttler
            Throttler for queue-full warnings.

        """
        try:
            self._iterate_source(
                source=source,
                output=output,
                skip_past=skip_past,
                throttler=throttler,
            )
        except PluginGenerationError as e:
            logger.error(str(e), **e.context)
        except queue_mod.ShutDown:
            logger.debug(
                'Input stage interrupted by queue shutdown',
            )
        except Exception as e:
            logger.exception(
                'Unexpected error during input plugins execution',
                reason=str(e),
            )

    def _iterate_source(
        self,
        source: SupportsIdentifiedTimestampsIterate,
        output: PipelineQueue[IdentifiedTimestamps],
        *,
        skip_past: bool,
        throttler: Throttler,
    ) -> None:
        """Iterate a single source and put batches to the output queue.

        Parameters
        ----------
        source : SupportsIdentifiedTimestampsIterate
            Source to iterate.

        output : PipelineQueue[IdentifiedTimestamps]
            Queue for produced timestamp batches.

        skip_past : bool
            Whether to skip past timestamps.

        throttler : Throttler
            Throttler for queue-full warnings.

        """
        for timestamps in source.iterate(skip_past=skip_past):
            if self._stop_event is not None and self._stop_event.is_set():
                break

            if output.is_full and self._params.live_mode:
                throttler(
                    logger.warning,
                    (
                        'Timestamps queue is full, events are '
                        'produced later than their timestamps'
                    ),
                    hint=(
                        'Event and output stages are not keeping up '
                        'with the generation rate, consider decreasing '
                        'the rate or increasing the queue size'
                    ),
                )

            output.put(timestamps)

    def _run_sources_concurrently(
        self,
        sources: list[SupportsIdentifiedTimestampsIterate],
        output: PipelineQueue[IdentifiedTimestamps],
        *,
        skip_past: bool,
        throttler: Throttler,
    ) -> None:
        """Run multiple sources in sub-threads, merging into one
        output queue.

        Parameters
        ----------
        sources : list[SupportsIdentifiedTimestampsIterate]
            Sources to iterate.

        output : PipelineQueue[IdentifiedTimestamps]
            Queue for produced timestamp batches.

        skip_past : bool
            Whether to skip past timestamps.

        throttler : Throttler
            Throttler for queue-full warnings.

        """
        threads: list[Thread] = []

        # A new thread does not inherit the context of this one, so the
        # records of every source are carried to the generator log.
        log_context = capture_log_context()

        def run_source(source: SupportsIdentifiedTimestampsIterate) -> None:
            bind_log_context(log_context)
            self._run_source(
                source=source,
                output=output,
                skip_past=skip_past,
                throttler=throttler,
            )

        for i, source in enumerate(sources):
            t = Thread(
                target=run_source,
                args=(source,),
                name=f'input-source-{i}:{self._params.id}',
            )
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

    def stop(self) -> None:
        """Stop producing timestamps. Idempotent and safe to call from
        any thread.

        The stop event wakes scheduled inputs, while interactive plugins
        are stopped directly, since one waiting for interaction never
        observes the event.
        """
        if self._stop_event is not None:
            self._stop_event.set()

        for plugin in self._plugins:
            if plugin.is_interactive:
                plugin.stop_interacting()

    @property
    def input_tags(self) -> dict[int, tuple[str, ...]]:
        """Map of input plugin ID to tags."""
        return self._input_tags

    @property
    def plugins(self) -> list[InputPlugin]:
        """Input plugins."""
        return self._plugins
