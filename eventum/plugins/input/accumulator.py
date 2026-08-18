"""Accumulator of timestamp arrays into size limited batches."""

import numpy as np

from eventum.plugins.input.protocols import IdentifiedTimestamps
from eventum.plugins.input.utils.array_utils import chunk_array


class BatchAccumulator:
    """Accumulator of identified timestamps into batches of limited
    size. Pushed arrays are accumulated until they form a complete
    batch, incomplete remainder is kept for the following pushes until
    it is taken away by flushing. Both operations return batches that
    are ready to be published.

    Parameters
    ----------
    max_size : int | None
        Maximum size of formed batches, not limited if value is `None`.

    """

    def __init__(self, max_size: int | None) -> None:
        """Initialize accumulator.

        Parameters
        ----------
        max_size : int | None
            Maximum size of formed batches, not limited if value is
            `None`.

        Raises
        ------
        ValueError
            If `max_size` is less than 1.

        """
        if max_size is not None and max_size < 1:
            msg = 'Parameter `max_size` must be greater or equal to 1'
            raise ValueError(msg)

        self._max_size = max_size
        self._arrays: list[IdentifiedTimestamps] = []
        self._size = 0

    def push(
        self,
        array: IdentifiedTimestamps,
    ) -> list[IdentifiedTimestamps]:
        """Push array of timestamps to accumulator.

        Parameters
        ----------
        array : IdentifiedTimestamps
            Array to push.

        Returns
        -------
        list[IdentifiedTimestamps]
            Batches completed by this push, empty list if none of them
            is complete yet.

        """
        if array.size == 0:
            return []

        self._arrays.append(array)
        self._size += array.size

        if self._max_size is None or self._size < self._max_size:
            return []

        batches = chunk_array(
            array=np.concatenate(self._arrays),
            size=self._max_size,
        )
        self._reset()

        if batches[-1].size < self._max_size:
            self._push_back(batches.pop())

        return batches

    def flush(self) -> list[IdentifiedTimestamps]:
        """Take away all accumulated timestamps as incomplete batch.

        Returns
        -------
        list[IdentifiedTimestamps]
            Batch of accumulated timestamps, empty list if accumulator
            is empty.

        """
        if not self._arrays:
            return []

        array = np.concatenate(self._arrays)
        self._reset()

        return [array]

    def _push_back(self, array: IdentifiedTimestamps) -> None:
        """Return array to the emptied accumulator."""
        self._arrays.append(array)
        self._size += array.size

    def _reset(self) -> None:
        """Drop all accumulated timestamps."""
        self._arrays.clear()
        self._size = 0

    @property
    def size(self) -> int:
        """Current number of accumulated timestamps."""
        return self._size

    @property
    def first_timestamp(self) -> np.datetime64 | None:
        """First accumulated timestamp, `None` if accumulator is empty."""
        if not self._arrays:
            return None

        return self._arrays[0]['timestamp'][0]
