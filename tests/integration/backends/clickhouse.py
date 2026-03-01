"""ClickHouse backend consumer for integration tests."""

import asyncio
import json
import uuid
from functools import partial

import clickhouse_connect
from clickhouse_connect.driver.client import Client

from tests.integration.backends.base import BackendConsumer

DATABASE = 'eventum_test'

# Columns for the ECS-compliant event schema.  Every top-level JSON
# key produced by ``EventFactory`` maps to a ``String`` column so
# that ``JSONEachRow`` inserts work out of the box.
_COLUMNS = (
    '`@timestamp` String, '
    'agent String, '
    'ecs String, '
    'event String, '
    'host String, '
    'message String, '
    'source String, '
    'tags String, '
    '_test String'
)


def _deep_parse(value: object) -> object:
    """Try to deserialize stringified JSON values recursively."""
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    if not stripped or stripped[0] not in ('{', '['):
        return value
    try:
        parsed = json.loads(stripped)
    except (json.JSONDecodeError, ValueError):
        return value
    if isinstance(parsed, dict):
        return {k: _deep_parse(v) for k, v in parsed.items()}
    if isinstance(parsed, list):
        return [_deep_parse(item) for item in parsed]
    return parsed


def _reconstruct_event(row: dict) -> str:
    """Rebuild the original JSON string from a ClickHouse row.

    ClickHouse stores nested objects as escaped JSON strings inside
    ``String`` columns.  This function parses them back into native
    dicts/lists so that the reconstructed JSON matches what was
    originally inserted.
    """
    rebuilt = {k: _deep_parse(v) for k, v in row.items()}
    return json.dumps(rebuilt, sort_keys=True)


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
            f'({_COLUMNS}) '
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
        """Return all rows as reconstructed JSON strings.

        ClickHouse stores nested objects as escaped JSON inside
        ``String`` columns.  Each row is read back with column names
        and then reconstructed into the original JSON structure.

        Parameters
        ----------
        timeout : float
            Not directly used for ClickHouse queries but kept
            for interface consistency.

        Returns
        -------
        list[str]
            List of JSON event strings.

        """
        assert self._client is not None

        result = await asyncio.to_thread(
            self._client.query,
            f'SELECT * FROM {DATABASE}.{self._table_name} '
            f'ORDER BY _part, _part_offset',
        )

        columns = result.column_names
        events: list[str] = []
        for row in result.result_rows:
            row_dict = dict(zip(columns, row))
            events.append(_reconstruct_event(row_dict))

        return events

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
