"""Event stage of the pipeline — consumes timestamps, produces events."""

import queue as queue_mod
from datetime import datetime
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

import structlog

from eventum.plugins.event.base.plugin import EventPlugin, ProduceParams
from eventum.plugins.event.exceptions import (
    PluginEventsExhaustedError,
    PluginProduceError,
)
from eventum.utils.throttler import Throttler

if TYPE_CHECKING:
    from eventum.core.parameters import GeneratorParameters
    from eventum.core.queue import PipelineQueue
    from eventum.plugins.input.protocols import IdentifiedTimestamps

logger = structlog.stdlib.get_logger()


class EventStage:
    """Consumes timestamp batches and produces event batches.

    This stage runs synchronously in a thread pool because event
    plugins (e.g. Jinja2 template rendering) are CPU-bound.

    Parameters
    ----------
    plugin : EventPlugin
        Event plugin to use.

    input_tags : dict[int, tuple[str, ...]]
        Map of input plugin ID to tags.

    params : GeneratorParameters
        Generator parameters.

    """

    def __init__(
        self,
        plugin: EventPlugin,
        input_tags: dict[int, tuple[str, ...]],
        params: GeneratorParameters,
    ) -> None:
        """Initialize event stage.

        Parameters
        ----------
        plugin : EventPlugin
            Event plugin to use.

        input_tags : dict[int, tuple[str, ...]]
            Map of input plugin ID to tags.

        params : GeneratorParameters
            Generator parameters.

        """
        self._plugin = plugin
        self._input_tags = input_tags
        self._params = params
        self._timezone = ZoneInfo(self._params.timezone)

    def _produce_batch(
        self,
        timestamps: IdentifiedTimestamps,
        input: PipelineQueue[IdentifiedTimestamps],
    ) -> tuple[list[str], bool]:
        """Produce events for a single timestamp batch.

        Returns
        -------
        tuple[list[str], bool]
            Produced events and whether the plugin is exhausted.

        """
        dt_timestamps = timestamps['timestamp'].astype(dtype=datetime)
        params: ProduceParams = ProduceParams(
            tags=...,  # type: ignore[typeddict-item]
            timestamp=...,  # type: ignore[typeddict-item]
        )
        events: list[str] = []

        for id, timestamp in zip(
            timestamps['id'],
            dt_timestamps,
            strict=False,
        ):
            params['tags'] = self._input_tags[id]
            params['timestamp'] = timestamp.replace(
                tzinfo=self._timezone,
            )

            try:
                events.extend(self._plugin.produce(params))
            except PluginProduceError as e:
                logger.error(str(e), **e.context)
            except PluginEventsExhaustedError:
                logger.debug(
                    'Events exhausted, closing upstream queue',
                )
                input.shutdown()
                return events, True
            except Exception as e:
                logger.exception(
                    'Unexpected error during event plugin execution',
                    reason=str(e),
                )

        return events, False

    def execute(
        self,
        input: PipelineQueue[IdentifiedTimestamps],
        output: PipelineQueue[list[str]],
    ) -> None:
        """Consume timestamps and produce event batches.

        Parameters
        ----------
        input : PipelineQueue[IdentifiedTimestamps]
            Queue of timestamp batches to consume.

        output : PipelineQueue[list[str]]
            Queue for produced event batches.

        Notes
        -----
        This method is synchronous and intended to be called from a
        thread pool executor.

        """
        exhausted = False
        throttler = Throttler(limit=1, period=10)

        logger.debug('Starting to consume timestamps queue')

        try:
            while not exhausted:
                timestamps = input.get()

                if timestamps is None:
                    break

                events, exhausted = self._produce_batch(timestamps, input)

                if events:
                    if output.is_full and self._params.live_mode:
                        throttler(
                            logger.warning,
                            (
                                'Events queue is full, consider decreasing '
                                'EPS or changing batching settings to avoid '
                                'time lag with actual event timestamps'
                            ),
                        )

                    output.put(events)
        except queue_mod.ShutDown:
            logger.debug('Event stage interrupted by queue shutdown')
        except Exception as e:
            logger.exception(
                'Fatal error in event stage',
                reason=str(e),
            )
            input.shutdown()
        finally:
            logger.debug('Finishing event plugin execution')
            output.close()
