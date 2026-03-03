"""Typed pipeline queue for inter-stage communication."""

import queue
from typing import Generic, TypeVar

T = TypeVar('T')


class PipelineQueue(Generic[T]):
    """Typed wrapper over stdlib queue with sentinel-based closing.

    Stages receive queues as constructor parameters and communicate
    exclusively through them.

    Parameters
    ----------
    maxsize : int
        Maximum number of items in the queue.

    """

    def __init__(self, maxsize: int) -> None:
        """Initialize pipeline queue.

        Parameters
        ----------
        maxsize : int
            Maximum number of items in the queue.

        """
        self._maxsize = maxsize
        self._queue: queue.Queue[T | None] = queue.Queue(maxsize=maxsize)

    def put(self, item: T) -> None:
        """Put an item into the queue.

        Parameters
        ----------
        item : T
            Item to put.

        Raises
        ------
        queue.ShutDown
            If the queue has been shut down.

        """
        self._queue.put(item)

    def get(self) -> T | None:
        """Get an item from the queue.

        Returns
        -------
        T | None
            Item from the queue, or ``None`` if the queue has been
            closed via sentinel.

        Raises
        ------
        queue.ShutDown
            If the queue has been shut down.

        """
        item = self._queue.get()
        self._queue.task_done()
        return item

    def close(self) -> None:
        """Close the queue by sending sentinel and waiting for it
        to be consumed.

        Safe to call even if the queue has already been shut down.
        """
        try:
            self._queue.put(None)
            self._queue.join()
        except queue.ShutDown:
            pass

    def shutdown(self) -> None:
        """Shut down the queue immediately without sending sentinel.

        Useful for stopping upstream producers when downstream has
        exhausted.
        """
        self._queue.shutdown(immediate=True)

    @property
    def is_full(self) -> bool:
        """Whether the queue is full."""
        return self._queue.full()
