"""Scheduler for publishing timestamps at moments in time that
correspond to the value of those timestamps.
"""

import time
from collections.abc import Iterator
from threading import Event
from typing import TYPE_CHECKING, override
from zoneinfo import ZoneInfo

from eventum.plugins.input.accumulator import BatchAccumulator
from eventum.plugins.input.protocols import (
    IdentifiedTimestamps,
    SupportsIdentifiedTimestampsIterate,
)
from eventum.plugins.input.utils.time_utils import (
    now64,
    timedelta64_to_seconds,
)

if TYPE_CHECKING:
    import numpy as np


class BatchScheduler(SupportsIdentifiedTimestampsIterate):
    """Scheduler of timestamp batches. Scheduler iterates over batches
    of timestamps and does not yield them immediately, but it waits
    until current time reaches the last timestamp in the batch.

    Batches that are already due are published without waiting, so they
    are merged together until they reach `max_batch_size`, instead of
    being published one by one.

    Parameters
    ----------
    source : SupportsIdentifiedTimestampsIterate
        Timestamps source.

    timezone : ZoneInfo
        Timezone of timestamps in batches, used to match timestamps
        with current time.

    stop_event : Event | None, default=None
        If provided, the scheduler will check this event during sleep
        and exit early when it is set.

    max_batch_size : int | None, default=None
        Maximum size of batches merged from the due ones, due batches
        are published as is if value is `None`.

    """

    def __init__(
        self,
        source: SupportsIdentifiedTimestampsIterate,
        timezone: ZoneInfo,
        stop_event: Event | None = None,
        max_batch_size: int | None = None,
    ) -> None:
        """Initialize scheduler.

        Parameters
        ----------
        source : SupportsIdentifiedTimestampsIterate
            Timestamps source.

        timezone : ZoneInfo
            Timezone of timestamps in batches, used to match timestamps
            with current time.

        stop_event : Event | None, default=None
            If provided, the scheduler will check this event during
            sleep and exit early when it is set.

        max_batch_size : int | None, default=None
            Maximum size of batches merged from the due ones, due
            batches are published as is if value is `None`.

        """
        self._source = source
        self._timezone = timezone
        self._stop_event = stop_event
        self._max_batch_size = max_batch_size

    def _get_delay(self, array: IdentifiedTimestamps) -> float:
        """Get time to wait before publishing the batch.

        Parameters
        ----------
        array : IdentifiedTimestamps
            Batch of timestamps.

        Returns
        -------
        float
            Number of seconds to wait, zero for the due batch.

        """
        latest_timestamp: np.datetime64 = array['timestamp'][-1]
        delta = latest_timestamp - now64(self._timezone)

        return max(timedelta64_to_seconds(timedelta=delta), 0)

    def _wait(self, delay: float) -> bool:
        """Wait for the specified time.

        Parameters
        ----------
        delay : float
            Number of seconds to wait.

        Returns
        -------
        bool
            Whether the waiting was interrupted by stop event.

        """
        if self._stop_event is None:
            time.sleep(delay)
            return False

        return self._stop_event.wait(timeout=delay)

    @override
    def iterate(
        self,
        *,
        skip_past: bool = True,
    ) -> Iterator[IdentifiedTimestamps]:
        accumulator = BatchAccumulator(max_size=self._max_batch_size)

        for array in self._source.iterate(skip_past=skip_past):
            delay = self._get_delay(array)

            if delay == 0 and self._max_batch_size is not None:
                yield from accumulator.push(array)
                continue

            # due timestamps are published before waiting for the rest
            yield from accumulator.flush()

            if delay > 0 and self._wait(delay):
                return

            yield array

        yield from accumulator.flush()
