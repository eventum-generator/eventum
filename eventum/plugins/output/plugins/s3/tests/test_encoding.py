import gzip
import io
import json
from compression import zstd

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from eventum.plugins.output.plugins.s3.config import (
    Encoding,
    JsonLinesEncoderConfig,
    ParquetEncoderConfig,
)
from eventum.plugins.output.plugins.s3.encoding import (
    EncodingError,
    content_type_of,
    encode,
    extension_of,
    read_schema,
)

EVENTS = [
    json.dumps({'@timestamp': '2026-03-04T05:06:07Z', 'n': i, 'host': 'h'})
    for i in range(3)
]


def json_lines(**kwargs) -> JsonLinesEncoderConfig:
    return JsonLinesEncoderConfig(encoding=Encoding.JSON_LINES, **kwargs)


def parquet(**kwargs) -> ParquetEncoderConfig:
    return ParquetEncoderConfig(encoding=Encoding.PARQUET, **kwargs)


class TestExtension:
    def test_json_lines(self):
        assert extension_of(json_lines()) == '.jsonl'

    def test_json_lines_gzip(self):
        assert extension_of(json_lines(compression='gzip')) == '.jsonl.gz'

    def test_json_lines_zstd(self):
        assert extension_of(json_lines(compression='zstd')) == '.jsonl.zst'

    def test_parquet(self):
        assert extension_of(parquet()) == '.parquet'


class TestContentType:
    def test_json_lines(self):
        assert content_type_of(json_lines()) == 'application/x-ndjson'

    def test_compression_does_not_change_content_type(self):
        assert content_type_of(json_lines(compression='gzip')) == (
            content_type_of(json_lines())
        )

    def test_parquet(self):
        assert content_type_of(parquet()) == 'application/vnd.apache.parquet'


class TestJsonLinesEncoding:
    def test_every_event_ends_with_separator(self):
        body = encode(EVENTS, json_lines())

        assert body.decode().count('\n') == len(EVENTS)
        assert body.endswith(b'\n')

    def test_events_are_kept_intact(self):
        body = encode(EVENTS, json_lines())

        assert body.decode().splitlines() == EVENTS

    def test_custom_separator(self):
        body = encode(EVENTS, json_lines(separator='\r\n'))

        assert body.decode().split('\r\n')[:-1] == EVENTS

    def test_gzip_roundtrip(self):
        body = encode(EVENTS, json_lines(compression='gzip'))

        assert gzip.decompress(body).decode().splitlines() == EVENTS

    def test_gzip_output_carries_no_timestamp(self):
        body = encode(EVENTS, json_lines(compression='gzip'))

        assert body[4:8] == b'\x00\x00\x00\x00'

    def test_gzip_output_is_reproducible(self):
        first = encode(EVENTS, json_lines(compression='gzip'))
        second = encode(EVENTS, json_lines(compression='gzip'))

        assert first == second

    def test_gzip_level_changes_output(self):
        events = [json.dumps({'msg': 'x' * 500})] * 50
        low = encode(
            events, json_lines(compression='gzip', compression_level=1)
        )
        high = encode(
            events,
            json_lines(compression='gzip', compression_level=9),
        )

        assert len(high) < len(low)

    def test_zstd_roundtrip(self):
        body = encode(EVENTS, json_lines(compression='zstd'))

        assert zstd.decompress(body).decode().splitlines() == EVENTS

    def test_zstd_level_changes_output(self):
        events = [
            json.dumps({'msg': f'{i}-{"ab" * (i % 40)}'}) for i in range(400)
        ]
        low = encode(
            events,
            json_lines(compression='zstd', compression_level=1),
        )
        high = encode(
            events,
            json_lines(compression='zstd', compression_level=19),
        )

        assert low != high
        assert len(high) < len(low)
        assert zstd.decompress(high).decode().splitlines() == events

    def test_compression_shrinks_repetitive_events(self):
        events = [json.dumps({'msg': 'x' * 500})] * 50
        plain = encode(events, json_lines())
        compressed = encode(events, json_lines(compression='gzip'))

        assert len(compressed) < len(plain)

    def test_events_that_cannot_be_encoded_are_reported(self):
        with pytest.raises(EncodingError, match='Cannot encode events'):
            encode(['\ud800'], json_lines())

    def test_huge_event_is_encoded(self):
        body = encode([json.dumps({'msg': 'x' * 3_000_000})], json_lines())

        assert len(body.decode().splitlines()) == 1


class TestParquetEncoding:
    def test_roundtrip_keeps_every_row(self):
        body = encode(EVENTS, parquet())

        assert pq.read_table(io.BytesIO(body)).num_rows == len(EVENTS)

    def test_roundtrip_keeps_values(self):
        body = encode(EVENTS, parquet())
        rows = pq.read_table(io.BytesIO(body)).to_pylist()

        assert [row['n'] for row in rows] == [0, 1, 2]

    def test_body_is_a_parquet_file(self):
        body = encode(EVENTS, parquet())

        assert body.startswith(b'PAR1')
        assert body.endswith(b'PAR1')

    def test_nested_objects_become_a_struct(self):
        events = [json.dumps({'host': {'name': 'h1'}})]
        body = encode(events, parquet())
        schema = pq.read_schema(io.BytesIO(body))

        assert pa.types.is_struct(schema.field('host').type)

    def test_row_group_size_splits_row_groups(self):
        events = [json.dumps({'n': i}) for i in range(10)]
        body = encode(events, parquet(row_group_size=4))

        assert pq.ParquetFile(io.BytesIO(body)).num_row_groups == 3

    def test_compression_is_applied(self):
        events = [json.dumps({'msg': 'x' * 500})] * 200
        plain = encode(events, parquet(compression='none'))
        compressed = encode(events, parquet(compression='zstd'))

        assert len(compressed) < len(plain)

    def test_explicit_schema_fills_missing_fields_with_null(self):
        schema = pa.schema([('n', pa.int64()), ('absent', pa.string())])
        body = encode([json.dumps({'n': 1})], parquet(), schema)
        rows = pq.read_table(io.BytesIO(body)).to_pylist()

        assert rows == [{'n': 1, 'absent': None}]

    def test_explicit_schema_keeps_field_order_across_objects(self):
        schema = pa.schema([('a', pa.int64()), ('b', pa.int64())])
        first = encode([json.dumps({'a': 1, 'b': 2})], parquet(), schema)
        second = encode([json.dumps({'b': 4, 'a': 3})], parquet(), schema)

        assert pq.read_schema(io.BytesIO(first)).names == ['a', 'b']
        assert pq.read_schema(io.BytesIO(second)).names == ['a', 'b']

    def test_explicit_schema_drops_undeclared_fields(self):
        schema = pa.schema([('n', pa.int64())])
        body = encode([json.dumps({'n': 1, 'extra': 'x'})], parquet(), schema)

        assert pq.read_schema(io.BytesIO(body)).names == ['n']

    def test_explicit_schema_holds_across_events_of_mixed_shape(self):
        schema = pa.schema([('n', pa.int64())])
        events = [json.dumps({'n': 1}), json.dumps({'n': 2, 'extra': 'x'})]
        body = encode(events, parquet(), schema)
        table = pq.read_table(io.BytesIO(body))

        assert table.schema.names == ['n']
        assert table.to_pylist() == [{'n': 1}, {'n': 2}]

    def test_event_conflicting_with_schema_is_reported(self):
        schema = pa.schema([('n', pa.int64())])

        with pytest.raises(EncodingError, match='Cannot read events'):
            encode([json.dumps({'n': 1.5})], parquet(), schema)

    def test_event_larger_than_the_reader_block_is_encoded(self):
        events = [json.dumps({'msg': 'x' * 3_000_000})]
        body = encode(events, parquet())

        assert pq.read_table(io.BytesIO(body)).num_rows == 1

    def test_batch_mixing_a_huge_event_is_encoded(self):
        events = [
            json.dumps({'msg': 'x' * 3_000_000}),
            json.dumps({'msg': 'y'}),
        ]
        body = encode(events, parquet())

        assert pq.read_table(io.BytesIO(body)).num_rows == len(events)

    def test_write_failure_is_reported(self, monkeypatch):
        def failing(*_args, **_kwargs):
            msg = 'unsupported column type'
            raise pa.ArrowNotImplementedError(msg)

        monkeypatch.setattr(pq, 'write_table', failing)

        with pytest.raises(EncodingError, match='Cannot write events'):
            encode(EVENTS, parquet())

    def test_non_json_event_is_reported(self):
        with pytest.raises(EncodingError, match='Cannot read events'):
            encode(['not json at all'], parquet())

    def test_json_scalar_event_is_reported(self):
        with pytest.raises(EncodingError, match='Cannot read events'):
            encode(['42'], parquet())

    def test_json_array_event_is_reported(self):
        with pytest.raises(EncodingError, match='Cannot read events'):
            encode(['[{"n": 1}]'], parquet())

    def test_inferred_schema_differs_between_objects_of_different_shape(self):
        first = encode([json.dumps({'a': 1})], parquet())
        second = encode([json.dumps({'b': 1})], parquet())

        assert pq.read_schema(io.BytesIO(first)).names == ['a']
        assert pq.read_schema(io.BytesIO(second)).names == ['b']


class TestParquetEventEncoding:
    def test_event_that_cannot_be_encoded_is_reported(self):
        with pytest.raises(EncodingError, match='Cannot encode events'):
            encode(['\ud800'], parquet())


class TestReadSchema:
    def test_schema_is_inferred_from_sample_event(self, tmp_path):
        path = tmp_path / 'event.json'
        path.write_text(json.dumps({'n': 1, 'msg': 'x'}))

        schema = read_schema(path)

        assert schema.names == ['n', 'msg']
        assert pa.types.is_integer(schema.field('n').type)

    def test_nested_sample_event(self, tmp_path):
        path = tmp_path / 'event.json'
        path.write_text(json.dumps({'host': {'name': 'h'}}))

        schema = read_schema(path)

        assert pa.types.is_struct(schema.field('host').type)

    def test_pretty_printed_sample_event(self, tmp_path):
        path = tmp_path / 'event.json'
        path.write_text(json.dumps({'n': 1, 'msg': 'x'}, indent=4))

        assert read_schema(path).names == ['n', 'msg']

    def test_missing_file_raises_os_error(self, tmp_path):
        with pytest.raises(OSError, match='No such file'):
            read_schema(tmp_path / 'absent.json')

    def test_sample_that_is_not_an_object_is_reported(self, tmp_path):
        path = tmp_path / 'event.json'
        path.write_text('[1, 2, 3]')

        with pytest.raises(EncodingError, match='not a JSON object'):
            read_schema(path)

    def test_schema_from_file_is_used_for_encoding(self, tmp_path):
        path = tmp_path / 'event.json'
        path.write_text(json.dumps({'n': 1, 'absent': 'x'}))

        body = encode([json.dumps({'n': 2})], parquet(), read_schema(path))

        assert pq.read_table(io.BytesIO(body)).to_pylist() == [
            {'n': 2, 'absent': None},
        ]
