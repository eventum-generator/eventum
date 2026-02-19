"""Definition of opensearch output plugin config."""

from pathlib import Path
from typing import Self

from pydantic import Field, HttpUrl, model_validator

from eventum.plugins.output.base.config import OutputPluginConfig
from eventum.plugins.output.fields import (
    Format,
    FormatterConfigT,
    JsonFormatterConfig,
)


class OpensearchOutputPluginConfig(OutputPluginConfig, frozen=True):
    """Configuration for `opensearch` output plugin.

    Attributes
    ----------
    hosts: list[HttpUrl]
        Opensearch cluster nodes that will be used for indexing events,
        specifying more than one nodes allows for load balancing,
        nodes must be specified in format `https://<host>:<port>`.

    username: str
        Username that is used to authenticate to Opensearch for indexing
        events.

    password: str
        Password for user to authenticate.

    index: str
        Index for writing events.

    connect_timeout : int, default=10
        Connection timeout in seconds.

    request_timeout : int, default=300
        Requests timeout in seconds.

    verify: bool, default=True
        Whether to verify SSL certificate of the cluster nodes when
        connecting to them.

    ca_cert: str | None, default=None
        Path to CA certificate.

    client_cert: str | None, default=None
        Path to client certificate.

    client_cert_key: str | None, default=None
        Path to client certificate key.

    proxy_url : HttpUrl | None, default=None
        HTTP(S) proxy address.

    Notes
    -----
    By default one line JSON formatter is used for events.

    """

    hosts: list[HttpUrl] = Field(min_length=1)
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)
    index: str = Field(min_length=1)
    connect_timeout: int = Field(default=10, ge=1)
    request_timeout: int = Field(default=300, ge=1)
    verify: bool = Field(default=False)
    ca_cert: Path | None = Field(default=None, min_length=1)
    client_cert: Path | None = Field(default=None, min_length=1)
    client_cert_key: Path | None = Field(default=None, min_length=1)
    proxy_url: HttpUrl | None = Field(default=None)
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
