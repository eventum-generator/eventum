"""Output stage of the pipeline — consumes events, writes to outputs."""

import asyncio
from typing import TYPE_CHECKING, cast

import structlog

from eventum.plugins.output.exceptions import PluginOpenError, PluginWriteError

if TYPE_CHECKING:
    from collections.abc import Sequence

    from eventum.core.parameters import GeneratorParameters
    from eventum.core.queue import PipelineQueue
    from eventum.plugins.output.base.plugin import OutputPlugin

logger = structlog.stdlib.get_logger()


class OutputStage:
    """Consumes event batches and writes to output plugins.

    Parameters
    ----------
    plugins : Sequence[OutputPlugin]
        Output plugins to use.

    params : GeneratorParameters
        Generator parameters.

    """

    def __init__(
        self,
        plugins: Sequence[OutputPlugin],
        params: GeneratorParameters,
    ) -> None:
        """Initialize output stage.

        Parameters
        ----------
        plugins : Sequence[OutputPlugin]
            Output plugins to use.

        params : GeneratorParameters
            Generator parameters.

        """
        self._plugins = list(plugins)
        self._params = params
        self._tasks: set[asyncio.Task] = set()
        self._semaphore = asyncio.Semaphore(
            value=self._params.max_concurrency,
        )

    async def open(self) -> None:
        """Open all output plugins for writing.

        Raises
        ------
        OutputStageError
            If opening for at least one output plugin fails.

        """
        from eventum.core.executor import ExecutionError

        try:
            async with asyncio.TaskGroup() as group:
                for plugin in self._plugins:
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

    async def close(self) -> None:
        """Close all output plugins."""
        await asyncio.gather(
            *[plugin.close() for plugin in self._plugins],
            return_exceptions=True,
        )

    async def execute(
        self,
        input: PipelineQueue[list[str]],
    ) -> None:
        """Consume event batches and write to output plugins.

        Parameters
        ----------
        input : PipelineQueue[list[str]]
            Queue of event batches to consume.

        """
        loop = asyncio.get_running_loop()

        gathering_tasks: list[asyncio.Task] = []
        await logger.adebug('Starting to consume events queue')

        while True:
            events = await asyncio.to_thread(input.get)

            if events is None:
                break

            for plugin in self._plugins:
                await self._semaphore.acquire()

                task = loop.create_task(
                    asyncio.wait_for(
                        plugin.write(events),
                        self._params.write_timeout,
                    ),
                    name=f'Writing with {plugin}',
                )
                self._tasks.add(task)
                gathering_tasks.append(task)

                task.add_done_callback(self._handle_write_result)

            if self._params.keep_order:
                await asyncio.gather(
                    *gathering_tasks,
                    return_exceptions=True,
                )

            gathering_tasks.clear()

        if self._tasks:
            await asyncio.gather(
                *self._tasks,
                return_exceptions=True,
            )
            self._tasks.clear()

    def _handle_write_result(self, task: asyncio.Task[int]) -> None:
        """Handle result of an output plugin write task.

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
                    'or changing batching settings to avoid '
                    'loosing events'
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
            self._semaphore.release()
            self._tasks.remove(task)
