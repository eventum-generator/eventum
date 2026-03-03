"""Definition of tcp output plugin config."""

from pathlib import Path
from typing import Self

from pydantic import Field, model_validator

from eventum.plugins.fields import Encoding
from eventum.plugins.output.base.config import OutputPluginConfig


class TcpOutputPluginConfig(OutputPluginConfig, frozen=True):
    r"""Configuration for `tcp` output plugin.

    Attributes
    ----------
    host : str
        Hostname or IP address to connect to.

    port : int
        TCP port number to connect to.

    encoding : Encoding, default='utf_8'
        Encoding used to encode events before sending.

    separator : str, default='\\n'
        Separator appended after each event.

    connect_timeout : int, default=10
        Connection timeout in seconds.

    ssl : bool, default=False
        Whether to use SSL/TLS for the connection.

    verify : bool, default=True
        Whether to verify the server's SSL certificate.

    ca_cert : Path | None, default=None
        Path to CA certificate for server verification.

    client_cert : Path | None, default=None
        Path to client certificate for mutual TLS.

    client_cert_key : Path | None, default=None
        Path to client certificate key for mutual TLS.

    """

    host: str = Field(min_length=1)
    port: int = Field(ge=1, le=65535)
    encoding: Encoding = Field(default='utf_8')
    separator: str = Field(default='\n')
    connect_timeout: int = Field(default=10, ge=1)
    ssl: bool = Field(default=False)
    verify: bool = Field(default=True)
    ca_cert: Path | None = Field(default=None)
    client_cert: Path | None = Field(default=None)
    client_cert_key: Path | None = Field(default=None)

    @model_validator(mode='after')
    def validate_ssl_config(self) -> Self:  # noqa: D102
        ssl_fields = [
            name
            for name, value in {
                'ca_cert': self.ca_cert,
                'client_cert': self.client_cert,
                'client_cert_key': self.client_cert_key,
            }.items()
            if value is not None
        ]

        if not self.ssl and ssl_fields:
            msg = 'Following fields require ssl to be enabled: ' + ', '.join(
                ssl_fields,
            )
            raise ValueError(msg)

        if (self.client_cert is None) != (self.client_cert_key is None):
            msg = 'Client certificate and key must be provided together'
            raise ValueError(msg)

        return self
