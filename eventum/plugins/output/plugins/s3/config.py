"""Definition of s3 output plugin config."""

from abc import ABC
from enum import StrEnum
from pathlib import Path
from typing import Literal, Self, assert_never

from pydantic import (
    BaseModel,
    Field,
    HttpUrl,
    field_validator,
    model_validator,
)

from eventum.plugins.output.base.config import OutputPluginConfig
from eventum.plugins.output.fields import (
    Format,
    FormatterConfigT,
    JsonFormatterConfig,
)
from eventum.plugins.output.plugins.s3.keys import validate_key_template

HEADER_VALUE_PATTERN = r'^[^\x00-\x1f\x7f]+$'
"""Values that travel in a request header hold no control character."""

DEFAULT_KEY_TEMPLATE = (
    'year={year}/month={month}/day={day}/hour={hour}/{timestamp}-{uuid}{ext}'
)
"""Hive style time partitioning with a key unique across runs."""

MAX_GZIP_COMPRESSION_LEVEL = 9

MAX_ZSTD_COMPRESSION_LEVEL = 22


class Encoding(StrEnum):
    """Encoding of an object body."""

    JSON_LINES = 'jsonl'
    PARQUET = 'parquet'


class BaseEncoderConfig(BaseModel, ABC, frozen=True, extra='forbid'):
    """Base encoder config."""


class JsonLinesEncoderConfig(BaseEncoderConfig, frozen=True):
    """Config for encoding objects as JSON Lines.

    Attributes
    ----------
    encoding : Literal[Encoding.JSON_LINES]
        Target encoding.

    compression : Literal['none', 'gzip', 'zstd'], default='none'
        Compression applied to the whole object.

    compression_level : int | None, default=None
        Compression level, `None` to use the default level of the
        selected algorithm.

    """

    encoding: Literal[Encoding.JSON_LINES]
    compression: Literal['none', 'gzip', 'zstd'] = 'none'
    compression_level: int | None = Field(
        default=None,
        ge=1,
        le=MAX_ZSTD_COMPRESSION_LEVEL,
    )

    @model_validator(mode='after')
    def validate_compression_level(self) -> Self:  # noqa: D102
        if self.compression_level is None:
            return self

        if self.compression == 'none':
            msg = 'Compression level requires a compression algorithm'
            raise ValueError(msg)

        if (
            self.compression == 'gzip'
            and self.compression_level > MAX_GZIP_COMPRESSION_LEVEL
        ):
            msg = (
                'Compression level of gzip must be at most '
                f'{MAX_GZIP_COMPRESSION_LEVEL}'
            )
            raise ValueError(msg)

        return self


class ParquetEncoderConfig(BaseEncoderConfig, frozen=True):
    """Config for encoding objects as Parquet.

    Attributes
    ----------
    encoding : Literal[Encoding.PARQUET]
        Target encoding.

    compression : Literal['none', 'snappy', 'gzip', 'zstd', 'brotli',
    'lz4'], default='snappy'
        Compression applied to the columns inside the file.

    row_group_size : int, default=100000
        Maximum number of rows in a row group of the file.

    schema_path : Path | None, default=None
        Path to a JSON file holding one representative event, the
        schema of every object is taken from it, `None` to infer the
        schema of each object from the events it holds.

    Notes
    -----
    A declared schema is what keeps the objects of one run comparable:
    a field it does not declare is left out and a field the events lack
    becomes null, so every object carries the same columns. Inferred
    instead, an object describes only its own events, and two objects
    differ as soon as their batches differ in shape.

    """

    encoding: Literal[Encoding.PARQUET]
    compression: Literal[
        'none',
        'snappy',
        'gzip',
        'zstd',
        'brotli',
        'lz4',
    ] = 'snappy'
    row_group_size: int = Field(default=100_000, ge=1)
    schema_path: Path | None = Field(default=None)


EncoderConfigT = JsonLinesEncoderConfig | ParquetEncoderConfig

_JSON_LINES_FORMATS = frozenset({Format.PLAIN, Format.JSON, Format.TEMPLATE})

_PARQUET_FORMATS = frozenset({Format.JSON})


def supported_formats(config: EncoderConfigT) -> frozenset[Format]:
    """Get formats an encoding takes.

    Parameters
    ----------
    config : EncoderConfigT
        Encoder config.

    Returns
    -------
    frozenset[Format]
        Formats the encoding can read back, the rest produce an object
        that is not readable as the encoding promises.

    """
    match config:
        case JsonLinesEncoderConfig():
            return _JSON_LINES_FORMATS
        case ParquetEncoderConfig():
            return _PARQUET_FORMATS
        case t:
            assert_never(t)


class S3OutputPluginConfig(OutputPluginConfig, frozen=True):
    """Configuration for `s3` output plugin.

    Attributes
    ----------
    bucket : str
        Name of the bucket to write objects to.

    key_template : str, default=DEFAULT_KEY_TEMPLATE
        Template of object keys, see notes for available fields.

    endpoint_url : HttpUrl | None, default=None
        Address of the storage endpoint, `None` to use the AWS endpoint
        of the selected region.

    region : str, default='us-east-1'
        Region of the bucket.

    addressing_style : Literal['auto', 'path', 'virtual'],
    default='auto'
        Whether the bucket name goes into the path of a request or into
        its host name, `auto` picks path style for a custom endpoint and
        virtual hosted style for AWS.

    access_key_id : str | None, default=None
        Access key ID to authenticate with, `None` to resolve
        credentials from the environment.

    secret_access_key : str | None, default=None
        Secret access key to authenticate with.

    session_token : str | None, default=None
        Session token of temporary credentials.

    encoder : EncoderConfigT, default=JsonLinesEncoderConfig(...)
        Encoding of object bodies.

    content_type : str | None, default=None
        Content type to set on objects, `None` to use the content type
        of the selected encoding.

    connect_timeout : int, default=10
        Connection timeout in seconds.

    request_timeout : int, default=300
        Request timeout in seconds.

    max_retries : int, default=3
        Maximum number of retries of a failed request.

    verify : bool, default=True
        Whether to verify SSL certificate of the storage endpoint.

    ca_cert : Path | None, default=None
        Path to CA certificate.

    proxy_url : HttpUrl | None, default=None
        HTTP(S) proxy address.

    Notes
    -----
    Each batch of events becomes one object, so the size of objects
    follows the batch parameters of the generator.

    Credentials and the content type travel in request headers, so a
    control character in them is rejected here rather than breaking
    every write - a trailing line break of a value read from a file is
    the usual way one gets in.

    A write is also bounded by `generation.write_timeout` of the
    generator, so a request timeout above it is never reached and the
    upload of a large object is cancelled at that ceiling instead.

    Key templates substitute `year`, `month`, `day`, `hour`, `minute`
    and `second` of the moment the object is written at in UTC,
    `timestamp` of that moment as a whole, `seq` with the number of
    objects written before this one, `uuid` with a random value and
    `ext` with the extension of the selected encoding. To tell apart
    the objects of several generators sharing a bucket, put a
    `${params.*}` value into the template.

    By default one line JSON formatter is used for events.

    """

    bucket: str = Field(min_length=1)
    key_template: str = Field(default=DEFAULT_KEY_TEMPLATE, min_length=1)
    endpoint_url: HttpUrl | None = Field(default=None)
    region: str = Field(default='us-east-1', min_length=1)
    addressing_style: Literal['auto', 'path', 'virtual'] = 'auto'
    access_key_id: str | None = Field(
        default=None,
        min_length=1,
        pattern=HEADER_VALUE_PATTERN,
    )
    secret_access_key: str | None = Field(
        default=None,
        min_length=1,
        pattern=HEADER_VALUE_PATTERN,
    )
    session_token: str | None = Field(
        default=None,
        min_length=1,
        pattern=HEADER_VALUE_PATTERN,
    )
    encoder: EncoderConfigT = Field(
        default_factory=lambda: JsonLinesEncoderConfig(
            encoding=Encoding.JSON_LINES,
        ),
        validate_default=True,
        discriminator='encoding',
    )
    content_type: str | None = Field(
        default=None,
        min_length=1,
        pattern=HEADER_VALUE_PATTERN,
    )
    connect_timeout: int = Field(default=10, ge=1)
    request_timeout: int = Field(default=300, ge=1)
    max_retries: int = Field(default=3, ge=0)
    verify: bool = Field(default=True)
    ca_cert: Path | None = Field(default=None)
    proxy_url: HttpUrl | None = Field(default=None)
    formatter: FormatterConfigT = Field(
        default_factory=lambda: JsonFormatterConfig(
            format=Format.JSON,
            indent=0,
        ),
        validate_default=True,
        discriminator='format',
    )

    @field_validator('key_template')
    @classmethod
    def validate_key_template(cls, v: str) -> str:  # noqa: D102
        return validate_key_template(v)

    @model_validator(mode='after')
    def validate_credentials(self) -> Self:  # noqa: D102
        if (self.access_key_id is None) != (self.secret_access_key is None):
            msg = 'Access key ID and secret access key must be provided '
            msg += 'together'
            raise ValueError(msg)

        if self.session_token is not None and self.access_key_id is None:
            msg = 'Session token requires access key ID and secret access key'
            raise ValueError(msg)

        return self

    @model_validator(mode='after')
    def validate_formatter_is_supported(self) -> Self:  # noqa: D102
        supported = supported_formats(self.encoder)

        if self.formatter.format not in supported:
            formats = ', '.join(sorted(supported))
            msg = (
                f'Encoding `{self.encoder.encoding}` takes events of '
                f'{formats} format, got `{self.formatter.format}`'
            )
            raise ValueError(msg)

        return self

    @model_validator(mode='after')
    def validate_json_lines_stay_on_single_lines(self) -> Self:  # noqa: D102
        if self.encoder.encoding != Encoding.JSON_LINES:
            return self

        formatter = self.formatter
        if isinstance(formatter, JsonFormatterConfig) and formatter.indent > 0:
            msg = (
                'JSON Lines encoding requires events on single lines, set '
                'formatter indent to 0'
            )
            raise ValueError(msg)

        return self
