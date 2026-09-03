"""Tests for http output plugin config."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from eventum.plugins.output.http_auth.config import (
    AuthType,
    BasicHttpAuthConfig,
    BearerHttpAuthConfig,
)
from eventum.plugins.output.plugins.http.config import (
    HttpOutputPluginConfig,
)

_DEFAULT_CONCURRENCY = 100


def test_concurrency_defaults_to_connection_pool_size() -> None:
    """Concurrency falls back to the default size of the pool."""
    config = HttpOutputPluginConfig(url='https://localhost:8080')
    assert config.concurrency == _DEFAULT_CONCURRENCY


def test_concurrency_rejects_non_positive_value() -> None:
    """Concurrency below one is rejected."""
    with pytest.raises(ValidationError):
        HttpOutputPluginConfig(url='https://localhost:8080', concurrency=0)


def test_verify_is_enabled_by_default() -> None:
    """Certificate verification is on when `verify` is omitted."""
    config = HttpOutputPluginConfig(url='https://localhost:8080')
    assert config.verify is True


def test_verify_can_be_disabled() -> None:
    """Certificate verification is off when `verify` is disabled."""
    config = HttpOutputPluginConfig(
        url='https://localhost:8080',
        verify=False,
    )
    assert config.verify is False


def test_ca_cert_accepts_path() -> None:
    """A `ca_cert` path is accepted and stored as a `Path`."""
    config = HttpOutputPluginConfig(
        url='https://localhost:8080',
        ca_cert='certs/ca.pem',
    )
    assert config.ca_cert == Path('certs/ca.pem')


def test_client_cert_pair_accepts_paths() -> None:
    """`client_cert` and `client_cert_key` paths are accepted together."""
    config = HttpOutputPluginConfig(
        url='https://localhost:8080',
        client_cert='certs/client.pem',
        client_cert_key='certs/client.key',
    )
    assert config.client_cert == Path('certs/client.pem')
    assert config.client_cert_key == Path('certs/client.key')


def test_auth_defaults_to_none() -> None:
    """A config without credentials authenticates with nothing."""
    config = HttpOutputPluginConfig(url='https://localhost:8080')
    assert config.auth is None


def test_auth_discriminates_by_type() -> None:
    """The auth section is resolved by its `type`."""
    config = HttpOutputPluginConfig(
        url='https://localhost:8080',
        auth={'type': 'bearer', 'token': 'abc'},
    )
    assert isinstance(config.auth, BearerHttpAuthConfig)


def test_basic_auth_is_accepted() -> None:
    """The basic section carries the credentials."""
    config = HttpOutputPluginConfig(
        url='https://localhost:8080',
        auth={'type': 'basic', 'username': 'user', 'password': 'pass'},
    )

    assert isinstance(config.auth, BasicHttpAuthConfig)
    assert config.auth.type is AuthType.BASIC
    assert config.auth.username == 'user'
    assert config.auth.password == 'pass'  # noqa: S105


@pytest.mark.parametrize(
    'credentials',
    [
        {'username': 'user'},
        {'password': 'pass'},
        {'username': 'user', 'password': 'pass'},
    ],
)
def test_flat_credentials_name_their_replacement(
    credentials: dict[str, str],
) -> None:
    """The removed keys fail with the section to write instead."""
    with pytest.raises(ValidationError, match='auth') as info:
        HttpOutputPluginConfig(
            url='https://localhost:8080',
            **credentials,
        )

    assert 'type: basic' in str(info.value)


@pytest.mark.parametrize(
    'header',
    ['Authorization', 'authorization', 'AUTHORIZATION'],
)
def test_authorization_header_cannot_be_combined_with_auth(
    header: str,
) -> None:
    """The auth section and a hand written header are exclusive."""
    with pytest.raises(ValidationError, match='Authorization'):
        HttpOutputPluginConfig(
            url='https://localhost:8080',
            headers={header: 'Bearer abc'},
            auth={'type': 'bearer', 'token': 'abc'},
        )


@pytest.mark.parametrize('value', [3, None, ['a']])
def test_header_value_must_be_a_string(value: object) -> None:
    """A header value that cannot be sent is refused where written."""
    with pytest.raises(ValidationError):
        HttpOutputPluginConfig(
            url='https://localhost:8080',
            headers={'X-Retry': value},
        )


def test_authorization_header_is_kept_without_auth() -> None:
    """A hand written header stays valid on its own."""
    config = HttpOutputPluginConfig(
        url='https://localhost:8080',
        headers={'Authorization': 'Bearer abc'},
    )
    assert config.headers['Authorization'] == 'Bearer abc'
