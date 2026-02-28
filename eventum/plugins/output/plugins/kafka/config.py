"""Definition of kafka output plugin config."""

from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from eventum.plugins.output.base.config import OutputPluginConfig
from eventum.plugins.output.fields import (
    Format,
    FormatterConfigT,
    JsonFormatterConfig,
)


class KafkaOutputPluginConfig(OutputPluginConfig, frozen=True):
    r"""Configuration for `kafka` output plugin.

    Attributes
    ----------
    bootstrap_servers : list[str]
        Kafka broker addresses in `host:port` format.

    topic : str
        Target Kafka topic.

    key : str | None, default=None
        Message key applied to all produced messages.

    encoding : str, default='utf-8'
        Encoding for converting formatted event strings and keys
        to bytes.

    client_id : str | None, default=None
        Client name passed in each request to brokers.

    metadata_max_age_ms : int, default=300000
        Period after which metadata is force-refreshed (ms).

    request_timeout_ms : int, default=40000
        Produce request timeout (ms).

    connections_max_idle_ms : int, default=540000
        Close idle connections after this time (ms).

    acks : Literal[0, 1, -1], default=1
        Number of acknowledgments the producer requires:
        `0` = fire-and-forget, `1` = leader only, `-1` = all replicas.

    compression_type : str | None, default=None
        Compression codec for all produced data.

    max_batch_size : int, default=16384
        Maximum size of buffered data per partition (bytes).

    max_request_size : int, default=1048576
        Maximum size of a produce request (bytes).

    linger_ms : int, default=0
        Artificial delay to allow batching (ms).

    retry_backoff_ms : int, default=100
        Backoff between retries on errors (ms).

    enable_idempotence : bool, default=False
        Ensure exactly one copy of each message is written.

    transactional_id : str | None, default=None
        Transactional producer identifier.

    transaction_timeout_ms : int, default=60000
        Transaction timeout (ms).

    security_protocol : str, default='PLAINTEXT'
        Protocol used to communicate with brokers.

    sasl_mechanism : str | None, default=None
        SASL authentication mechanism.

    sasl_plain_username : str | None, default=None
        Username for SASL PLAIN authentication.

    sasl_plain_password : str | None, default=None
        Password for SASL PLAIN authentication.

    sasl_kerberos_service_name : str, default='kafka'
        Kerberos service name.

    sasl_kerberos_domain_name : str | None, default=None
        Kerberos domain name.

    ssl_cafile : Path | None, default=None
        Path to CA certificate file.

    ssl_certfile : Path | None, default=None
        Path to client certificate file.

    ssl_keyfile : Path | None, default=None
        Path to client certificate key file.

    Notes
    -----
    By default one line JSON formatter is used for events.

    """

    # Connection
    bootstrap_servers: list[Annotated[str, Field(min_length=1)]] = Field(
        min_length=1,
    )
    client_id: str | None = Field(default=None, min_length=1)
    metadata_max_age_ms: int = Field(default=300000, ge=0)
    request_timeout_ms: int = Field(default=40000, ge=1)
    connections_max_idle_ms: int = Field(default=540000, ge=0)

    # Topic & Message
    topic: str = Field(min_length=1)
    key: str | None = Field(default=None, min_length=1)
    encoding: str = Field(default='utf-8', min_length=1)

    # Performance & Reliability
    acks: Literal[0, 1, -1] = Field(default=1)
    compression_type: Literal[
        'gzip', 'snappy', 'lz4', 'zstd',
    ] | None = Field(default=None)
    max_batch_size: int = Field(default=16384, ge=1)
    max_request_size: int = Field(default=1048576, ge=1)
    linger_ms: int = Field(default=0, ge=0)
    retry_backoff_ms: int = Field(default=100, ge=0)
    enable_idempotence: bool = Field(default=False)
    transactional_id: str | None = Field(default=None, min_length=1)
    transaction_timeout_ms: int = Field(default=60000, ge=1)

    # Security
    security_protocol: Literal[
        'PLAINTEXT', 'SSL', 'SASL_PLAINTEXT', 'SASL_SSL',
    ] = Field(default='PLAINTEXT')
    sasl_mechanism: Literal[
        'PLAIN', 'SCRAM-SHA-256', 'SCRAM-SHA-512',
    ] | None = Field(default=None)
    sasl_plain_username: str | None = Field(default=None, min_length=1)
    sasl_plain_password: str | None = Field(default=None, min_length=1)
    sasl_kerberos_service_name: str = Field(
        default='kafka', min_length=1,
    )
    sasl_kerberos_domain_name: str | None = Field(
        default=None, min_length=1,
    )

    # SSL/TLS
    ssl_cafile: Path | None = Field(default=None)
    ssl_certfile: Path | None = Field(default=None)
    ssl_keyfile: Path | None = Field(default=None)

    # Formatter
    formatter: FormatterConfigT = Field(
        default_factory=lambda: JsonFormatterConfig(
            format=Format.JSON,
            indent=0,
        ),
        validate_default=True,
        discriminator='format',
    )

    @model_validator(mode='after')
    def validate_ssl_cert(self) -> Self:  # noqa: D102
        if self.ssl_certfile is None and self.ssl_keyfile is None:
            return self

        if self.ssl_certfile is None or self.ssl_keyfile is None:
            msg = 'SSL certificate and key must be provided together'
            raise ValueError(msg)

        return self

    @model_validator(mode='after')
    def validate_sasl_credentials(self) -> Self:  # noqa: D102
        has_username = self.sasl_plain_username is not None
        has_password = self.sasl_plain_password is not None

        if has_username != has_password:
            msg = (
                'SASL username and password must be provided together'
            )
            raise ValueError(msg)

        return self
