"""Tests for http authentication configs."""

import pytest
from pydantic import BaseModel, Field, ValidationError

from eventum.plugins.output.http_auth.config import (
    AuthType,
    BasicHttpAuthConfig,
    BearerHttpAuthConfig,
    ClientAuthMethod,
    HttpAuthConfigT,
    OAuth2ClientCredentialsHttpAuthConfig,
)


class _Holder(BaseModel):
    """Model discriminating the union the same way a plugin does."""

    auth: HttpAuthConfigT = Field(discriminator='type')


def test_basic_requires_username() -> None:
    """Basic authentication is meaningless without a username."""
    with pytest.raises(ValidationError):
        BasicHttpAuthConfig(type=AuthType.BASIC)  # type: ignore[call-arg]


def test_basic_accepts_username_without_password() -> None:
    """A username alone is accepted with an empty password."""
    config = BasicHttpAuthConfig(type=AuthType.BASIC, username='user')
    assert config.password is None


def test_bearer_rejects_empty_token() -> None:
    """An empty token is not a token."""
    with pytest.raises(ValidationError):
        BearerHttpAuthConfig(type=AuthType.BEARER, token='')


def test_oauth2_defaults() -> None:
    """Optional parameters of the grant default to nothing set."""
    config = OAuth2ClientCredentialsHttpAuthConfig(
        type=AuthType.OAUTH2_CLIENT_CREDENTIALS,
        token_url='https://login.example.com/token',  # type: ignore[arg-type]  # noqa: S106
        client_id='id',
        client_secret='secret',  # noqa: S106
    )

    assert config.client_auth_method is ClientAuthMethod.POST
    assert config.scopes == []
    assert config.audience is None
    assert config.resource is None
    assert config.extra_params == {}


def test_union_discriminates_by_type() -> None:
    """The variant is resolved by the `type` field."""
    holder = _Holder.model_validate(
        {'auth': {'type': 'bearer', 'token': 'abc'}},
    )
    assert isinstance(holder.auth, BearerHttpAuthConfig)


def test_variant_forbids_extra_fields() -> None:
    """A misspelled field is reported instead of ignored."""
    with pytest.raises(ValidationError):
        _Holder.model_validate(
            {'auth': {'type': 'bearer', 'token': 'abc', 'extra': 1}},
        )


@pytest.mark.parametrize(
    'token',
    ['tok en', 'tok\nen', 'token\n', 'tok\u0435n'],
)
def test_bearer_rejects_a_token_no_header_can_carry(token: str) -> None:
    """A token holding a space, a break or a non ASCII character."""
    with pytest.raises(ValidationError):
        BearerHttpAuthConfig(type=AuthType.BEARER, token=token)


def test_oauth2_requires_a_url_of_the_token_endpoint() -> None:
    """The token endpoint is named by a URL, not by any string."""
    with pytest.raises(ValidationError):
        OAuth2ClientCredentialsHttpAuthConfig(
            type=AuthType.OAUTH2_CLIENT_CREDENTIALS,
            token_url='login.example.com',  # type: ignore[arg-type]  # noqa: S106
            client_id='id',
            client_secret='secret',  # noqa: S106
        )


@pytest.mark.parametrize(
    'credentials',
    [{'client_id': ''}, {'client_secret': ''}],
)
def test_oauth2_rejects_empty_client_credentials(
    credentials: dict[str, str],
) -> None:
    """Neither half of the client credentials may be empty."""
    with pytest.raises(ValidationError):
        OAuth2ClientCredentialsHttpAuthConfig(
            type=AuthType.OAUTH2_CLIENT_CREDENTIALS,
            token_url='https://login.example.com/token',  # type: ignore[arg-type]  # noqa: S106
            **{'client_id': 'id', 'client_secret': 'secret'} | credentials,
        )


def test_variants_are_frozen() -> None:
    """A config cannot be rewritten once it is validated."""
    config = BearerHttpAuthConfig(type=AuthType.BEARER, token='abc')  # noqa: S106

    with pytest.raises(ValidationError):
        config.token = 'other'  # type: ignore[misc]  # noqa: S105
