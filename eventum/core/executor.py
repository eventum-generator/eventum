"""Executor that orchestrates the input - event - output pipeline."""

import asyncio
import contextlib
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from threading import Event, Lock, Thread

import structlog

from eventum.core.parameters import GeneratorParameters
from eventum.core.queue import PipelineQueue, estimate_events_bytes
from eventum.core.resources import QueuesUsage, QueueUsage
from eventum.core.stages import EventStage, InputStage, OutputStage
from eventum.exceptions import ContextualError
from eventum.plugins.event.base.plugin import EventPlugin
from eventum.plugins.input.base.plugin import InputPlugin
from eventum.plugins.input.protocols import IdentifiedTimestamps
from eventum.plugins.output.base.plugin import OutputPlugin

logger = structlog.stdlib.get_logger()

ABORT_TIMEOUT = 10
"""Seconds an aborted execution is given to end.

Aborting interrupts everything that waits on the pipeline itself, so
what keeps an execution alive past this is plugin code that does not
return.
"""

ABORT_CLOSE_TIMEOUT = 5
"""Seconds output plugins are given to close once execution is aborted,
so a plugin flushing to an unreachable target cannot hold the abort
back. Kept under the abort timeout.
"""


def max_stop_seconds(params: GeneratorParameters) -> float:
    """Longest time a stop of an execution with these parameters may
    take before it gives the execution up.

    Parameters
    ----------
    params : GeneratorParameters
        Parameters of the execution.

    Returns
    -------
    float
        Seconds of the graceful stop and of the abort together.

    """
    return params.stop_timeout + ABORT_TIMEOUT


class ImproperlyConfiguredError(ContextualError):
    """Plugins cannot be executed with provided parameters."""


class ExecutionError(ContextualError):
    """Execution error."""


class Executor:
    """Orchestrates the input - event - output pipeline.

    Each stage runs in its own thread. Input and event stages are
    synchronous; the output stage runs an asyncio event loop for
    concurrent writes.

    Parameters
    ----------
    input : Sequence[InputPlugin]
        Input plugins.

    event : EventPlugin
        Event plugin.

    output : Sequence[OutputPlugin]
        Output plugins.

    params : GeneratorParameters
        Generator parameters.

    Raises
    ------
    ValueError
        If input or output plugin sequences are empty.

    ImproperlyConfiguredError
        If the input pipeline cannot be configured.

    """

    def __init__(
        self,
        input: Sequence[InputPlugin],
        event: EventPlugin,
        output: Sequence[OutputPlugin],
        params: GeneratorParameters,
    ) -> None:
        """Initialize executor with plugin stages and parameters."""
        if not input:
            msg = 'At least one input plugin must be provided'
            raise ValueError(msg)

        if not output:
            msg = 'At least one output plugin must be provided'
            raise ValueError(msg)

        self._params = params
        self._logger = logger.bind(generator_id=params.id)
        self._stop_event = Event()
        self._done_event = Event()
        self._skip_past = params.live_mode and params.skip_past
        self._execution_error: ExecutionError | None = None

        # Guards the abort flag against the output stage registering
        # its task, so an abort never misses a task being started.
        self._abort_lock = Lock()
        self._is_aborted = False

        self._discard_lock = Lock()
        self._discarded_events = 0
        self._output_loop: asyncio.AbstractEventLoop | None = None
        self._output_task: asyncio.Task | None = None
        self._output_pool: ThreadPoolExecutor | None = None

        logger.debug('Initializing queues')
        self._timestamps_queue: PipelineQueue[IdentifiedTimestamps] = (
            PipelineQueue(
                maxsize=params.queue.max_timestamp_batches,
                sizer=lambda timestamps: timestamps.nbytes,
            )
        )
        self._events_queue: PipelineQueue[list[str]] = PipelineQueue(
            maxsize=params.queue.max_event_batches,
            sizer=estimate_events_bytes,
            max_bytes=params.queue.max_event_bytes,
        )

        logger.debug('Configuring stages')
        self._input_stage = InputStage(plugins=input, params=params)
        self._input_stage.configure(stop_event=self._stop_event)

        self._event_stage = EventStage(
            plugin=event,
            input_tags=self._input_stage.input_tags,
            params=params,
            abandon_input=self._input_stage.stop,
            discard_events=self._count_discarded,
        )
        self._output_stage = OutputStage(
            plugins=output,
            params=params,
            discard_events=self._count_discarded,
        )

    def execute(self) -> None:
        """Start the pipeline and block until all stages complete.

        Raises
        ------
        ExecutionError
            If a fatal error occurs (e.g. output plugins fail to open).

        """
        try:
            threads = self._start_pipeline()
            self._await_pipeline(threads)
        finally:
            discarded = self.discarded_events
            if discarded:
                self._logger.warning(
                    'Events produced but not written are discarded',
                    count=discarded,
                )

            self._done_event.set()

        if self._execution_error is not None:
            raise self._execution_error

    def request_stop(self) -> None:
        """Request graceful stop from another thread. Idempotent."""
        self._input_stage.stop()

    def abort(self) -> None:
        """Discard what the pipeline holds and cancel the output stage.

        Shuts the queues down without waiting for what they hold to be
        consumed, stops the input and cancels the output stage wherever
        it waits - opening, writing or closing plugins. Idempotent and
        safe to call from any thread.
        """
        with self._abort_lock:
            if self._is_aborted:
                return

            self._is_aborted = True
            loop = self._output_loop
            task = self._output_task
            pool = self._output_pool

        # Cancelled before the queues are shut down, so the output stage
        # learns of the abort from the cancellation rather than from a
        # queue it would start closing plugins over, only to have the
        # cancellation interrupt that close.
        if loop is not None and task is not None and pool is not None:
            # A closed loop raises, meaning the output stage has ended.
            # The pool goes first, so what the stage does on its way
            # out does not queue behind calls that never return.
            with contextlib.suppress(RuntimeError):
                loop.call_soon_threadsafe(
                    self._abandon_output_pool,
                    loop,
                    pool,
                )
                loop.call_soon_threadsafe(task.cancel)

        discarded = self._abort_upstream()

        self._logger.warning(
            'Execution is aborted, events waiting to be written are discarded',
            count=discarded,
        )

    @property
    def discarded_events(self) -> int:
        """Number of events produced but discarded unwritten."""
        with self._discard_lock:
            return self._discarded_events

    def _count_discarded(self, count: int) -> None:
        """Count events produced but discarded unwritten. Safe to call
        from any thread.
        """
        with self._discard_lock:
            self._discarded_events += count

    def stop(self) -> bool:
        """Stop execution within bounded time from another thread.

        Requests a graceful stop first, letting the pipeline deliver
        what it has already produced. An execution still running after
        `stop_timeout` of the parameters is aborted. A stop following
        an abort goes straight to waiting for the aborted execution.

        Returns
        -------
        bool
            `True` if the execution ended, `False` if it is still
            running after the abort, which leaves its threads to plugin
            code that does not return.

        """
        if not self._is_aborted:
            self.request_stop()

            if self._done_event.wait(self._params.stop_timeout):
                return True

            self._logger.warning(
                'Execution did not stop gracefully, aborting it',
                timeout=self._params.stop_timeout,
            )
            self.abort()

        return self._done_event.wait(ABORT_TIMEOUT)

    # - Pipeline orchestration ----------------------------------------

    def _start_pipeline(self) -> tuple[Thread, Thread, Thread]:
        """Create and start all stage threads.

        Start order: output (consumer), event, input (producer).
        Consumers start first so they are ready when producers begin.
        """
        gen_id = self._params.id

        # Daemon threads, as a stage stuck in plugin code is abandoned
        # rather than joined and must not keep the process from exiting.
        input_thread = Thread(
            target=self._run_input_stage,
            name=f'input:{gen_id}',
            daemon=True,
        )
        event_thread = Thread(
            target=self._run_event_stage,
            name=f'event:{gen_id}',
            daemon=True,
        )
        output_thread = Thread(
            target=self._run_output_stage,
            name=f'output:{gen_id}',
            daemon=True,
        )

        output_thread.start()
        event_thread.start()
        input_thread.start()

        return input_thread, event_thread, output_thread

    def _await_pipeline(
        self,
        threads: tuple[Thread, Thread, Thread],
    ) -> None:
        """Join all stage threads in cascade order.

        Join order: input, event, output. Input finishes and closes the
        timestamps queue; event sees the sentinel, finishes, and closes
        the events queue; output sees the sentinel and drains.
        """
        input_thread, event_thread, output_thread = threads

        input_thread.join()
        event_thread.join()
        output_thread.join()

    # - Stage runners (one per thread) --------------------------------

    def _run_input_stage(self) -> None:
        self._input_stage.execute(
            output=self._timestamps_queue,
            skip_past=self._skip_past,
        )

    def _run_event_stage(self) -> None:
        self._event_stage.execute(
            input=self._timestamps_queue,
            output=self._events_queue,
        )

    def queue_usage(self) -> QueuesUsage:
        """Get fill levels of the queues between the stages.

        Returns
        -------
        QueuesUsage
            Fill level of the timestamps and the events queue.

        """
        return QueuesUsage(
            timestamps=QueueUsage(
                size=self._timestamps_queue.size,
                maxsize=self._timestamps_queue.maxsize,
                size_bytes=self._timestamps_queue.size_bytes,
                max_bytes=self._timestamps_queue.max_bytes,
            ),
            events=QueueUsage(
                size=self._events_queue.size,
                maxsize=self._events_queue.maxsize,
                size_bytes=self._events_queue.size_bytes,
                max_bytes=self._events_queue.max_bytes,
            ),
        )

    def _run_output_stage(self) -> None:
        try:
            asyncio.run(self._execute_output_stage())
        except ExecutionError as e:
            self._execution_error = e
            self._abort_upstream()
        except asyncio.CancelledError:
            logger.debug('Output stage is aborted')
        except Exception:
            logger.exception('Unexpected error in output stage')
            self._abort_upstream()

    def _abort_upstream(self) -> int:
        """Unblock upstream stages after output stage failure.

        Without this, a failed output stage leaves the event and
        input stages hanging on queue put/close operations, and an
        interactive input waiting for interaction.

        Returns
        -------
        int
            Number of events the events queue held, counted as
            discarded.

        """
        # Counted before the queue lets the stages go, so the total the
        # execution reports as it ends already holds these events.
        with self._discard_lock:
            discarded = sum(
                len(batch) for batch in self._events_queue.shutdown()
            )
            self._discarded_events += discarded

        self._timestamps_queue.shutdown()
        self._input_stage.stop()

        return discarded

    async def _execute_output_stage(self) -> None:
        """Open output plugins, run the write loop, close plugins.

        Replaces the default executor of the loop with a pool named
        after the generator, so the CPU time of the work the stage
        offloads - event formatting above all - is accounted for the
        generator that caused it. The pool is shut down along with the
        loop, or left to its threads once aborted.

        Registers its task for an abort to cancel, and closes plugins
        within a bound once aborted.
        """
        loop = asyncio.get_running_loop()

        with self._abort_lock:
            if self._is_aborted:
                return

            self._output_loop = loop
            self._output_task = asyncio.current_task()
            self._output_pool = self._make_output_pool()
            loop.set_default_executor(self._output_pool)

        try:
            await self._output_stage.open()
            await self._output_stage.execute(input=self._events_queue)
        finally:
            if self._is_aborted:
                await self._close_aborted_output()
            else:
                await self._close_output()

    def _make_output_pool(self) -> ThreadPoolExecutor:
        """Create a pool for the work the output stage offloads."""
        return ThreadPoolExecutor(
            thread_name_prefix=f'output-worker:{self._params.id}:',
        )

    def _abandon_output_pool(
        self,
        loop: asyncio.AbstractEventLoop,
        pool: ThreadPoolExecutor,
    ) -> None:
        """Leave calls of an aborted execution to their own threads.

        The loop waits for its default executor as it closes, so a
        plugin call that never returns would keep the stage from
        ending. The pool is shut down without waiting, and the loop is
        given an idle one in its place.
        """
        pool.shutdown(wait=False, cancel_futures=True)
        loop.set_default_executor(self._make_output_pool())

    async def _close_output(self) -> None:
        """Close output plugins, reporting a close cut by an abort."""
        try:
            await self._output_stage.close()
        except asyncio.CancelledError:
            if self._is_aborted:
                logger.warning('Output plugins did not close before abort')
            raise

    async def _close_aborted_output(self) -> None:
        """Close output plugins of an aborted execution in time."""
        try:
            async with asyncio.timeout(ABORT_CLOSE_TIMEOUT):
                await self._output_stage.close()
        except TimeoutError:
            await logger.awarning(
                'Output plugins did not close in time after abort',
                timeout=ABORT_CLOSE_TIMEOUT,
            )
