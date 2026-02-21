"""Executor of plugins that orchestrates data flow between them."""

import asyncio
from collections.abc import Sequence
from datetime import datetime
from typing import TypedDict, cast
from zoneinfo import ZoneInfo

import janus
import structlog
import uvloop
from aiostream import stream

from eventum.core.parameters import GeneratorParameters
from eventum.exceptions import ContextualError
from eventum.logging.context import propagate_logger_context
from eventum.plugins.event.base.plugin import EventPlugin, ProduceParams
from eventum.plugins.event.exceptions import (
    PluginExhaustedError,
    PluginProduceError,
)
from eventum.plugins.input.adapters import (
    AsyncIdentifiedTimestampsEmptyAdapter,
    AsyncIdentifiedTimestampsSyncAdapter,
    IdentifiedTimestampsPluginAdapter,
)
from eventum.plugins.input.base.plugin import InputPlugin
from eventum.plugins.input.batcher import TimestampsBatcher
from eventum.plugins.input.exceptions import PluginGenerationError
from eventum.plugins.input.merger import InputPluginsMerger
from eventum.plugins.input.protocols import (
    IdentifiedTimestamps,
    SupportsAsyncIdentifiedTimestampsIterate,
    SupportsIdentifiedTimestampsSizedIterate,
)
from eventum.plugins.input.scheduler import BatchScheduler
from eventum.plugins.output.base.plugin import OutputPlugin
from eventum.plugins.output.exceptions import PluginOpenError, PluginWriteError
from eventum.utils.throttler import AsyncThrottler, Throttler

logger = structlog.stdlib.get_logger()


class ImproperlyConfiguredError(ContextualError):
    """Plugins cannot be executed with provided parameters."""


class ExecutionError(ContextualError):
    """Execution error."""


class Executor:
    """Executor of plugins."""

    def __init__(
        self,
        input: Sequence[InputPlugin],
        event: EventPlugin,
        output: Sequence[OutputPlugin],
        params: GeneratorParameters,
    ) -> None:
        """Initialize executor.

        Parameters
        ----------
        input : Sequence[InputPlugin]
            List of input plugins.

        event: EventPlugin
            Event plugin.

        output: Sequence[OutputPlugin]
            List of output plugins.

        params: GeneratorParameters
            Generator parameters.

        Raises
        ------
        ValueError
            If some of the top level parameters are invalid.

        ImproperlyConfiguredError
            If initialization fails with provided plugins and parameters.

        """
        self._input = list(input)
        self._event = event
        self._output = list(output)
        self._params = params
        self._timezone = ZoneInfo(self._params.timezone)

        if not self._input:
            msg = 'At least one input plugin must be provided'
            raise ValueError(msg)

        if not self._output:
            msg = 'At least one output plugin must be provided'
            raise ValueError(msg)

        logger.debug('Initializing queues')
        self._timestamps_queue: janus.Queue[IdentifiedTimestamps | None] = (
            janus.Queue(maxsize=params.queue.max_timestamp_batches)
        )
        self._events_queue: janus.Queue[list[str] | None] = janus.Queue(
            maxsize=params.queue.max_event_batches,
        )

        logger.debug('Collecting input plugin tags')
        self._input_tags = self._build_input_tags_map()

        logger.debug('Configuring input')
        (
            self._configured_non_interactive_input,
            self._configured_interactive_input,
        ) = self._configure_input()

        self._output_tasks: set[asyncio.Task] = set()
        self._output_semaphore = asyncio.Semaphore(
            value=self._params.max_concurrency,
        )

        self._stop_event = asyncio.Event()
        self._end_execution_event = asyncio.Event()

        self._event_loop: None | asyncio.AbstractEventLoop = None

    def _build_input_tags_map(self) -> dict[int, tuple[str, ...]]:
        """Build map of input plugin tags.

        Returns
        -------
        dict[int, tuple[str, ...]]
            Tags map with input plugin id in keys and tags tuple in
            values.

        """
        tags_map: dict[int, tuple[str, ...]] = {}
        for plugin in self._input:
            tags_map[plugin.id] = plugin.config.tags

        return tags_map

    def _configure_input(
        self,
    ) -> tuple[
        SupportsAsyncIdentifiedTimestampsIterate,
        SupportsAsyncIdentifiedTimestampsIterate,
    ]:
        """Configure input plugins according to generator parameters by
        wrapping it to merger, batcher and scheduler.

        Returns
        -------
        tuple[SupportsAsyncIdentifiedTimestampsIterate,\
            SupportsAsyncIdentifiedTimestampsIterate]
            Input configured for non interactive and interactive plugins.

        Raises
        ------
        ImproperlyConfiguredError
            If input plugins cannot be configured.

        """

        class PluginItem(TypedDict):
            plugins: list[InputPlugin]
            lax_batcher_mode: bool

        non_interactive_plugins, interactive_plugins = (
            list(
                filter(lambda plugin: not plugin.is_interactive, self._input),
            ),
            list(filter(lambda plugin: plugin.is_interactive, self._input)),
        )

        result: list[SupportsAsyncIdentifiedTimestampsIterate] = []

        items: list[PluginItem] = [
            {'plugins': non_interactive_plugins, 'lax_batcher_mode': False},
            {'plugins': interactive_plugins, 'lax_batcher_mode': True},
        ]

        for item in items:
            plugins = item['plugins']
            if len(plugins) > 1:
                logger.debug('Merging input plugins')
                try:
                    input: SupportsIdentifiedTimestampsSizedIterate = (
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
                input = IdentifiedTimestampsPluginAdapter(
                    plugin=plugins[0],
                )
            else:
                result.append(AsyncIdentifiedTimestampsEmptyAdapter())
                continue

            logger.debug('Wrapping to timestamps batcher')
            try:
                batcher = TimestampsBatcher(
                    source=input,
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
                logger.debug(
                    'Wrapping to batch scheduler and adapting '
                    'for async iteration',
                )
                result.append(
                    AsyncIdentifiedTimestampsSyncAdapter(
                        target=BatchScheduler(
                            source=batcher,
                            timezone=self._timezone,
                        ),
                    ),
                )
            else:
                logger.debug('Adapting batcher for async iteration')
                result.append(
                    AsyncIdentifiedTimestampsSyncAdapter(target=batcher),
                )

        return result[0], result[1]

    async def _open_output_plugins(self) -> None:
        """Open output plugins.

        Raises
        ------
        ExecutionError
            If opening for at least one output plugin fails.

        """
        try:
            async with asyncio.TaskGroup() as group:
                for plugin in self._output:
                    group.create_task(plugin.open())
        except* PluginOpenError as e:
            exceptions = cast('tuple[PluginOpenError]', e.exceptions)
            await asyncio.gather(
                *[
                    logger.aerror(str(exc), **exc.context)
                    for exc in exceptions
                ],
            )
            msg = 'Failed to open some of the output plugins'
            raise ExecutionError(msg, context={}) from None
        except* Exception as e:
            await logger.aexception(str(e))
            msg = 'Unexpected error occurred during opening output plugins'
            raise ExecutionError(msg, context={}) from e

    async def _close_output_plugins(self) -> None:
        """Close output plugins."""
        await asyncio.gather(
            *[plugin.close() for plugin in self._output],
            return_exceptions=True,
        )

    async def _execute(self) -> None:
        """Start execution of plugins in different threads.

        Raises
        ------
        ExecutionError
            If any error occurs during execution.

        """
        await logger.adebug('Setting event loop')
        loop = asyncio.get_running_loop()
        self._event_loop = loop

        await logger.adebug('Opening output plugins')
        await self._open_output_plugins()

        # input task is executed in underlying thread due to async adapter,
        # event task is executed in separate thread of loop thread pool
        # and output task is executed in current thread
        await logger.adebug('Starting input, event and output tasks')
        input_task = loop.create_task(
            self._execute_input(),
            name=f'execute-input-{self._params.id}',
        )
        loop.run_in_executor(
            executor=None,
            func=propagate_logger_context()(self._execute_event),
        )
        output_task = loop.create_task(
            self._execute_output(),
            name=f'execute-output-{self._params.id}',
        )

        done_event_task = loop.create_task(
            self._end_execution_event.wait(),
            name=f'monitor-done-{self._params.id}',
        )
        stop_event_task = loop.create_task(
            self._stop_event.wait(),
            name=f'monitor-stop-{self._params.id}',
        )

        done, _ = await asyncio.wait(
            [done_event_task, stop_event_task],
            return_when=asyncio.FIRST_COMPLETED,
        )

        if stop_event_task in done:
            await logger.adebug('Stop event is detected')

            # interactive plugin must be stopped anyway because they can use
            # underlying threads that serve interaction
            await logger.adebug('Stopping interactive input plugins')
            for plugin in self._input:
                if plugin.is_interactive:
                    plugin.stop_interacting()

            input_task.cancel()

            await output_task

            self._stop_event.clear()
            done_event_task.cancel()

        if done_event_task in done:
            await logger.adebug('Done event is detected')
            self._end_execution_event.clear()
            stop_event_task.cancel()

        await logger.adebug('Closing output plugins')
        await self._close_output_plugins()

        self._event_loop = None

    def execute(self) -> None:
        """Start execution of plugins.

        Raises
        ------
        ExecutionError
            If any error occurs during execution.

        Notes
        -----
        This method is intended to be called once per executor instance.

        """
        with asyncio.Runner(loop_factory=uvloop.new_event_loop) as runner:
            runner.run(self._execute())

    async def _execute_input(self) -> None:
        """Execute input plugins."""
        skip_past = self._params.live_mode and self._params.skip_past

        throttler = AsyncThrottler(limit=1, period=10)

        await logger.adebug('Starting to produce to timestamps queue')
        try:
            async with stream.merge(
                self._configured_non_interactive_input.iterate(
                    skip_past=skip_past,
                ),
                self._configured_interactive_input.iterate(
                    skip_past=skip_past,
                ),
            ).stream() as streamer:
                async for timestamps in streamer:
                    if (
                        self._timestamps_queue.async_q.full()
                        and self._params.live_mode
                    ):
                        await throttler(
                            logger.awarning,
                            (
                                'Timestamps queue is full, consider decreasing'
                                ' EPS or changing batching settings to avoid '
                                'time lag with actual event timestamps'
                            ),
                        )

                    await self._timestamps_queue.async_q.put(timestamps)

            await logger.adebug('Finishing input plugins execution')
        except asyncio.QueueShutDown:
            await logger.adebug(
                'Stopping input plugins execution due to downstream queue '
                'is closed',
            )
            for plugin in self._input:
                if plugin.is_interactive:
                    plugin.stop_interacting()
        except PluginGenerationError as e:
            await logger.aerror(str(e), **e.context)
        except Exception as e:  # noqa: BLE001
            await logger.aexception(
                'Unexpected error during input plugins execution',
                reason=str(e),
            )
        finally:
            if not self._timestamps_queue.closed:
                await self._timestamps_queue.async_q.put(None)
                await self._timestamps_queue.async_q.join()
                await self._timestamps_queue.aclose()

    def _execute_event(self) -> None:
        """Execute event plugin."""
        exhausted = False

        throttler = Throttler(limit=1, period=10)

        logger.debug('Starting to consume timestamps queue')
        while not exhausted:
            timestamps = self._timestamps_queue.sync_q.get()
            self._timestamps_queue.sync_q.task_done()

            if timestamps is None:
                break

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
                params['timestamp'] = timestamp.replace(tzinfo=self._timezone)

                try:
                    events.extend(self._event.produce(params))
                except PluginProduceError as e:
                    logger.error(str(e), **e.context)
                except PluginExhaustedError:
                    logger.debug(
                        'Events exhausted, closing upstream queue',
                    )
                    self._timestamps_queue.close()
                    exhausted = True
                    break
                except Exception as e:
                    logger.exception(
                        'Unexpected error during event plugin execution',
                        reason=str(e),
                    )

            if events:
                if self._events_queue.sync_q.full() and self._params.live_mode:
                    throttler(
                        logger.warning,
                        (
                            'Events queue is full, consider decreasing EPS '
                            'or changing batching settings to avoid time lag '
                            'with actual event timestamps'
                        ),
                    )

                self._events_queue.sync_q.put(events)

        logger.debug('Finishing event plugin execution')
        self._events_queue.sync_q.put(None)
        self._events_queue.sync_q.join()
        self._events_queue.close()

    def _handle_write_result(self, task: asyncio.Task[int]) -> None:
        """Handle result of output plugin write task.

        Parameters
        ----------
        task : asyncio.Task[int]
            Done future.

        """
        try:
            task.result()
        except PluginWriteError as e:
            logger.error(str(e), **e.context)
        except TimeoutError:
            logger.warning(
                (
                    'Write operation timed out, EPS is to high '
                    'for output target, consider decreasing EPS '
                    'or changing batching settings to avoid loosing events'
                ),
                task_name=task.get_name(),
                timeout=self._params.write_timeout,
            )
        except Exception as e:
            logger.exception(
                'Unexpected error occurred during output plugin write',
                reason=str(e),
            )
        except asyncio.CancelledError:
            logger.warning('Write operation discarded')
        finally:
            self._output_semaphore.release()
            self._output_tasks.remove(task)

    async def _execute_output(self) -> None:
        """Execute output plugins."""
        loop = asyncio.get_running_loop()

        gathering_tasks: list[asyncio.Task] = []
        await logger.adebug('Starting to consume events queue')
        while True:
            events = await self._events_queue.async_q.get()
            self._events_queue.async_q.task_done()

            if events is None:
                break

            for plugin in self._output:
                await self._output_semaphore.acquire()

                task = loop.create_task(
                    asyncio.wait_for(
                        plugin.write(events),
                        self._params.write_timeout,
                    ),
                    name=f'Writing with {plugin}',
                )
                self._output_tasks.add(task)
                gathering_tasks.append(task)

                task.add_done_callback(self._handle_write_result)

            if self._params.keep_order:
                await asyncio.gather(*gathering_tasks, return_exceptions=True)

            gathering_tasks.clear()

        if self._output_tasks:
            await asyncio.gather(*self._output_tasks, return_exceptions=True)
            self._output_tasks.clear()

        self._end_execution_event.set()

    def request_stop(self) -> None:
        """Request stop of execution. This method is expected to be
        called from thread other than the one executing `execute`
        method.

        Raises
        ------
        RuntimeError
            If executor is not currently executed.

        """
        if self._event_loop is None:
            msg = 'Not currently executed'
            raise RuntimeError(msg)

        if self._stop_event.is_set():
            return

        self._event_loop.call_soon_threadsafe(self._stop_event.set)
