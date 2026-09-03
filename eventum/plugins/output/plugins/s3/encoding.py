"""Encoding of object bodies for s3 output plugin."""

import gzip
import io
from collections.abc import Sequence
from compression import zstd
from pathlib import Path
from typing import TYPE_CHECKING, assert_never

if TYPE_CHECKING:
    import pyarrow as pa
    import pyarrow.json as pj

from eventum.plugins.output.plugins.s3.config import (
    EncoderConfigT,
    JsonLinesEncoderConfig,
    ParquetEncoderConfig,
)

_ENCODING = 'utf-8'
"""Objects are encoded as UTF-8, as JSON and Parquet both require."""

_SEPARATOR = '\n'
"""JSON Lines is delimited by line breaks, so this is not a setting."""

_COMPRESSION_EXTENSIONS = {'none': '', 'gzip': '.gz', 'zstd': '.zst'}

_MIN_BLOCK_SIZE = 1 << 20
"""Block size the record reader falls back to, matching its own default."""


def _block_size(record: bytes | str) -> int:
    """Get a reader block size that the largest record fits into.

    The reader splits its input into blocks and refuses a record that
    straddles two of them, so the block has to take the whole record.
    """
    return max(_MIN_BLOCK_SIZE, 2 * len(record))


class EncodingError(Exception):
    """Object body cannot be encoded."""


def extension_of(config: EncoderConfigT) -> str:
    """Get extension of objects of the encoding.

    Parameters
    ----------
    config : EncoderConfigT
        Encoder config.

    Returns
    -------
    str
        Extension including the leading dot.

    """
    match config:
        case JsonLinesEncoderConfig():
            suffix = _COMPRESSION_EXTENSIONS[config.compression]
            return f'.jsonl{suffix}'
        case ParquetEncoderConfig():
            return '.parquet'
        case t:
            assert_never(t)


def content_type_of(config: EncoderConfigT) -> str:
    """Get content type of objects of the encoding.

    Parameters
    ----------
    config : EncoderConfigT
        Encoder config.

    Returns
    -------
    str
        Content type.

    Notes
    -----
    Compression of JSON Lines is not reported as a content encoding,
    since a client that acts on it serves an object other than the one
    that is stored; the extension of the key carries it instead.

    """
    match config:
        case JsonLinesEncoderConfig():
            return 'application/x-ndjson'
        case ParquetEncoderConfig():
            return 'application/vnd.apache.parquet'
        case t:
            assert_never(t)


def read_schema(path: Path) -> pa.Schema:
    """Read schema of objects from a file with a sample event.

    Parameters
    ----------
    path : Path
        Path to a JSON file holding one representative event.

    Returns
    -------
    pa.Schema
        Schema inferred from the sample event.

    Raises
    ------
    OSError
        If the file cannot be read.

    EncodingError
        If the file does not hold a JSON object.

    """
    import pyarrow as pa
    import pyarrow.json as pj

    content = path.read_bytes()

    try:
        return pj.read_json(
            io.BytesIO(content),
            read_options=pj.ReadOptions(block_size=_block_size(content)),
        ).schema
    except pa.ArrowInvalid as e:
        msg = f'Sample event is not a JSON object: {e}'
        raise EncodingError(msg) from None


def encode(
    events: Sequence[str],
    config: EncoderConfigT,
    schema: pa.Schema | None = None,
) -> bytes:
    """Encode events into a body of a single object.

    Parameters
    ----------
    events : Sequence[str]
        Formatted events to encode.

    config : EncoderConfigT
        Encoder config.

    schema : pa.Schema | None, default=None
        Schema to encode the events with, `None` to infer it from the
        events, only used by encodings that have a schema.

    Returns
    -------
    bytes
        Body of the object.

    Raises
    ------
    EncodingError
        If the events cannot be encoded.

    """
    match config:
        case JsonLinesEncoderConfig():
            return _encode_json_lines(events, config)
        case ParquetEncoderConfig():
            return _encode_parquet(events, config, schema)
        case t:
            assert_never(t)


def _read_records(
    events: Sequence[str],
    parse_options: pj.ParseOptions | None = None,
) -> pa.Table:
    """Read events as JSON records into a table.

    Parameters
    ----------
    events : Sequence[str]
        Formatted events to read.

    parse_options : pj.ParseOptions | None, default=None
        Parse options to read the records with.

    Returns
    -------
    pa.Table
        Table of the records.

    Raises
    ------
    EncodingError
        If the events cannot be read as JSON records.

    Notes
    -----
    Records are handed over to arrow for parsing instead of being
    decoded into python objects first, since the columns of the table
    are built from them anyway.

    """
    import pyarrow as pa
    import pyarrow.json as pj

    try:
        records = '\n'.join(events).encode(_ENCODING)
    except UnicodeEncodeError as e:
        msg = f'Cannot encode events: {e}'
        raise EncodingError(msg) from None

    try:
        return pj.read_json(
            io.BytesIO(records),
            read_options=pj.ReadOptions(
                block_size=_block_size(max(events, key=len)),
            ),
            parse_options=parse_options,
        )
    except pa.ArrowInvalid as e:
        msg = f'Cannot read events as JSON records: {e}'
        raise EncodingError(msg) from None


def _encode_json_lines(
    events: Sequence[str],
    config: JsonLinesEncoderConfig,
) -> bytes:
    """Encode events as JSON Lines.

    Parameters
    ----------
    events : Sequence[str]
        Formatted events to encode.

    config : JsonLinesEncoderConfig
        Encoder config.

    Returns
    -------
    bytes
        Body of the object.

    Raises
    ------
    EncodingError
        If the events cannot be encoded.

    """
    try:
        body = ''.join(event + _SEPARATOR for event in events).encode(
            _ENCODING,
        )
    except UnicodeEncodeError as e:
        msg = f'Cannot encode events: {e}'
        raise EncodingError(msg) from None

    level = config.compression_level

    match config.compression:
        case 'none':
            return body
        case 'gzip':
            if level is None:
                return gzip.compress(body, mtime=0)
            return gzip.compress(body, compresslevel=level, mtime=0)
        case 'zstd':
            return zstd.compress(body, level=level)
        case t:
            assert_never(t)


def _encode_parquet(
    events: Sequence[str],
    config: ParquetEncoderConfig,
    schema: pa.Schema | None,
) -> bytes:
    """Encode events as Parquet.

    Parameters
    ----------
    events : Sequence[str]
        Formatted events to encode.

    config : ParquetEncoderConfig
        Encoder config.

    schema : pa.Schema | None
        Schema to encode the events with, `None` to infer it from the
        events.

    Returns
    -------
    bytes
        Body of the object.

    Raises
    ------
    EncodingError
        If the events cannot be encoded.

    """
    import pyarrow as pa
    import pyarrow.json as pj
    import pyarrow.parquet as pq

    if schema is None:
        parse_options = None
    else:
        # without this a field the schema does not declare is appended
        # to the columns of that object alone, so objects of one run
        # stop sharing a schema
        parse_options = pj.ParseOptions(
            explicit_schema=schema,
            unexpected_field_behavior='ignore',
        )

    table = _read_records(events, parse_options)

    body = io.BytesIO()

    try:
        pq.write_table(
            table,
            body,
            compression=config.compression,
            row_group_size=config.row_group_size,
        )
    except pa.ArrowException as e:
        msg = f'Cannot write events as Parquet: {e}'
        raise EncodingError(msg) from None

    return body.getvalue()
