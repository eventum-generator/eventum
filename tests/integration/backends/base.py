"""Abstract base class for backend consumers in integration tests."""

import asyncio
from abc import ABC, abstractmethod


class BackendConsumer(ABC):
    """Base class for consuming events from backend services.

    Backend consumers provide a unified interface for reading events
    written by output plugins during integration tests. Each concrete
    consumer wraps a specific backend (OpenSearch, ClickHouse, Kafka,
    TCP) and exposes methods to retrieve, count, and wait for events.
    """

    @abstractmethod
    async def setup(self) -> None:
        """Prepare the backend resource (create index, table, etc.)."""

    @abstractmethod
    async def teardown(self) -> None:
        """Clean up the backend resource (delete index, table, etc.)."""

    @abstractmethod
    async def consume_all(self, timeout: float = 10.0) -> list[str]:
        """Return all events currently stored in the backend.

        Parameters
        ----------
        timeout : float
            Maximum time in seconds to wait for events.

        Returns
        -------
        list[str]
            List of event payloads as strings.

        """

    @abstractmethod
    async def count(self) -> int:
        """Return the number of events currently stored in the backend.

        Returns
        -------
        int
            Event count.

        """

    async def wait_for_count(
        self,
        expected: int,
        timeout: float = 30.0,
        poll_interval: float = 0.5,
    ) -> int:
        """Wait until the backend has at least `expected` events.

        Polls ``count()`` at regular intervals until the count reaches
        or exceeds ``expected``, or the timeout is exceeded.

        Parameters
        ----------
        expected : int
            Minimum number of events to wait for.
        timeout : float
            Maximum time in seconds to wait.
        poll_interval : float
            Time in seconds between successive polls.

        Returns
        -------
        int
            Actual event count when the wait finished.

        Raises
        ------
        TimeoutError
            If the expected count is not reached within the timeout.

        """
        elapsed = 0.0

        while elapsed < timeout:
            actual = await self.count()
            if actual >= expected:
                return actual
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        actual = await self.count()
        if actual >= expected:
            return actual

        msg = (
            f'Timed out waiting for {expected} events '
            f'(got {actual} after {timeout}s)'
        )
        raise TimeoutError(msg)
