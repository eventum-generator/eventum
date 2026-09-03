"""S3 backend consumer for integration tests."""

import gzip
import io
import json
import uuid
from compression import zstd

import obstore
import pyarrow.parquet as pq
from obstore.store import S3Store

from tests.integration.backends.base import BackendConsumer


class S3Consumer(BackendConsumer):
    """Consume events from objects of an S3 compatible bucket.

    Every instance takes a key prefix of its own inside the shared test
    bucket, so tests never collide and each one cleans up only what it
    wrote. Reads go through the same client the output plugin uses, so
    objects are read back exactly as they were stored.
    """

    def __init__(
        self,
        endpoint_url: str,
        *,
        bucket: str,
        access_key_id: str,
        secret_access_key: str,
        region: str = 'us-east-1',
    ) -> None:
        """Initialize consumer.

        Parameters
        ----------
        endpoint_url : str
            Address of the storage endpoint.

        bucket : str
            Name of the bucket the objects are written to.

        access_key_id : str
            Access key ID to authenticate with.

        secret_access_key : str
            Secret access key to authenticate with.

        region : str, default='us-east-1'
            Region of the bucket.

        """
        self._bucket = bucket
        self._prefix = f'test-{uuid.uuid4().hex[:12]}'
        self._store = S3Store(
            config={
                'bucket': bucket,
                'region': region,
                'endpoint': endpoint_url.rstrip('/'),
                'access_key_id': access_key_id,
                'secret_access_key': secret_access_key,
                'virtual_hosted_style_request': False,
            },
            client_options={'allow_http': True, 'timeout': '30s'},
            retry_config={'max_retries': 3},
        )

    @property
    def bucket(self) -> str:
        """Name of the bucket the objects are written to."""
        return self._bucket

    @property
    def prefix(self) -> str:
        """Key prefix this consumer owns."""
        return self._prefix

    def key_template(self, suffix: str = '{seq}{ext}') -> str:
        """Build a key template writing under the owned prefix."""
        return f'{self._prefix}/{suffix}'

    async def setup(self) -> None:
        """Nothing to prepare, the bucket is created by the service."""

    async def teardown(self) -> None:
        """Delete every object written under the owned prefix."""
        for key in await self.keys():
            await obstore.delete_async(self._store, key)

    async def keys(self) -> list[str]:
        """Return keys of the objects written under the owned prefix."""
        return sorted(
            meta['path']
            for page in obstore.list(self._store, prefix=self._prefix)
            for meta in page
        )

    async def body_of(self, key: str) -> bytes:
        """Return the body of one object."""
        result = await obstore.get_async(self._store, key)

        return bytes(await result.bytes_async())

    async def consume_all(  # noqa: ASYNC109
        self,
        timeout: float = 10.0,  # noqa: ARG002
    ) -> list[str]:
        """Return every event stored under the owned prefix."""
        events: list[str] = []

        for key in await self.keys():
            events.extend(decode_object(key, await self.body_of(key)))

        return events

    async def count(self) -> int:
        """Return the number of events stored under the owned prefix."""
        return len(await self.consume_all())


def decode_object(key: str, body: bytes) -> list[str]:
    """Decode the events of an object by the extension of its key.

    Parameters
    ----------
    key : str
        Key of the object.

    body : bytes
        Body of the object.

    Returns
    -------
    list[str]
        Events the object holds, as JSON strings.

    """
    if key.endswith('.parquet'):
        table = pq.read_table(io.BytesIO(body))

        return [json.dumps(row, default=str) for row in table.to_pylist()]

    if key.endswith('.gz'):
        body = gzip.decompress(body)
    elif key.endswith('.zst'):
        body = zstd.decompress(body)

    return body.decode().splitlines()
