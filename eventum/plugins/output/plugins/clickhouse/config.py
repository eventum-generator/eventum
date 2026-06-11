"""Definition of clickhouse output plugin config."""

from pathlib import Path
from typing import Literal, Self

from pydantic import ClickHouseDsn, Field, HttpUrl, model_validator

from eventum.plugins.output.base.config import OutputPluginConfig
from eventum.plugins.output.fields import (
    Format,
    FormatterConfigT,
    JsonFormatterConfig,
)
from eventum.plugins.output.plugins.clickhouse.fields import (
    ClickhouseInputFormat,
)


class ClickhouseOutputPluginConfig(OutputPluginConfig, frozen=True):
    r"""Configuration for `clickhouse` output plugin.

    Attributes
    ----------
    host : str
        The hostname or IP address of the ClickHouse server.

    port : int, default=8123
        The ClickHouse HTTP or HTTPS port.

    protocol : Literal['http', 'https'], default='http'
        Protocol to use to connect to ClickHouse.

    database : str, default='default'
        Database name for inserting events.

    table : str
        Table name for inserting events.

    username : str, default='default'
        Username that is used to authenticate to ClickHouse.

    password : str, default=''
        Password for user to authenticate.

    dsn : ClickHouseDsn | None, default=None
        A string in standard DSN (Data Source Name) format, other
        connection values (such as host or username) will be extracted
        from this string if not set otherwise.

    connect_timeout : int, default=10
        Connection timeout in seconds.

    request_timeout : int, default=300
        Requests timeout in seconds.

    client_name : str | None, default=None
        Client name that is prepended to the HTTP User Agent header,
        set this to track client queries in the ClickHouse query log.

    verify : bool, default=False
        Whether to verify SSL certificate of ClickHouse server.

    ca_cert : Path | None, default=None
        Path to CA certificate.

    client_cert : Path | None, default=None
        Path to client certificate.

    client_cert_key : Path | None, default=None
        Path to client certificate key.

    server_host_name : str | None, default=None
        The ClickHouse server hostname as identified by the CN or SNI
        of its TLS certificate, set this to avoid SSL errors when
        connecting through a proxy or tunnel with a different hostname.

    tls_mode : Literal['proxy', 'strict', 'mutual'] | None, default=None
        Mode of TLS behavior, `proxy` and `strict` do not invoke
        ClickHouse mutual TLS connection, but do send client cert and
        key, `mutual` assumes ClickHouse mutual TLS auth with a client
        certificate, default behavior is `mutual`.

    proxy_url : HttpUrl | None, default=None
        HTTP(S) proxy address.

    pool_maxsize : int, default=32
        Maximum number of HTTP connections kept in the underlying
        connection pool toward the ClickHouse host. Raise this value
        together with `generation.max_concurrency` to avoid the pool
        discarding connections under bursts of concurrent writes.

    input_format : ClickhouseInputFormat, default='JSONEachRow'
        ClickHouse input format for inserting, documentation:
        https://clickhouse.com/docs/en/interfaces/formats

    header : str, default=''
        Header that inserted before all events.

    footer: str, default=''
        Footer that inserted after all events.

    separator: str, default='\n'
        Separator between events.

    Notes
    -----
    To see full documentation of parameters:
    https://clickhouse.com/docs/en/integrations/python#connection-arguments

    By default one line JSON formatter is used for events.

    """

    host: str = Field(min_length=1)
    port: int = Field(default=8123, ge=1, le=65535)
    protocol: Literal['http', 'https'] = Field(default='http')
    database: str = Field(default='default', min_length=1)
    table: str = Field(min_length=1)
    username: str = Field(default='default', min_length=1)
    password: str = Field(default='')
    dsn: ClickHouseDsn | None = Field(default=None)
    connect_timeout: int = Field(default=10, ge=1)
    request_timeout: int = Field(default=300, ge=1)
    client_name: str | None = Field(default=None, min_length=1)
    verify: bool = Field(default=True)
    ca_cert: Path | None = Field(default=None, min_length=1)
    client_cert: Path | None = Field(default=None, min_length=1)
    client_cert_key: Path | None = Field(default=None, min_length=1)
    server_host_name: str | None = Field(default=None, min_length=1)
    tls_mode: Literal['proxy', 'strict', 'mutual'] | None = Field(default=None)
    proxy_url: HttpUrl | None = Field(default=None)
    pool_maxsize: int = Field(default=32, ge=1)
    input_format: ClickhouseInputFormat = Field(
        default='JSONEachRow',
        validate_default=True,
    )
    header: str = Field(default='')
    footer: str = Field(default='')
    separator: str = Field(default='\n')
    formatter: FormatterConfigT = Field(
        default_factory=lambda: JsonFormatterConfig(
            format=Format.JSON,
            indent=0,
        ),
        validate_default=True,
        discriminator='format',
    )

    @model_validator(mode='after')
    def validate_client_cert(self) -> Self:  # noqa: D102
        if self.client_cert is None and self.client_cert_key is None:
            return self

        if self.client_cert is None or self.client_cert_key is None:
            msg = 'Client certificate and key must be provided together'
            raise ValueError(msg)

        return self
