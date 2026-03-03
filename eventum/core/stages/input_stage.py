"""Input stage of the pipeline — configures and executes input plugins."""

from threading import Event, Thread
from typing import TYPE_CHECKING, TypedDict
from zoneinfo import ZoneInfo

import structlog

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

        self._configured_non_interactive: (
            SupportsIdentifiedTimestampsIterate | None
        )
        self._configured_interactive: (
            SupportsIdentifiedTimestampsIterate | None
        )

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

        class _PluginItem(TypedDict):
            plugins: list[InputPlugin]
            lax_batcher_mode: bool

        non_interactive_plugins = [
            p for p in self._plugins if not p.is_interactive
        ]
        interactive_plugins = [p for p in self._plugins if p.is_interactive]

        result: list[SupportsIdentifiedTimestampsIterate | None] = []

        items: list[_PluginItem] = [
            {
                'plugins': non_interactive_plugins,
                'lax_batcher_mode': False,
            },
            {
                'plugins': interactive_plugins,
                'lax_batcher_mode': True,
            },
        ]

        for item in items:
            plugins = item['plugins']

            if len(plugins) > 1:
                logger.debug('Merging input plugins')
                try:
                    merged: SupportsIdentifiedTimestampsSizedIterate = (
                        InputPluginsMerger(plugins=plugins)
                    )
                except ValueError as e:
                    msg = 'Failed to merge input plugins'
                    raise ImproperlyConfiguredError(
                        msg,
                        context={'reason': str(e)},
                    ) from None
            elif len(plugins) == 1:
                logger.debug('Adapting single input plugin')
                merged = IdentifiedTimestampsPluginAdapter(
                    plugin=plugins[0],
                )
            else:
                result.append(None)
                continue

            logger.debug('Wrapping to timestamps batcher')
            try:
                batcher = TimestampsBatcher(
                    source=merged,
                    batch_size=self._params.batch.size,
                    batch_delay=self._params.batch.delay,
                    lax=item['lax_batcher_mode'],
                )
            except ValueError as e:
                msg = 'Failed to initialize batcher'
                raise ImproperlyConfiguredError(
                    msg,
                    context={'reason': str(e)},
                ) from None

            if self._params.live_mode:
                logger.debug('Wrapping to batch scheduler')
                result.append(
                    BatchScheduler(
                        source=batcher,
                        timezone=self._timezone,
                        stop_event=stop_event,
                    ),
                )
            else:
                result.append(batcher)

        self._configured_non_interactive = result[0]
        self._configured_interactive = result[1]

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
        sources: list[SupportsIdentifiedTimestampsIterate] = [
            s
            for s in (
                self._configured_non_interactive,
                self._configured_interactive,
            )
            if s is not None
        ]

        if not sources:
            logger.debug('No input sources configured')
            output.close()
            return

        throttler = Throttler(limit=1, period=10)

        logger.debug('Starting to produce to timestamps queue')
        try:
            if len(sources) == 1:
                self._iterate_source(
                    source=sources[0],
                    output=output,
                    skip_past=skip_past,
                    throttler=throttler,
                )
            else:
                self._iterate_merged_sources(
                    sources=sources,
                    output=output,
                    skip_past=skip_past,
                    throttler=throttler,
                )

            logger.debug('Finishing input plugins execution')
        except PluginGenerationError as e:
            logger.error(str(e), **e.context)
        except Exception as e:
            logger.exception(
                'Unexpected error during input plugins execution',
                reason=str(e),
            )
        finally:
            output.close()

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
                        'Timestamps queue is full, consider '
                        'decreasing EPS or changing batching '
                        'settings to avoid time lag with actual '
                        'event timestamps'
                    ),
                )

            output.put(timestamps)

    def _iterate_merged_sources(
        self,
        sources: list[SupportsIdentifiedTimestampsIterate],
        output: PipelineQueue[IdentifiedTimestamps],
        *,
        skip_past: bool,
        throttler: Throttler,
    ) -> None:
        """Iterate multiple sources in sub-threads, merging into one
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

        for i, source in enumerate(sources):
            t = Thread(
                target=self._iterate_source,
                args=(source, output),
                kwargs={
                    'skip_past': skip_past,
                    'throttler': throttler,
                },
                name=f'input-source-{i}:{self._params.id}',
            )
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

    def stop_interactive_plugins(self) -> None:
        """Stop all interactive input plugins."""
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
