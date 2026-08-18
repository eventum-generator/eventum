"""Size and delay based batcher of timestamp arrays."""

from collections.abc import Iterator
from datetime import timedelta
from typing import override

import numpy as np

from eventum.plugins.input.accumulator import BatchAccumulator
from eventum.plugins.input.protocols import (
    IdentifiedTimestamps,
    SupportsIdentifiedTimestampsIterate,
    SupportsIdentifiedTimestampsSizedIterate,
)

DEFAULT_READ_SIZE = 10_000


class TimestampsBatcher(SupportsIdentifiedTimestampsIterate):
    """Batcher of timestamps.

    Attributes
    ----------
    MIN_BATCH_SIZE : int
        Minimum batch size that can be configured for batcher.

    MIN_BATCH_DELAY : float
        Minimum batch delay that can be configured for batcher.

    """

    MIN_BATCH_SIZE = 1
    MIN_BATCH_DELAY = 0.1

    def __init__(
        self,
        source: SupportsIdentifiedTimestampsSizedIterate,
        batch_size: int | None = 100_000,
        batch_delay: float | None = None,
        lax: bool = False,  # noqa: FBT001, FBT002
    ) -> None:
        """Initialize batcher.

        Parameters
        ----------
        source : SupportsIdentifiedTimestampsSizedIterate
            Source of identified timestamp arrays.

        batch_size : int | None, default=100_000
            Maximum size of producing batches, not limited if value is
            `None`, cannot be  less than `MIN_BATCH_SIZE` attribute.

        batch_delay: float | None, default=None
            Maximum time span (in seconds) of timestamps accumulated
            into a single batch, not limited if value is `None`, cannot
            be less then `MIN_BATCH_DELAY` attribute.

        lax : bool, default=False
            Whether the batches should not be accumulated but only
            chunked. In this mode iterations of consuming timestamps
            are isolated from each other and not concatenated.

        Raises
        ------
        ValueError
            If some parameter is out of allowed range.

        """
        if batch_size is None and batch_delay is None:
            msg = 'Batch size and delay cannot be both omitted'
            raise ValueError(msg)

        if batch_size is not None and not batch_size >= self.MIN_BATCH_SIZE:
            msg = (
                f'Batch size must be greater or equal to {self.MIN_BATCH_SIZE}'
            )
            raise ValueError(msg)

        if batch_delay is not None and batch_delay < self.MIN_BATCH_DELAY:
            msg = (
                'Batch delay must be greater or equal to '
                f'{self.MIN_BATCH_DELAY}'
            )
            raise ValueError(msg)

        self._batch_size = batch_size
        self._batch_delay = batch_delay

        self._source = source
        self._lax_mode_enabled = lax

    def _get_cutoff_index(
        self,
        accumulator: BatchAccumulator,
        array: IdentifiedTimestamps,
        window: np.timedelta64 | None,
    ) -> int:
        """Get index the array must be cut at to keep the time span of
        the accumulated batch within the window.

        Parameters
        ----------
        accumulator : BatchAccumulator
            Accumulator the array is going to be pushed to.

        array : IdentifiedTimestamps
            Array to find index for.

        window : np.timedelta64 | None
            Maximum time span of a single batch, not limited if value
            is `None`.

        Returns
        -------
        int
            Cutoff index.

        """
        if window is None:
            return array.size

        first_timestamp = accumulator.first_timestamp

        if first_timestamp is None:
            first_timestamp = array['timestamp'][0]

        latest_timestamp = first_timestamp + window
        timestamps = array['timestamp']

        if latest_timestamp < timestamps[-1]:
            return int(
                np.searchsorted(
                    a=timestamps,
                    v=latest_timestamp,  # type: ignore[assignment]
                    side='left',
                ),
            )

        return array.size

    def _iterate(
        self,
        iterator: Iterator[IdentifiedTimestamps],
        window: np.timedelta64 | None,
    ) -> Iterator[IdentifiedTimestamps]:
        """Iterate over batches.

        Parameters
        ----------
        iterator: Iterator[IdentifiedTimestamps]
            Iterator to use.

        window : np.timedelta64 | None
            Maximum time span of a single batch, not limited if value
            is `None`.

        Yields
        ------
        IdentifiedTimestamps
            Batch of timestamps.

        """
        accumulator = BatchAccumulator(max_size=self._batch_size)

        for array in iterator:
            remaining = array

            while remaining.size > 0:
                cutoff_index = self._get_cutoff_index(
                    accumulator=accumulator,
                    array=remaining,
                    window=window,
                )
                batches = accumulator.push(remaining[:cutoff_index])
                remaining = remaining[cutoff_index:]

                if batches:
                    # window is recomputed for the kept remainder
                    yield from batches
                elif remaining.size > 0:
                    # window is closed by the timestamps left out of it
                    yield from accumulator.flush()

                if self._lax_mode_enabled:
                    yield from accumulator.flush()

        yield from accumulator.flush()

    @override
    def iterate(
        self,
        *,
        skip_past: bool = True,
    ) -> Iterator[IdentifiedTimestamps]:
        iterator = self._source.iterate(
            size=self._batch_size or DEFAULT_READ_SIZE,
            skip_past=skip_past,
        )

        if self._batch_delay is None:
            window = None
        else:
            window = np.timedelta64(  # type: ignore[call-overload]
                timedelta(seconds=self._batch_delay),
                'us',
            )

        yield from self._iterate(iterator=iterator, window=window)
