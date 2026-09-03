import asyncio
import io
import json
import time
import threading
import uuid
from datetime import UTC, datetime, timedelta

import obstore
import pyarrow.parquet as pq
import pytest
from obstore.exceptions import GenericError, NotFoundError
import obstore.store
from obstore.store import MemoryStore, S3Store

from eventum.plugins.exceptions import PluginConfigurationError
from eventum.plugins.output.base.plugin import OutputPluginParams
from eventum.plugins.output.exceptions import PluginOpenError, PluginWriteError
from eventum.plugins.output.plugins.s3.config import S3OutputPluginConfig
from eventum.plugins.output.plugins.s3.plugin import S3OutputPlugin
from eventum.utils import net_accounting

PARAMS: OutputPluginParams = {'id': 1}

EVENTS = [
    json.dumps({'@timestamp': '2026-03-04T05:06:07Z', 'n': i, 'host': 'h'})
    for i in range(3)
]


def build(**kwargs) -> S3OutputPlugin:
    config = S3OutputPluginConfig.model_validate({'bucket': 'lake', **kwargs})
    return S3OutputPlugin(config=config, params=PARAMS)


@pytest.fixture
def store_kwargs() -> dict:
    """Keyword arguments the plugin built its store with."""
    return {}


@pytest.fixture
def opened(monkeypatch, store_kwargs):
    """Return a factory opening a plugin against the provided store."""

    async def factory(store, *, params=None, **kwargs) -> S3OutputPlugin:
        config = S3OutputPluginConfig.model_validate(
            {'bucket': 'lake', **kwargs},
        )
        instance = S3OutputPlugin(config=config, params=params or PARAMS)

        def build(**built):
            store_kwargs.update(built)
            return store

        monkeypatch.setattr(obstore.store, 'S3Store', build)
        await instance.open()
        return instance

    return factory


def keys(store) -> list[str]:
    return [meta['path'] for page in obstore.list(store) for meta in page]


async def body_of(store, key: str) -> bytes:
    result = await obstore.get_async(store, key)
    return bytes(await result.bytes_async())


class TestWriting:
    async def test_batch_becomes_one_object(self, opened):
        store = MemoryStore()
        instance = await opened(store)

        await instance.write(EVENTS)

        assert len(keys(store)) == 1

    async def test_every_event_is_counted_as_written(self, opened):
        instance = await opened(MemoryStore())

        assert await instance.write(EVENTS) == len(EVENTS)

    async def test_object_holds_every_event(self, opened):
        store = MemoryStore()
        instance = await opened(store)

        await instance.write(EVENTS)
        body = await body_of(store, keys(store)[0])

        assert len(body.decode().splitlines()) == len(EVENTS)

    async def test_each_batch_becomes_its_own_object(self, opened):
        store = MemoryStore()
        instance = await opened(store)

        await instance.write(EVENTS)
        await instance.write(EVENTS)

        assert len(keys(store)) == 2

    async def test_objects_of_one_run_do_not_overwrite_each_other(
        self, opened
    ):
        store = MemoryStore()
        instance = await opened(store)

        await instance.write(EVENTS)
        await instance.write(EVENTS)

        assert len(set(keys(store))) == 2

    async def test_written_counter_accumulates(self, opened):
        instance = await opened(MemoryStore())

        await instance.write(EVENTS)
        await instance.write(EVENTS)

        assert instance.written == 2 * len(EVENTS)

    async def test_empty_batch_writes_nothing(self, opened):
        store = MemoryStore()
        instance = await opened(store)

        assert await instance.write([]) == 0
        assert keys(store) == []

    async def test_write_before_open_is_rejected(self):
        instance = build()

        with pytest.raises(PluginWriteError, match='not opened'):
            await instance.write(EVENTS)

    async def test_close_leaves_nothing_pending(self, opened):
        store = MemoryStore()
        instance = await opened(store)

        await instance.write(EVENTS)
        await instance.close()

        assert len(keys(store)) == 1


class TestObjectKeys:
    async def test_key_follows_the_template(self, opened):
        store = MemoryStore()
        instance = await opened(store, key_template='events/{seq}{ext}')

        await instance.write(EVENTS)

        assert keys(store) == ['events/0.jsonl']

    async def test_sequence_grows_per_object(self, opened):
        store = MemoryStore()
        instance = await opened(store, key_template='{seq}{ext}')

        await instance.write(EVENTS)
        await instance.write(EVENTS)

        assert sorted(keys(store)) == ['0.jsonl', '1.jsonl']

    async def test_extension_follows_compression(self, opened):
        store = MemoryStore()
        instance = await opened(
            store,
            key_template='{seq}{ext}',
            encoder={'encoding': 'jsonl', 'compression': 'gzip'},
        )

        await instance.write(EVENTS)

        assert keys(store) == ['0.jsonl.gz']

    async def test_extension_follows_encoding(self, opened):
        store = MemoryStore()
        instance = await opened(
            store,
            key_template='{seq}{ext}',
            encoder={'encoding': 'parquet'},
        )

        await instance.write(EVENTS)

        assert keys(store) == ['0.parquet']

    async def test_partitioning_fields_are_utc(self, opened):
        store = MemoryStore()
        instance = await opened(
            store,
            key_template='{year}/{month}/{day}/{hour}{ext}',
        )

        before = datetime.now(tz=UTC)
        await instance.write(EVENTS)
        after = datetime.now(tz=UTC)

        rendered = keys(store)[0].removesuffix('.jsonl')
        expected = {
            moment.strftime('%Y/%m/%d/%H') for moment in (before, after)
        }

        assert rendered in expected

    async def test_partitioning_fields_are_not_local_time(
        self,
        opened,
        monkeypatch,
    ):
        monkeypatch.setenv('TZ', 'Asia/Tokyo')
        time.tzset()
        store = MemoryStore()
        instance = await opened(store, key_template='{hour}{ext}')
        try:
            await instance.write(EVENTS)
        finally:
            monkeypatch.delenv('TZ')
            time.tzset()

        expected = datetime.now(tz=UTC).strftime('%H')

        assert keys(store)[0] == f'{expected}.jsonl'

    async def test_key_is_partitioned_by_time_by_default(self, opened):
        store = MemoryStore()
        instance = await opened(store)

        await instance.write(EVENTS)

        assert keys(store)[0].startswith('year=')


class TestEncodings:
    async def test_json_lines_object_is_line_delimited(self, opened):
        store = MemoryStore()
        instance = await opened(store)

        await instance.write(EVENTS)
        body = await body_of(store, keys(store)[0])

        assert [json.loads(line) for line in body.decode().splitlines()] == [
            json.loads(event) for event in EVENTS
        ]

    async def test_parquet_object_is_readable(self, opened):
        store = MemoryStore()
        instance = await opened(store, encoder={'encoding': 'parquet'})

        await instance.write(EVENTS)
        body = await body_of(store, keys(store)[0])

        assert pq.read_table(io.BytesIO(body)).num_rows == len(EVENTS)

    async def test_parquet_schema_comes_from_the_configured_file(
        self,
        opened,
        tmp_path,
    ):
        schema_path = tmp_path / 'event.json'
        schema_path.write_text(json.dumps({'n': 1, 'absent': 'x'}))
        store = MemoryStore()
        instance = await opened(
            store,
            encoder={'encoding': 'parquet', 'schema_path': str(schema_path)},
        )

        await instance.write([json.dumps({'n': 2})])
        body = await body_of(store, keys(store)[0])

        assert pq.read_schema(io.BytesIO(body)).names == ['n', 'absent']

    async def test_each_object_carries_the_schema_of_its_own_events(
        self,
        opened,
    ):
        store = MemoryStore()
        instance = await opened(
            store,
            key_template='{seq}{ext}',
            encoder={'encoding': 'parquet'},
        )

        await instance.write([json.dumps({'n': 1})])
        await instance.write([json.dumps({'n': 2, 'late': 'x'})])

        schemas = [
            pq.read_schema(io.BytesIO(await body_of(store, key))).names
            for key in sorted(keys(store))
        ]

        assert schemas == [['n'], ['n', 'late']]

    async def test_declared_schema_holds_across_batches(
        self,
        opened,
        tmp_path,
    ):
        schema_path = tmp_path / 'event.json'
        schema_path.write_text(json.dumps({'n': 1}))
        store = MemoryStore()
        instance = await opened(
            store,
            key_template='{seq}{ext}',
            encoder={'encoding': 'parquet', 'schema_path': str(schema_path)},
        )

        await instance.write([json.dumps({'n': 1})])
        await instance.write([json.dumps({'n': 2, 'late': 'x'})])

        schemas = [
            pq.read_schema(io.BytesIO(await body_of(store, key))).names
            for key in sorted(keys(store))
        ]

        assert schemas == [['n'], ['n']]

    async def test_json_lines_needs_no_schema(self, opened):
        store = MemoryStore()
        instance = await opened(store)

        await instance.write([json.dumps({'n': 1})])
        await instance.write([json.dumps({'other': 'x'})])

        assert len(keys(store)) == 2

    async def test_event_conflicting_within_a_batch_fails_the_write(
        self, opened
    ):
        instance = await opened(MemoryStore(), encoder={'encoding': 'parquet'})
        events = [json.dumps({'n': 1}), json.dumps({'n': 'text'})]

        with pytest.raises(PluginWriteError, match='Failed to encode'):
            await instance.write(events)

    async def test_event_conflicting_with_the_schema_fails_the_write(
        self,
        opened,
        tmp_path,
    ):
        schema_path = tmp_path / 'event.json'
        schema_path.write_text(json.dumps({'n': 1}))
        instance = await opened(
            MemoryStore(),
            encoder={'encoding': 'parquet', 'schema_path': str(schema_path)},
        )

        with pytest.raises(PluginWriteError, match='Failed to encode'):
            await instance.write([json.dumps({'n': 1.5})])

    async def test_conflict_with_the_schema_names_the_schema_file(
        self,
        opened,
        tmp_path,
    ):
        """A declared schema is the usual cause, so the error points at
        the file to fix."""
        schema_path = tmp_path / 'event.json'
        schema_path.write_text(json.dumps({'n': 1}))
        instance = await opened(
            MemoryStore(),
            encoder={'encoding': 'parquet', 'schema_path': str(schema_path)},
        )

        with pytest.raises(PluginWriteError) as info:
            await instance.write([json.dumps({'n': 1.5})])

        assert info.value.context['file_path'] == str(schema_path)

    async def test_inferred_schema_conflict_names_no_file(self, opened):
        instance = await opened(MemoryStore(), encoder={'encoding': 'parquet'})
        events = [json.dumps({'n': 1}), json.dumps({'n': 'text'})]

        with pytest.raises(PluginWriteError) as info:
            await instance.write(events)

        assert 'file_path' not in info.value.context

    async def test_failed_encoding_writes_no_object(self, opened):
        store = MemoryStore()
        instance = await opened(store, encoder={'encoding': 'parquet'})
        events = [json.dumps({'n': 1}), json.dumps({'n': 'text'})]

        with pytest.raises(PluginWriteError):
            await instance.write(events)

        assert keys(store) == []

    async def test_failed_encoding_counts_events_as_failed(self, opened):
        instance = await opened(MemoryStore(), encoder={'encoding': 'parquet'})
        events = [json.dumps({'n': 1}), json.dumps({'n': 'text'})]

        with pytest.raises(PluginWriteError):
            await instance.write(events)

        assert instance.write_failed == len(events)


class TestOpening:
    def test_missing_schema_file_fails_configuration(self, tmp_path):
        """A typo in the path is caught when a generator is validated,
        not when it starts."""
        with pytest.raises(
            PluginConfigurationError,
            match='Failed to read schema',
        ):
            build(
                encoder={
                    'encoding': 'parquet',
                    'schema_path': str(tmp_path / 'absent.json'),
                },
            )

    def test_broken_schema_file_fails_configuration(self, tmp_path):
        schema_path = tmp_path / 'event.json'
        schema_path.write_text('[1, 2, 3]')

        with pytest.raises(
            PluginConfigurationError,
            match='Failed to infer schema',
        ):
            build(
                encoder={
                    'encoding': 'parquet',
                    'schema_path': str(schema_path),
                },
            )

    def test_missing_ca_certificate_fails_configuration(self, tmp_path):
        with pytest.raises(
            PluginConfigurationError,
            match='CA certificate',
        ):
            build(ca_cert=str(tmp_path / 'absent.pem'))

    def test_huge_schema_file_is_read(self, tmp_path):
        """The record reader refuses a record straddling two blocks."""
        schema_path = tmp_path / 'event.json'
        schema_path.write_text(json.dumps({'msg': 'x' * 3_000_000}))

        instance = build(
            encoder={
                'encoding': 'parquet',
                'schema_path': str(schema_path),
            },
        )

        assert instance._schema.names == ['msg']

    async def test_schema_file_is_resolved_against_the_base_path(
        self,
        opened,
        tmp_path,
    ):
        (tmp_path / 'schema').mkdir()
        (tmp_path / 'schema' / 'event.json').write_text(json.dumps({'n': 1}))
        store = MemoryStore()
        instance = await opened(
            store,
            params={**PARAMS, 'base_path': tmp_path},
            encoder={
                'encoding': 'parquet',
                'schema_path': 'schema/event.json',
            },
        )

        await instance.write([json.dumps({'n': 2})])

        assert len(keys(store)) == 1


class TestStoreWiring:
    async def test_computed_config_reaches_the_client(
        self,
        opened,
        store_kwargs,
    ):
        instance = await opened(
            MemoryStore(),
            endpoint_url='http://127.0.0.1:9000',
            region='eu-west-1',
        )

        assert store_kwargs['config'] == instance._build_store_config()
        assert store_kwargs['client_options'] == (
            instance._build_client_config()
        )

    async def test_retries_reach_the_client(self, opened, store_kwargs):
        await opened(MemoryStore(), max_retries=7)

        assert store_kwargs['retry_config'] == {'max_retries': 7}

    async def test_client_failure_fails_opening(self, monkeypatch):
        instance = build()

        def failing(**_kwargs):
            msg = 'unknown configuration key'
            raise GenericError(msg)

        monkeypatch.setattr(obstore.store, 'S3Store', failing)

        with pytest.raises(PluginOpenError, match='Failed to initialize'):
            await instance.open()

    async def test_content_type_is_set_on_the_object(self, opened):
        store = MemoryStore()
        instance = await opened(store)

        await instance.write(EVENTS)
        result = await obstore.get_async(store, keys(store)[0])

        assert result.attributes['Content-Type'] == 'application/x-ndjson'

    async def test_parquet_content_type_is_set_on_the_object(self, opened):
        store = MemoryStore()
        instance = await opened(store, encoder={'encoding': 'parquet'})

        await instance.write(EVENTS)
        result = await obstore.get_async(store, keys(store)[0])

        assert result.attributes['Content-Type'] == (
            'application/vnd.apache.parquet'
        )

    async def test_configured_content_type_overrides_the_encoding(
        self,
        opened,
    ):
        store = MemoryStore()
        instance = await opened(store, content_type='application/json')

        await instance.write(EVENTS)
        result = await obstore.get_async(store, keys(store)[0])

        assert result.attributes['Content-Type'] == 'application/json'


class TestStoreConfiguration:
    def test_relative_ca_certificate_is_resolved_against_the_base_path(
        self,
        tmp_path,
    ):
        (tmp_path / 'certs').mkdir()
        ca_path = tmp_path / 'certs' / 'ca.pem'
        ca_path.write_bytes(b'-----BEGIN CERTIFICATE-----\n')
        config = S3OutputPluginConfig.model_validate(
            {'bucket': 'lake', 'ca_cert': 'certs/ca.pem'},
        )
        instance = S3OutputPlugin(
            config=config,
            params={**PARAMS, 'base_path': tmp_path},
        )

        built = instance._build_client_config()

        assert built['root_certificate'] == ca_path.read_bytes()

    def test_bucket_and_region_are_passed(self):
        instance = build(region='eu-west-1')
        config = instance._build_store_config()

        assert config['bucket'] == 'lake'
        assert config['region'] == 'eu-west-1'

    def test_endpoint_trailing_slash_is_stripped(self):
        instance = build(endpoint_url='http://127.0.0.1:9000/')

        assert (
            instance._build_store_config()['endpoint']
            == 'http://127.0.0.1:9000'
        )

    def test_no_endpoint_is_passed_for_aws(self):
        assert 'endpoint' not in build()._build_store_config()

    def test_auto_addressing_is_virtual_for_aws(self):
        config = build()._build_store_config()

        assert config['virtual_hosted_style_request'] is True

    def test_auto_addressing_is_path_for_custom_endpoint(self):
        config = build(
            endpoint_url='http://127.0.0.1:9000',
        )._build_store_config()

        assert config['virtual_hosted_style_request'] is False

    def test_path_addressing_is_forced(self):
        config = build(addressing_style='path')._build_store_config()

        assert config['virtual_hosted_style_request'] is False

    def test_virtual_addressing_is_forced_for_custom_endpoint(self):
        config = build(
            endpoint_url='http://127.0.0.1:9000',
            addressing_style='virtual',
        )._build_store_config()

        assert config['virtual_hosted_style_request'] is True

    def test_credentials_are_omitted_when_not_configured(self):
        config = build()._build_store_config()

        assert 'access_key_id' not in config
        assert 'secret_access_key' not in config
        assert 'session_token' not in config

    def test_credentials_are_passed_when_configured(self):
        config = build(
            access_key_id='k',
            secret_access_key='s',  # noqa: S106
        )._build_store_config()

        assert config['access_key_id'] == 'k'
        assert config['secret_access_key'] == 's'

    def test_store_config_is_accepted_by_the_client(self):
        instance = build(
            endpoint_url='http://127.0.0.1:9000',
            access_key_id='k',
            secret_access_key='s',  # noqa: S106
        )

        store = S3Store(
            config=instance._build_store_config(),
            client_options=instance._build_client_config(),
            retry_config={'max_retries': 1},
        )

        assert store.config['bucket'] == 'lake'


class TestClientConfiguration:
    def test_timeouts_are_passed(self):
        config = build(
            connect_timeout=5,
            request_timeout=60,
        )._build_client_config()

        assert config['connect_timeout'] == timedelta(seconds=5)
        assert config['timeout'] == timedelta(seconds=60)

    def test_plain_http_endpoint_is_allowed(self):
        config = build(
            endpoint_url='http://127.0.0.1:9000',
        )._build_client_config()

        assert config['allow_http'] is True

    def test_plain_http_is_not_allowed_for_https_endpoint(self):
        config = build(
            endpoint_url='https://s3.example.com',
        )._build_client_config()

        assert config['allow_http'] is False

    def test_plain_http_is_not_allowed_for_aws(self):
        assert build()._build_client_config()['allow_http'] is False

    def test_verification_is_on_by_default(self):
        config = build()._build_client_config()

        assert config['allow_invalid_certificates'] is False

    def test_verification_can_be_turned_off(self):
        config = build(verify=False)._build_client_config()

        assert config['allow_invalid_certificates'] is True

    def test_ca_certificate_is_passed_as_content(self, tmp_path):
        ca_path = tmp_path / 'ca.pem'
        ca_path.write_bytes(b'-----BEGIN CERTIFICATE-----\n')

        config = build(ca_cert=str(ca_path))._build_client_config()

        assert config['root_certificate'] == ca_path.read_bytes()

    def test_no_ca_certificate_is_passed_when_not_configured(self):
        assert 'root_certificate' not in build()._build_client_config()

    def test_proxy_is_passed(self):
        config = build(
            proxy_url='http://proxy.example.com:3128',
        )._build_client_config()

        assert config['proxy_url'].startswith('http://proxy.example.com')


class TestWriteFailures:
    async def test_unparseable_key_is_translated(self, opened, monkeypatch):
        """The client rejects a key it cannot parse with a ValueError."""
        instance = await opened(MemoryStore())

        async def failing(*_args, **_kwargs):
            msg = 'Could not parse path'
            raise ValueError(msg)

        monkeypatch.setattr(obstore, 'put_async', failing)

        with pytest.raises(PluginWriteError, match='Failed to write'):
            await instance.write(EVENTS)

    async def test_store_failure_is_translated(self, opened, monkeypatch):
        instance = await opened(MemoryStore())

        async def failing(*_args, **_kwargs):
            msg = 'endpoint is unreachable'
            raise GenericError(msg)

        monkeypatch.setattr(obstore, 'put_async', failing)

        with pytest.raises(PluginWriteError, match='Failed to write'):
            await instance.write(EVENTS)

    async def test_missing_bucket_is_translated(self, opened, monkeypatch):
        """A 404 arrives as a builtin OS error, not as a store error."""
        instance = await opened(MemoryStore())

        async def failing(*_args, **_kwargs):
            msg = 'Object at location k not found'
            raise FileNotFoundError(msg)

        monkeypatch.setattr(obstore, 'put_async', failing)

        with pytest.raises(PluginWriteError, match='Failed to write'):
            await instance.write(EVENTS)

    async def test_missing_bucket_counts_events_as_failed(
        self,
        opened,
        monkeypatch,
    ):
        instance = await opened(MemoryStore())

        async def failing(*_args, **_kwargs):
            msg = 'Object at location k not found'
            raise FileNotFoundError(msg)

        monkeypatch.setattr(obstore, 'put_async', failing)

        with pytest.raises(PluginWriteError):
            await instance.write(EVENTS)

        assert instance.write_failed == len(EVENTS)

    async def test_store_failure_reports_the_key(self, opened, monkeypatch):
        instance = await opened(MemoryStore(), key_template='{seq}{ext}')

        async def failing(*_args, **_kwargs):
            msg = 'bucket does not exist'
            raise NotFoundError(msg)

        monkeypatch.setattr(obstore, 'put_async', failing)

        with pytest.raises(PluginWriteError) as info:
            await instance.write(EVENTS)

        assert info.value.context['object_key'] == '0.jsonl'
        assert info.value.context['bucket'] == 'lake'

    async def test_store_failure_counts_events_as_failed(
        self,
        opened,
        monkeypatch,
    ):
        instance = await opened(MemoryStore())

        async def failing(*_args, **_kwargs):
            msg = 'endpoint is unreachable'
            raise GenericError(msg)

        monkeypatch.setattr(obstore, 'put_async', failing)

        with pytest.raises(PluginWriteError):
            await instance.write(EVENTS)

        assert instance.write_failed == len(EVENTS)


class TestNetworkAccounting:
    """The store moves its bytes outside python sockets, so the plugin
    reports them itself. Writes run in a thread of their own, since the
    counters of a thread are keyed by the name it carries."""

    @staticmethod
    def _sent_by(action) -> int:
        """Run an async action in a named thread and return the bytes
        the accounting attributed to it."""
        net_accounting.install()
        name = f'accounting-{uuid.uuid4().hex}'
        outcome: list[BaseException] = []

        def target() -> None:
            try:
                asyncio.run(action())
            except BaseException as e:  # noqa: BLE001
                outcome.append(e)

        thread = threading.Thread(target=target, name=name)
        thread.start()
        thread.join()

        if outcome:
            raise outcome[0]

        return net_accounting.usage_of(lambda n: n == name).sent_bytes

    def test_written_bytes_are_reported(self, opened):
        async def action() -> None:
            instance = await opened(MemoryStore())
            await instance.write(EVENTS)

        assert self._sent_by(action) > 0

    def test_reported_bytes_match_the_object_size(self, opened):
        sizes: list[int] = []

        async def action() -> None:
            store = MemoryStore()
            instance = await opened(store)
            await instance.write(EVENTS)
            sizes.append(len(await body_of(store, keys(store)[0])))

        assert self._sent_by(action) == sizes[0]

    def test_compressed_object_reports_its_compressed_size(self, opened):
        sizes: list[int] = []

        async def action() -> None:
            store = MemoryStore()
            instance = await opened(
                store,
                encoder={'encoding': 'jsonl', 'compression': 'gzip'},
            )
            await instance.write(EVENTS)
            sizes.append(len(await body_of(store, keys(store)[0])))

        reported = self._sent_by(action)

        assert reported == sizes[0]
        assert reported < len(''.join(EVENTS))

    def test_failed_write_reports_nothing(self, opened, monkeypatch):
        async def action() -> None:
            instance = await opened(MemoryStore())

            async def failing(*_args, **_kwargs):
                msg = 'endpoint is unreachable'
                raise GenericError(msg)

            monkeypatch.setattr(obstore, 'put_async', failing)

            with pytest.raises(PluginWriteError):
                await instance.write(EVENTS)

        assert self._sent_by(action) == 0
