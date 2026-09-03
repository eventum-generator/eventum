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
from eventum.plugins.output.http_auth.config import HttpAuthConfigT

_REMOVED_CREDENTIAL_KEYS = ('username', 'password')


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

    headers: dict[str, str], default={}
        Request headers.

    auth: HttpAuthConfigT | None, default=None
        Authentication used for requests, no authentication is
        performed when it is omitted.

    connect_timeout : int, default=10
        Connection timeout in seconds.

    request_timeout : int, default=300
        Requests timeout in seconds.

    verify: bool, default=True
        Whether to verify SSL certificate of the server when
        connecting to it.

    ca_cert: Path | None, default=None
        Path to CA certificate.

    client_cert: Path | None, default=None
        Path to client certificate.

    client_cert_key: Path | None, default=None
        Path to client certificate key.

    proxy_url : HttpUrl | None, default=None
        HTTP(S) proxy address.

    concurrency : int, default=100
        Maximum number of requests performed concurrently, it also
        sets the size of the connection pool kept toward the target.
        Formatters that produce a string per event send one request
        per event, so this value bounds how much of a batch is in
        flight at a time.

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
    headers: dict[str, str] = Field(default_factory=dict)
    auth: HttpAuthConfigT | None = Field(
        default=None,
        discriminator='type',
    )
    connect_timeout: int = Field(default=10, ge=1)
    request_timeout: int = Field(default=300, ge=1)
    verify: bool = Field(default=True)
    ca_cert: Path | None = Field(default=None)
    client_cert: Path | None = Field(default=None)
    client_cert_key: Path | None = Field(default=None)
    proxy_url: HttpUrl | None = Field(default=None)
    concurrency: int = Field(default=100, ge=1)
    formatter: FormatterConfigT = Field(
        default_factory=lambda: JsonFormatterConfig(
            format=Format.JSON_BATCH,
            indent=0,
        ),
        validate_default=True,
        discriminator='format',
    )

    @model_validator(mode='before')
    @classmethod
    def _reject_flat_credentials(cls, data: Any) -> Any:
        """Name the auth section to configs still using flat keys."""
        if not isinstance(data, dict):
            return data

        if any(key in data for key in _REMOVED_CREDENTIAL_KEYS):
            msg = (
                '`username` and `password` are moved into the `auth` '
                'section; use `auth` with `type: basic` instead'
            )
            raise ValueError(msg)

        return data

    @model_validator(mode='after')
    def validate_authorization_header(self) -> Self:  # noqa: D102
        if self.auth is None:
            return self

        for header in self.headers:
            if header.lower() == 'authorization':
                msg = (
                    'The `Authorization` header cannot be set together '
                    'with `auth`; keep one of them'
                )
                raise ValueError(msg)

        return self

    @model_validator(mode='after')
    def validate_client_cert(self) -> Self:  # noqa: D102
        if self.client_cert is None and self.client_cert_key is None:
            return self

        if self.client_cert is None or self.client_cert_key is None:
            msg = 'Client certificate and key must be provided together'
            raise ValueError(msg)

        return self
