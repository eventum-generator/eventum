"""Scheduler for publishing timestamps at moments in time that
correspond to the value of those timestamps.
"""

import time
from collections.abc import Iterator
from threading import Event
from typing import TYPE_CHECKING, override
from zoneinfo import ZoneInfo

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

    """

    def __init__(
        self,
        source: SupportsIdentifiedTimestampsIterate,
        timezone: ZoneInfo,
        stop_event: Event | None = None,
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

        """
        self._source = source
        self._timezone = timezone
        self._stop_event = stop_event

    @override
    def iterate(
        self,
        *,
        skip_past: bool = True,
    ) -> Iterator[IdentifiedTimestamps]:
        for array in self._source.iterate(skip_past=skip_past):
            now = now64(self._timezone)
            latest_ts: np.datetime64 = array['timestamp'][-1]
            delta = latest_ts - now
            delay = max(timedelta64_to_seconds(timedelta=delta), 0)

            if delay > 0:
                if self._stop_event is not None:
                    if self._stop_event.wait(timeout=delay):
                        return
                else:
                    time.sleep(delay)

            yield array
