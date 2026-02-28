"""Executor that orchestrates the input - event - output pipeline."""

import asyncio
from collections.abc import Sequence
from threading import Event, Thread

import structlog

from eventum.core.parameters import GeneratorParameters
from eventum.core.queue import PipelineQueue
from eventum.core.stages import EventStage, InputStage, OutputStage
from eventum.exceptions import ContextualError
from eventum.plugins.event.base.plugin import EventPlugin
from eventum.plugins.input.base.plugin import InputPlugin
from eventum.plugins.input.protocols import IdentifiedTimestamps
from eventum.plugins.output.base.plugin import OutputPlugin

logger = structlog.stdlib.get_logger()


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
        if not input:
            msg = 'At least one input plugin must be provided'
            raise ValueError(msg)

        if not output:
            msg = 'At least one output plugin must be provided'
            raise ValueError(msg)

        self._params = params
        self._stop_event = Event()
        self._skip_past = params.live_mode and params.skip_past
        self._execution_error: ExecutionError | None = None

        logger.debug('Initializing queues')
        self._timestamps_queue: PipelineQueue[IdentifiedTimestamps] = (
            PipelineQueue(maxsize=params.queue.max_timestamp_batches)
        )
        self._events_queue: PipelineQueue[list[str]] = PipelineQueue(
            maxsize=params.queue.max_event_batches,
        )

        logger.debug('Configuring stages')
        self._input_stage = InputStage(plugins=input, params=params)
        self._input_stage.configure(stop_event=self._stop_event)

        self._event_stage = EventStage(
            plugin=event,
            input_tags=self._input_stage.input_tags,
            params=params,
        )
        self._output_stage = OutputStage(plugins=output, params=params)

    def execute(self) -> None:
        """Start the pipeline and block until all stages complete.

        Raises
        ------
        ExecutionError
            If a fatal error occurs (e.g. output plugins fail to open).

        """
        threads = self._start_pipeline()
        self._await_pipeline(threads)

        if self._execution_error is not None:
            raise self._execution_error

    def request_stop(self) -> None:
        """Request graceful stop from another thread. Idempotent."""
        if self._stop_event.is_set():
            return

        self._stop_event.set()
        self._input_stage.stop_interactive_plugins()

    # -- Pipeline orchestration ----------------------------------------

    def _start_pipeline(self) -> tuple[Thread, Thread, Thread]:
        """Create and start all stage threads.

        Start order: output (consumer), event, input (producer).
        Consumers start first so they are ready when producers begin.
        """
        gen_id = self._params.id

        input_thread = Thread(
            target=self._run_input_stage,
            name=f'input:{gen_id}',
        )
        event_thread = Thread(
            target=self._run_event_stage,
            name=f'event:{gen_id}',
        )
        output_thread = Thread(
            target=self._run_output_stage,
            name=f'output:{gen_id}',
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

    # -- Stage runners (one per thread) --------------------------------

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

    def _run_output_stage(self) -> None:
        try:
            asyncio.run(self._execute_output_stage())
        except ExecutionError as e:
            self._execution_error = e
            self._abort_upstream()
        except Exception:
            logger.exception('Unexpected error in output stage')
            self._abort_upstream()

    def _abort_upstream(self) -> None:
        """Unblock upstream stages after output stage failure.

        Without this, a failed output stage leaves the event and
        input stages hanging on queue put/close operations.
        """
        self._events_queue.shutdown()
        self._timestamps_queue.shutdown()
        self._stop_event.set()

    async def _execute_output_stage(self) -> None:
        """Open output plugins, run the write loop, close plugins."""
        try:
            await self._output_stage.open()
            await self._output_stage.execute(input=self._events_queue)
        finally:
            await self._output_stage.close()
