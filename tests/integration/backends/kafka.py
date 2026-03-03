"""Kafka backend consumer for integration tests."""

import asyncio
import uuid

from aiokafka import AIOKafkaConsumer

from tests.integration.backends.base import BackendConsumer


class KafkaConsumer(BackendConsumer):
    """Consume events from a Kafka topic.

    Generates a unique topic name per instance. Kafka auto-creates
    topics on first produce, so ``setup`` and ``teardown`` are no-ops
    (test topics are ephemeral and cleaned up by broker retention).

    Wraps ``aiokafka.AIOKafkaConsumer`` to read messages from the
    beginning of the topic.
    """

    def __init__(
        self,
        bootstrap_servers: str = 'localhost:9094',
    ) -> None:
        self._bootstrap_servers = bootstrap_servers
        self._topic_name = f'eventum_test_{uuid.uuid4().hex[:12]}'

    @property
    def topic(self) -> str:
        """Name of the ephemeral test topic."""
        return self._topic_name

    async def setup(self) -> None:
        """No-op: Kafka auto-creates topics on first produce."""

    async def teardown(self) -> None:
        """No-op: test topics are ephemeral."""

    async def consume_all(
        self,
        timeout: float = 1.0,
    ) -> list[str]:
        """Read all messages from the topic from the beginning.

        Creates a fresh consumer each time, positioned at the
        earliest offset. Reads messages until no new message arrives
        for ``timeout`` seconds.

        Parameters
        ----------
        timeout : float
            Maximum idle time in seconds before stopping consumption.

        Returns
        -------
        list[str]
            List of message values decoded as UTF-8 strings.

        """
        consumer = AIOKafkaConsumer(
            self._topic_name,
            bootstrap_servers=self._bootstrap_servers,
            auto_offset_reset='earliest',
            enable_auto_commit=False,
            group_id=None,
        )
        await consumer.start()

        events: list[str] = []
        timeout_ms = int(timeout * 1000)

        try:
            while True:
                records = await consumer.getmany(
                    timeout_ms=timeout_ms,
                )
                if not records:
                    break

                for tp_records in records.values():
                    for record in tp_records:
                        if record.value is not None:
                            events.append(
                                record.value.decode('utf-8'),
                            )
        finally:
            await consumer.stop()

        return events

    async def count(self) -> int:
        """Return the number of messages in the topic.

        Kafka does not provide a direct count API, so this consumes
        all messages and returns the count.

        Returns
        -------
        int
            Message count.

        """
        events = await self.consume_all()
        return len(events)

    async def wait_for_count(
        self,
        expected: int,
        timeout: float = 30.0,
        poll_interval: float = 0.5,
    ) -> int:
        """Wait until the topic has at least `expected` messages.

        Creates a single consumer and reads messages into a buffer
        until the expected count is reached or the timeout expires.

        Parameters
        ----------
        expected : int
            Minimum number of messages to wait for.
        timeout : float
            Maximum time in seconds to wait.
        poll_interval : float
            Time in seconds to wait for each batch of messages.

        Returns
        -------
        int
            Actual message count when the wait finished.

        Raises
        ------
        TimeoutError
            If the expected count is not reached within the timeout.

        """
        consumer = AIOKafkaConsumer(
            self._topic_name,
            bootstrap_servers=self._bootstrap_servers,
            auto_offset_reset='earliest',
            enable_auto_commit=False,
            group_id=None,
        )
        await consumer.start()

        events: list[str] = []
        elapsed = 0.0
        batch_timeout_ms = int(poll_interval * 1000)

        try:
            while elapsed < timeout:
                records = await consumer.getmany(
                    timeout_ms=batch_timeout_ms,
                )
                for tp_records in records.values():
                    for record in tp_records:
                        if record.value is not None:
                            events.append(
                                record.value.decode('utf-8'),
                            )

                if len(events) >= expected:
                    return len(events)

                elapsed += poll_interval
        finally:
            await consumer.stop()

        if len(events) >= expected:
            return len(events)

        msg = (
            f'Timed out waiting for {expected} messages in '
            f'topic {self._topic_name} '
            f'(got {len(events)} after {timeout}s)'
        )
        raise TimeoutError(msg)
