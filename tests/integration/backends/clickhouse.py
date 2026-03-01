"""ClickHouse backend consumer for integration tests."""

import asyncio
import uuid
from functools import partial

import clickhouse_connect
from clickhouse_connect.driver.client import Client

from tests.integration.backends.base import BackendConsumer

DATABASE = 'eventum_test'


class ClickHouseConsumer(BackendConsumer):
    """Consume events from a ClickHouse table.

    Creates a unique, ephemeral table in the ``eventum_test`` database
    per instance so that tests never collide. Uses the synchronous
    ``clickhouse_connect`` client with calls dispatched to a thread
    pool via ``asyncio.to_thread``.
    """

    def __init__(
        self,
        host: str = 'localhost',
        port: int = 8123,
    ) -> None:
        self._host = host
        self._port = port
        self._table_name = f'eventum_{uuid.uuid4().hex[:12]}'
        self._client: Client | None = None

    @property
    def database(self) -> str:
        """Name of the test database."""
        return DATABASE

    @property
    def table(self) -> str:
        """Name of the ephemeral test table."""
        return self._table_name

    async def setup(self) -> None:
        """Create the test table in the ``eventum_test`` database.

        The table uses ``MergeTree`` engine with an empty
        ``ORDER BY tuple()`` since test data does not need
        a specific sort key.
        """
        self._client = await asyncio.to_thread(
            partial(
                clickhouse_connect.get_client,
                host=self._host,
                port=self._port,
            ),
        )

        await asyncio.to_thread(
            self._client.command,
            f'CREATE DATABASE IF NOT EXISTS {DATABASE}',
        )

        await asyncio.to_thread(
            self._client.command,
            f'CREATE TABLE {DATABASE}.{self._table_name} '
            f'(event String) '
            f'ENGINE = MergeTree() ORDER BY tuple()',
        )

    async def teardown(self) -> None:
        """Drop the test table and close the client."""
        if self._client is None:
            return

        try:
            await asyncio.to_thread(
                self._client.command,
                f'DROP TABLE IF EXISTS '
                f'{DATABASE}.{self._table_name}',
            )
        finally:
            self._client.close()
            self._client = None

    async def consume_all(
        self,
        timeout: float = 10.0,
    ) -> list[str]:
        """Return all rows from the ``event`` column.

        Parameters
        ----------
        timeout : float
            Not directly used for ClickHouse queries but kept
            for interface consistency.

        Returns
        -------
        list[str]
            List of event strings.

        """
        assert self._client is not None

        result = await asyncio.to_thread(
            self._client.query,
            f'SELECT event FROM {DATABASE}.{self._table_name}',
        )
        return [row[0] for row in result.result_rows]

    async def count(self) -> int:
        """Return the number of rows in the test table.

        Returns
        -------
        int
            Row count.

        """
        assert self._client is not None

        result = await asyncio.to_thread(
            self._client.command,
            f'SELECT count() FROM {DATABASE}.{self._table_name}',
        )
        return int(result)  # type: ignore[arg-type]
