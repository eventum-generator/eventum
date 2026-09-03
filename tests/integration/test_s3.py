"""Integration tests for the S3 output plugin.

Validates data integrity, both encodings, compression, key layout and
error handling through end-to-end roundtrip testing against a real
S3 compatible storage.
"""

import io
import json

import pyarrow.parquet as pq
import pytest

from eventum.plugins.output.exceptions import PluginWriteError
from tests.integration.backends.s3 import decode_object
from tests.integration.conftest import (
    MINIO_ACCESS_KEY,
    MINIO_SECRET_KEY,
    MINIO_URL,
)
from tests.integration.event_factory import EventSize
from tests.integration.verification import EventVerifier

pytestmark = pytest.mark.integration


async def _write_and_verify(plugin, consumer, events, event_factory):
    """Write events through the plugin and verify roundtrip integrity."""
    raw = [event.raw_json for event in events]
    written = await plugin.write(raw)
    assert written == len(events), (
        f'Expected {len(events)} written, got {written}'
    )

    consumed = await consumer.consume_all()

    verifier = EventVerifier(
        expected_batch_id=event_factory.batch_id,
        expected_count=len(events),
    )
    return verifier.verify(consumed)


class TestDataIntegrity:
    """Events survive the roundtrip through object storage."""

    async def test_single_event_roundtrip(
        self,
        s3_plugin_factory,
        s3_consumer,
        event_factory,
    ):
        plugin = await s3_plugin_factory()
        events = [event_factory.create(EventSize.MEDIUM)]

        result = await _write_and_verify(
            plugin,
            s3_consumer,
            events,
            event_factory,
        )

        assert result.is_perfect, result.summary()

    async def test_batch_roundtrip(
        self,
        s3_plugin_factory,
        s3_consumer,
        event_factory,
    ):
        plugin = await s3_plugin_factory()
        events = event_factory.create_batch(100, EventSize.MEDIUM)

        result = await _write_and_verify(
            plugin,
            s3_consumer,
            events,
            event_factory,
        )

        assert result.is_perfect, result.summary()

    async def test_large_events_roundtrip(
        self,
        s3_plugin_factory,
        s3_consumer,
        event_factory,
    ):
        plugin = await s3_plugin_factory()
        events = event_factory.create_batch(10, EventSize.LARGE)

        result = await _write_and_verify(
            plugin,
            s3_consumer,
            events,
            event_factory,
        )

        assert result.is_perfect, result.summary()

    async def test_each_batch_lands_in_its_own_object(
        self,
        s3_plugin_factory,
        s3_consumer,
        event_factory,
    ):
        plugin = await s3_plugin_factory()

        await plugin.write(
            [e.raw_json for e in event_factory.create_batch(5)],
        )
        await plugin.write(
            [e.raw_json for e in event_factory.create_batch(5)],
        )

        assert len(await s3_consumer.keys()) == 2

    async def test_events_of_several_batches_are_all_kept(
        self,
        s3_plugin_factory,
        s3_consumer,
        event_factory,
    ):
        plugin = await s3_plugin_factory()
        first = event_factory.create_batch(20)
        second = event_factory.create_batch(30)

        await plugin.write([e.raw_json for e in first])
        await plugin.write([e.raw_json for e in second])

        verifier = EventVerifier(
            expected_batch_id=event_factory.batch_id,
            expected_count=len(first) + len(second),
        )
        result = verifier.verify(await s3_consumer.consume_all())

        assert result.is_perfect, result.summary()


class TestEncodings:
    """Both encodings produce objects the ecosystem reads."""

    async def test_json_lines_object_is_line_delimited(
        self,
        s3_plugin_factory,
        s3_consumer,
        event_factory,
    ):
        plugin = await s3_plugin_factory()
        events = event_factory.create_batch(10)

        await plugin.write([e.raw_json for e in events])
        key = (await s3_consumer.keys())[0]
        body = await s3_consumer.body_of(key)

        assert key.endswith('.jsonl')
        assert len(body.decode().splitlines()) == len(events)

    async def test_gzip_object_is_smaller_and_readable(
        self,
        s3_plugin_factory,
        s3_consumer,
        event_factory,
    ):
        plain_plugin = await s3_plugin_factory(
            key_template=s3_consumer.key_template('plain-{seq}{ext}'),
        )
        gzip_plugin = await s3_plugin_factory(
            key_template=s3_consumer.key_template('gzip-{seq}{ext}'),
            encoder={'encoding': 'jsonl', 'compression': 'gzip'},
        )
        events = [e.raw_json for e in event_factory.create_batch(50)]

        await plain_plugin.write(events)
        await gzip_plugin.write(events)

        plain_key = next(k for k in await s3_consumer.keys() if 'plain-' in k)
        gzip_key = next(k for k in await s3_consumer.keys() if 'gzip-' in k)
        plain_body = await s3_consumer.body_of(plain_key)
        gzip_body = await s3_consumer.body_of(gzip_key)

        assert gzip_key.endswith('.jsonl.gz')
        assert len(gzip_body) < len(plain_body)
        assert decode_object(gzip_key, gzip_body) == decode_object(
            plain_key,
            plain_body,
        )

    async def test_zstd_object_is_readable(
        self,
        s3_plugin_factory,
        s3_consumer,
        event_factory,
    ):
        plugin = await s3_plugin_factory(
            encoder={'encoding': 'jsonl', 'compression': 'zstd'},
        )
        events = event_factory.create_batch(20)

        await plugin.write([e.raw_json for e in events])
        key = (await s3_consumer.keys())[0]

        assert key.endswith('.jsonl.zst')
        assert len(decode_object(key, await s3_consumer.body_of(key))) == len(
            events
        )

    async def test_parquet_object_is_readable_by_arrow(
        self,
        s3_plugin_factory,
        s3_consumer,
        event_factory,
    ):
        plugin = await s3_plugin_factory(
            encoder={'encoding': 'parquet', 'compression': 'zstd'},
        )
        events = event_factory.create_batch(50)

        await plugin.write([e.raw_json for e in events])
        key = (await s3_consumer.keys())[0]
        table = pq.read_table(io.BytesIO(await s3_consumer.body_of(key)))

        assert key.endswith('.parquet')
        assert table.num_rows == len(events)

    async def test_parquet_object_keeps_row_groups(
        self,
        s3_plugin_factory,
        s3_consumer,
        event_factory,
    ):
        plugin = await s3_plugin_factory(
            encoder={'encoding': 'parquet', 'row_group_size': 10},
        )
        events = event_factory.create_batch(50)

        await plugin.write([e.raw_json for e in events])
        key = (await s3_consumer.keys())[0]
        body = await s3_consumer.body_of(key)

        assert pq.ParquetFile(io.BytesIO(body)).num_row_groups == 5

    async def test_parquet_object_keeps_nested_fields(
        self,
        s3_plugin_factory,
        s3_consumer,
        event_factory,
    ):
        plugin = await s3_plugin_factory(
            encoder={'encoding': 'parquet'},
        )
        events = event_factory.create_batch(10)

        await plugin.write([e.raw_json for e in events])
        key = (await s3_consumer.keys())[0]
        schema = pq.read_schema(io.BytesIO(await s3_consumer.body_of(key)))

        assert 'host' in schema.names

    async def test_parquet_smaller_than_json_lines(
        self,
        s3_plugin_factory,
        s3_consumer,
        event_factory,
    ):
        jsonl_plugin = await s3_plugin_factory(
            key_template=s3_consumer.key_template('lines-{seq}{ext}'),
        )
        parquet_plugin = await s3_plugin_factory(
            key_template=s3_consumer.key_template('columns-{seq}{ext}'),
            encoder={'encoding': 'parquet', 'compression': 'zstd'},
        )
        events = [e.raw_json for e in event_factory.create_batch(200)]

        await jsonl_plugin.write(events)
        await parquet_plugin.write(events)

        keys = await s3_consumer.keys()
        lines = await s3_consumer.body_of(
            next(k for k in keys if 'lines-' in k),
        )
        columns = await s3_consumer.body_of(
            next(k for k in keys if 'columns-' in k),
        )

        assert len(columns) < len(lines)


class TestParquetIntegrity:
    """Values survive the columnar roundtrip, not only the row count."""

    async def test_values_survive_the_roundtrip(
        self,
        s3_plugin_factory,
        s3_consumer,
        event_factory,
    ):
        plugin = await s3_plugin_factory(
            encoder={'encoding': 'parquet'},
        )
        events = event_factory.create_batch(50)
        expected = [json.loads(e.raw_json) for e in events]

        await plugin.write([e.raw_json for e in events])
        key = (await s3_consumer.keys())[0]
        rows = pq.read_table(
            io.BytesIO(await s3_consumer.body_of(key)),
        ).to_pylist()

        assert len(rows) == len(expected)
        assert [row['message'] for row in rows] == [
            event['message'] for event in expected
        ]

    async def test_test_metadata_survives_the_roundtrip(
        self,
        s3_plugin_factory,
        s3_consumer,
        event_factory,
    ):
        plugin = await s3_plugin_factory(
            encoder={'encoding': 'parquet'},
        )
        events = event_factory.create_batch(20)

        await plugin.write([e.raw_json for e in events])
        key = (await s3_consumer.keys())[0]
        rows = pq.read_table(
            io.BytesIO(await s3_consumer.body_of(key)),
        ).to_pylist()

        sequence_ids = sorted(row['_test']['sequence_id'] for row in rows)

        assert sequence_ids == sorted(
            json.loads(e.raw_json)['_test']['sequence_id'] for e in events
        )


class TestObjectKeys:
    """Keys follow the configured layout."""

    async def test_time_partitioned_layout(
        self,
        s3_plugin_factory,
        s3_consumer,
        event_factory,
    ):
        plugin = await s3_plugin_factory(
            key_template=s3_consumer.key_template(
                'year={year}/month={month}/day={day}/hour={hour}/'
                '{timestamp}-{uuid}{ext}',
            ),
        )

        await plugin.write([e.raw_json for e in event_factory.create_batch(5)])
        key = (await s3_consumer.keys())[0]

        segments = key.split('/')

        assert segments[1].startswith('year=')
        assert segments[2].startswith('month=')
        assert segments[3].startswith('day=')
        assert segments[4].startswith('hour=')

    async def test_sequence_numbers_objects_of_a_run(
        self,
        s3_plugin_factory,
        s3_consumer,
        event_factory,
    ):
        plugin = await s3_plugin_factory(
            key_template=s3_consumer.key_template('{seq:04d}{ext}'),
        )

        for _ in range(3):
            await plugin.write(
                [e.raw_json for e in event_factory.create_batch(2)],
            )

        keys = await s3_consumer.keys()

        assert [k.split('/')[-1] for k in keys] == [
            '0000.jsonl',
            '0001.jsonl',
            '0002.jsonl',
        ]


class TestSchema:
    """A declared schema pins the columns of every object."""

    async def test_declared_schema_is_applied(
        self,
        s3_plugin_factory,
        s3_consumer,
        event_factory,
        tmp_path,
    ):
        sample = event_factory.create(EventSize.SMALL)
        declared = json.loads(sample.raw_json)
        declared['declared_only'] = 'x'
        schema_path = tmp_path / 'event.json'
        schema_path.write_text(json.dumps(declared))

        plugin = await s3_plugin_factory(
            encoder={
                'encoding': 'parquet',
                'schema_path': str(schema_path),
            },
        )
        events = event_factory.create_batch(10, EventSize.SMALL)

        await plugin.write([e.raw_json for e in events])
        key = (await s3_consumer.keys())[0]
        schema = pq.read_schema(io.BytesIO(await s3_consumer.body_of(key)))

        # the field only the declared schema has proves it was used, and
        # an inferred schema would not carry it
        assert schema.names == list(declared.keys())
        assert 'declared_only' in schema.names

    async def test_declared_schema_drops_undeclared_fields(
        self,
        s3_plugin_factory,
        s3_consumer,
        event_factory,
        tmp_path,
    ):
        schema_path = tmp_path / 'event.json'
        schema_path.write_text(json.dumps({'message': 'sample'}))

        plugin = await s3_plugin_factory(
            encoder={
                'encoding': 'parquet',
                'schema_path': str(schema_path),
            },
        )

        await plugin.write(
            [e.raw_json for e in event_factory.create_batch(5)],
        )
        key = (await s3_consumer.keys())[0]
        schema = pq.read_schema(io.BytesIO(await s3_consumer.body_of(key)))

        assert schema.names == ['message']


class TestErrorHandling:
    """Failures reach the caller as write errors."""

    async def test_missing_bucket_fails_the_write(
        self,
        s3_plugin_factory,
        event_factory,
    ):
        plugin = await s3_plugin_factory(bucket='eventum-absent-bucket')

        with pytest.raises(PluginWriteError):
            await plugin.write(
                [e.raw_json for e in event_factory.create_batch(2)],
            )

    async def test_wrong_credentials_fail_the_write(
        self,
        s3_plugin_factory,
        event_factory,
    ):
        plugin = await s3_plugin_factory(
            access_key_id='wrong',
            secret_access_key='wrong-secret',
        )

        with pytest.raises(PluginWriteError):
            await plugin.write(
                [e.raw_json for e in event_factory.create_batch(2)],
            )

    async def test_unreachable_endpoint_fails_the_write(
        self,
        s3_plugin_factory,
        event_factory,
    ):
        plugin = await s3_plugin_factory(
            endpoint_url='http://127.0.0.1:1',
            connect_timeout=1,
            request_timeout=2,
            max_retries=0,
        )

        with pytest.raises(PluginWriteError):
            await plugin.write(
                [e.raw_json for e in event_factory.create_batch(2)],
            )

    async def test_failed_write_leaves_no_object(
        self,
        s3_plugin_factory,
        s3_consumer,
        event_factory,
    ):
        """A write the storage rejects leaves the bucket untouched."""
        plugin = await s3_plugin_factory(
            access_key_id='wrong',
            secret_access_key='wrong-secret',
        )

        with pytest.raises(PluginWriteError):
            await plugin.write(
                [e.raw_json for e in event_factory.create_batch(2)],
            )

        assert await s3_consumer.keys() == []

    async def test_plugin_keeps_working_after_a_failed_write(
        self,
        s3_plugin_factory,
        s3_consumer,
        event_factory,
    ):
        plugin = await s3_plugin_factory()
        good = event_factory.create_batch(5)

        broken = await s3_plugin_factory(bucket='eventum-absent-bucket')
        with pytest.raises(PluginWriteError):
            await broken.write([e.raw_json for e in good])

        written = await plugin.write([e.raw_json for e in good])

        assert written == len(good)
        assert len(await s3_consumer.keys()) == 1


class TestConnectivity:
    """The plugin reaches the storage the way it is configured."""

    async def test_path_style_addressing(
        self,
        s3_plugin_factory,
        s3_consumer,
        event_factory,
    ):
        plugin = await s3_plugin_factory(addressing_style='path')

        written = await plugin.write(
            [e.raw_json for e in event_factory.create_batch(5)],
        )

        assert written == 5
        assert len(await s3_consumer.keys()) == 1

    async def test_credentials_from_the_environment(
        self,
        s3_plugin_factory,
        s3_consumer,
        event_factory,
        monkeypatch,
    ):
        monkeypatch.setenv('AWS_ACCESS_KEY_ID', MINIO_ACCESS_KEY)
        monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', MINIO_SECRET_KEY)
        monkeypatch.setenv('AWS_ENDPOINT_URL', MINIO_URL)

        plugin = await s3_plugin_factory(
            access_key_id=None,
            secret_access_key=None,
        )

        written = await plugin.write(
            [e.raw_json for e in event_factory.create_batch(5)],
        )

        assert written == 5
        assert len(await s3_consumer.keys()) == 1
