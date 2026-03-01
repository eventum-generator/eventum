"""OpenSearch backend consumer for integration tests."""

import asyncio
import json
import uuid

import httpx

from tests.integration.backends.base import BackendConsumer


class OpenSearchConsumer(BackendConsumer):
    """Consume events from an OpenSearch index.

    Creates a unique, ephemeral index per instance so that tests
    never collide. Uses ``httpx.AsyncClient`` to match the HTTP
    approach used by the OpenSearch output plugin.
    """

    def __init__(
        self,
        base_url: str,
        *,
        username: str = '',
        password: str = '',
    ) -> None:
        self._base_url = base_url.rstrip('/')
        self._username = username
        self._password = password
        self._index_name = f'eventum_test_{uuid.uuid4().hex[:12]}'
        self._client: httpx.AsyncClient | None = None

    @property
    def index(self) -> str:
        """Name of the ephemeral test index."""
        return self._index_name

    async def setup(self) -> None:
        """Create the test index with minimal resource settings."""
        auth = (
            (self._username, self._password)
            if self._username
            else None
        )
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            auth=auth,
            verify=False,
        )

        response = await self._client.put(
            f'/{self._index_name}',
            json={
                'settings': {
                    'number_of_shards': 1,
                    'number_of_replicas': 0,
                },
            },
        )
        response.raise_for_status()

    async def teardown(self) -> None:
        """Delete the test index and close the HTTP client."""
        if self._client is None:
            return

        try:
            response = await self._client.delete(
                f'/{self._index_name}',
            )
            response.raise_for_status()
        finally:
            await self._client.aclose()
            self._client = None

    async def _refresh(self) -> None:
        """Refresh the index to make all documents searchable."""
        assert self._client is not None
        response = await self._client.post(
            f'/{self._index_name}/_refresh',
        )
        response.raise_for_status()

    async def consume_all(
        self,
        timeout: float = 10.0,
    ) -> list[str]:
        """Return all indexed documents as JSON strings.

        Refreshes the index first, then fetches documents using
        ``_search`` with a large ``size`` parameter. For result sets
        exceeding 10 000 documents, uses the scroll API.

        Parameters
        ----------
        timeout : float
            Maximum time in seconds to wait for the search request.

        Returns
        -------
        list[str]
            List of ``_source`` documents serialized as JSON strings.

        """
        assert self._client is not None
        await self._refresh()

        events: list[str] = []
        page_size = 10_000

        # Initial search with scroll
        response = await self._client.post(
            f'/{self._index_name}/_search',
            params={'scroll': f'{int(timeout)}s', 'size': page_size},
            json={'query': {'match_all': {}}},
            timeout=timeout,
        )
        response.raise_for_status()
        result = response.json()

        scroll_id: str | None = result.get('_scroll_id')
        hits = result['hits']['hits']
        events.extend(json.dumps(hit['_source']) for hit in hits)

        # Continue scrolling if there are more documents
        try:
            while len(hits) == page_size:
                assert scroll_id is not None
                response = await self._client.post(
                    '/_search/scroll',
                    json={
                        'scroll': f'{int(timeout)}s',
                        'scroll_id': scroll_id,
                    },
                    timeout=timeout,
                )
                response.raise_for_status()
                result = response.json()
                scroll_id = result.get('_scroll_id')
                hits = result['hits']['hits']
                events.extend(
                    json.dumps(hit['_source']) for hit in hits
                )
        finally:
            # Clean up scroll context
            if scroll_id is not None:
                await self._client.request(
                    'DELETE',
                    '/_search/scroll',
                    json={'scroll_id': scroll_id},
                )

        return events

    async def count(self) -> int:
        """Return the number of documents in the index.

        Refreshes the index first to ensure the count is accurate.

        Returns
        -------
        int
            Document count.

        """
        assert self._client is not None
        await self._refresh()

        response = await self._client.get(
            f'/{self._index_name}/_count',
        )
        response.raise_for_status()
        return response.json()['count']

    async def wait_for_count(
        self,
        expected: int,
        timeout: float = 30.0,
        poll_interval: float = 0.5,
    ) -> int:
        """Wait until the index has at least `expected` documents.

        Refreshes the index before each count check.

        Parameters
        ----------
        expected : int
            Minimum number of documents to wait for.
        timeout : float
            Maximum time in seconds to wait.
        poll_interval : float
            Time in seconds between successive polls.

        Returns
        -------
        int
            Actual document count when the wait finished.

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
            f'Timed out waiting for {expected} documents in '
            f'index {self._index_name} '
            f'(got {actual} after {timeout}s)'
        )
        raise TimeoutError(msg)
