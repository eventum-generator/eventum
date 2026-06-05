"""Server parameters."""

from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, Field, field_validator, model_validator


class SSLParameters(BaseModel, extra='forbid', frozen=True):
    """SSL parameters.

    Attributes
    ----------
    enabled : bool, default=False
        Whether to enable SSL.

    verify_mode : Literal['none', 'optional', 'required'], default=None
        Verification mode of SSL connections. The default value `None`
        is same as Literal['none'], but `None` can also be used as
        meaningful value of "not provided" when SSL is disabled.

    ca_cert: Path | None, default=None
        Absolute path to CA certificate.

    cert: Path | None, default=None
        Absolute path to server certificate.

    cert_key: Path | None, default=None
        Absolute path to server certificate key.

    """

    enabled: bool = Field(default=False, description='Whether to enable SSL')
    verify_mode: Literal['none', 'optional', 'required'] | None = Field(
        default=None,
    )
    ca_cert: Path | None = Field(default=None)
    cert: Path | None = Field(default=None)
    cert_key: Path | None = Field(default=None)

    @field_validator('ca_cert', 'cert', 'cert_key', mode='before')
    @classmethod
    def validate_absolute_paths(cls, v: Path | None) -> Path | None:  # noqa: D102
        if v is not None and not Path(v).is_absolute():
            msg = 'Path must be absolute'
            raise ValueError(msg)

        return v

    @model_validator(mode='after')
    def validate_client_cert(self) -> Self:  # noqa: D102
        if self.cert is None and self.cert_key is None:
            return self

        if self.cert is None or self.cert_key is None:
            msg = 'Server certificate and key must be provided together'
            raise ValueError(msg)

        return self

    @model_validator(mode='after')
    def validate_certificate_and_key(self) -> Self:  # noqa: D102
        if self.enabled and (self.cert is None or self.cert_key is None):
            msg = (
                'Server certificate and key must be provided '
                'when SSL is enabled'
            )
            raise ValueError(msg)

        return self


class AuthParameters(BaseModel, extra='forbid', frozen=True):
    """Authentication parameters.

    Attributes
    ----------
    user : str, default='eventum'
        User for basic auth.

    password : str, default='eventum'
        Password for basic auth.

    """

    user: str = Field(default='eventum', min_length=1)
    password: str = Field(default='eventum', min_length=1)


class MCPParameters(BaseModel, extra='forbid', frozen=True):
    """MCP server service parameters.

    Attributes
    ----------
    enabled : bool, default=False
        Whether to mount the MCP server over HTTP.

    allow_write : bool, default=False
        Whether MCP write tools are permitted over HTTP. Enabling this
        lets a connected agent write and preview generator templates,
        which execute code on the host - keep it off unless the network
        and agent are trusted.

    path : str, default='/mcp'
        Mount path for the MCP HTTP endpoint.

    allowed_hosts : list[str], default=[]
        Allowed Host header values for DNS-rebinding protection. Empty
        disables the check (suitable behind a trusted reverse proxy);
        a non-empty list enables it and rejects other Host headers.

    """

    enabled: bool = Field(default=False)
    allow_write: bool = Field(default=False)
    path: str = Field(default='/mcp', min_length=1)
    allowed_hosts: list[str] = Field(default_factory=list)

    @field_validator('path')
    @classmethod
    def validate_path(cls, v: str) -> str:  # noqa: D102
        if not v.startswith('/'):
            msg = 'Path must start with "/"'
            raise ValueError(msg)
        if len(v) > 1 and v.endswith('/'):
            msg = 'Path must not end with "/"'
            raise ValueError(msg)
        return v


class ServerParameters(BaseModel, extra='forbid', frozen=True):
    """Server parameters.

    Attributes
    ----------
    ui_enabled : bool, default = True
        Whether to enable web UI.

    api_enabled : bool, default = True
        Whether to enable REST API.

    host : str, default='0.0.0.0'
        Bind address for server process.

    port : int, default=9474
        Bind port for server process,

    ssl : SSLParameters, default=SSLParameters(...)
        SSL parameters.

    auth : AuthParameters
        Auth parameters.

    mcp : MCPParameters
        MCP service parameters.

    """

    ui_enabled: bool = Field(default=True)
    api_enabled: bool = Field(default=True)
    host: str = Field(default='0.0.0.0', min_length=1)  # noqa: S104
    port: int = Field(default=9474, ge=1)
    ssl: SSLParameters = Field(default_factory=lambda: SSLParameters())
    auth: AuthParameters = Field(default_factory=lambda: AuthParameters())
    mcp: MCPParameters = Field(default_factory=lambda: MCPParameters())
