"""Definition of http output plugin config."""

from pathlib import Path
from typing import Any, Literal, Self

from pydantic import Field, HttpUrl, model_validator

from eventum.plugins.output.base.config import OutputPluginConfig
from eventum.plugins.output.fields import (
    Format,
    FormatterConfigT,
    JsonFormatterConfig,
)


class HttpOutputPluginConfig(OutputPluginConfig, frozen=True):
    """Configuration for `http` output plugin.

    Attributes
    ----------
    url : HttpUrl
        URL address of resource.

    method : Literal[\
        'GET', 'HEAD', 'OPTIONS', 'POST', 'PUT', 'PATCH', 'DELETE'\
    ], default='POST'
        HTTP method to use.

    success_code : int,default=201
        Expected HTTP response code, if server returns other code, then
        it is considered as an error.

    headers: dict[str, Any], default={}
        Request headers.

    username: str | None, default=None
        Username that is used to authenticate.

    password: str | None, default=None
        Password for user to authenticate.

    connect_timeout : int, default=10
        Connection timeout in seconds.

    request_timeout : int, default=300
        Requests timeout in seconds.

    verify: bool, default=True
        Whether to verify SSL certificate of the server when
        connecting to it.

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
    By default one line JSON batch formatter is used for events.

    """

    url: HttpUrl
    method: Literal[
        'GET',
        'HEAD',
        'OPTIONS',
        'POST',
        'PUT',
        'PATCH',
        'DELETE',
    ] = Field(default='POST')
    success_code: int = Field(default=201, ge=100)
    headers: dict[str, Any] = Field(default_factory=dict)
    username: str | None = Field(default=None, min_length=1)
    password: str | None = Field(default=None, min_length=1)
    connect_timeout: int = Field(default=10, ge=1)
    request_timeout: int = Field(default=300, ge=1)
    verify: bool = Field(default=False)
    ca_cert: Path | None = Field(default=None, min_length=1)
    client_cert: Path | None = Field(default=None, min_length=1)
    client_cert_key: Path | None = Field(default=None, min_length=1)
    proxy_url: HttpUrl | None = Field(default=None)
    formatter: FormatterConfigT = Field(
        default_factory=lambda: JsonFormatterConfig(
            format=Format.JSON_BATCH,
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
