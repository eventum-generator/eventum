"""Definition of authentication configs for http based outputs."""

from abc import ABC
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator


def is_header_value(value: str) -> bool:
    """Check whether a string can be sent as a header value.

    Parameters
    ----------
    value : str
        String to check.

    Returns
    -------
    bool
        Whether the string is a non empty run of visible ASCII
        characters, which is all a header value may carry.

    """
    return bool(value) and all('\x21' <= char <= '\x7e' for char in value)


class AuthType(StrEnum):
    """Type of HTTP authentication."""

    BASIC = 'basic'
    BEARER = 'bearer'
    OAUTH2_CLIENT_CREDENTIALS = 'oauth2_client_credentials'


class ClientAuthMethod(StrEnum):
    """Way client credentials are presented to a token endpoint."""

    POST = 'post'
    BASIC = 'basic'


class BaseHttpAuthConfig(BaseModel, ABC, frozen=True, extra='forbid'):
    """Base config of HTTP authentication."""


class BasicHttpAuthConfig(BaseHttpAuthConfig, frozen=True):
    """Config of HTTP basic authentication.

    Attributes
    ----------
    type : Literal[AuthType.BASIC]
        Type of authentication.

    username : str
        Username to authenticate with.

    password : str | None, default=None
        Password of the user, empty password is used when it is
        omitted.

    """

    type: Literal[AuthType.BASIC]
    username: str = Field(min_length=1)
    password: str | None = Field(default=None, min_length=1)


class BearerHttpAuthConfig(BaseHttpAuthConfig, frozen=True):
    """Config of authentication with a static bearer token.

    Attributes
    ----------
    type : Literal[AuthType.BEARER]
        Type of authentication.

    token : str
        Token sent in the `Authorization` header, of visible ASCII
        characters, as a header value can carry nothing else.

    """

    type: Literal[AuthType.BEARER]
    token: str = Field(min_length=1)

    @field_validator('token')
    @classmethod
    def validate_token(cls, v: str) -> str:  # noqa: D102
        if not is_header_value(v):
            msg = 'Token must be a run of visible ASCII characters'
            raise ValueError(msg)

        return v


class OAuth2ClientCredentialsHttpAuthConfig(BaseHttpAuthConfig, frozen=True):
    """Config of the OAuth2 client credentials grant.

    Attributes
    ----------
    type : Literal[AuthType.OAUTH2_CLIENT_CREDENTIALS]
        Type of authentication.

    token_url : HttpUrl
        URL of the token endpoint, over https: the client secret
        travels the body of the request to it.

    client_id : str
        Identifier of the client.

    client_secret : str
        Secret of the client.

    client_auth_method : ClientAuthMethod, default=ClientAuthMethod.POST
        Whether client credentials are sent in the body of the token
        request or in its `Authorization` header.

    scopes : list[str], default=[]
        Scopes requested for the token.

    audience : str | None, default=None
        Audience the token is requested for.

    resource : str | None, default=None
        Resource the token is requested for.

    extra_params : dict[str, str], default={}
        Additional form parameters of the token request.

    """

    type: Literal[AuthType.OAUTH2_CLIENT_CREDENTIALS]
    token_url: HttpUrl
    client_id: str = Field(min_length=1)
    client_secret: str = Field(min_length=1)
    client_auth_method: ClientAuthMethod = Field(
        default=ClientAuthMethod.POST,
    )
    scopes: list[str] = Field(default_factory=list)
    audience: str | None = Field(default=None, min_length=1)
    resource: str | None = Field(default=None, min_length=1)
    extra_params: dict[str, str] = Field(default_factory=dict)

    @field_validator('token_url')
    @classmethod
    def validate_token_url(cls, v: HttpUrl) -> HttpUrl:  # noqa: D102
        if v.scheme != 'https':
            msg = (
                'Token endpoint must be addressed over https, since '
                'the client secret travels the request to it'
            )
            raise ValueError(msg)

        return v


HttpAuthConfigT = (
    BasicHttpAuthConfig
    | BearerHttpAuthConfig
    | OAuth2ClientCredentialsHttpAuthConfig
)
