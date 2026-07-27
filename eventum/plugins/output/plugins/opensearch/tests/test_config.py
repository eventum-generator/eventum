"""Tests for opensearch output plugin config."""

from pathlib import Path

from eventum.plugins.output.plugins.opensearch.config import (
    OpensearchOutputPluginConfig,
)


def test_verify_is_enabled_by_default() -> None:
    """Certificate verification is on when `verify` is omitted."""
    config = OpensearchOutputPluginConfig(
        hosts=['https://localhost:9200'],
        index='i',
        username='u',
        password='p',  # noqa: S106
    )
    assert config.verify is True


def test_verify_can_be_disabled() -> None:
    """Certificate verification is off when `verify` is disabled."""
    config = OpensearchOutputPluginConfig(
        hosts=['https://localhost:9200'],
        index='i',
        username='u',
        password='p',  # noqa: S106
        verify=False,
    )
    assert config.verify is False


def test_ca_cert_accepts_path() -> None:
    """A `ca_cert` path is accepted and stored as a `Path`."""
    config = OpensearchOutputPluginConfig(
        hosts=['https://localhost:9200'],
        index='i',
        username='u',
        password='p',  # noqa: S106
        ca_cert='certs/ca.pem',
    )
    assert config.ca_cert == Path('certs/ca.pem')


def test_client_cert_pair_accepts_paths() -> None:
    """`client_cert` and `client_cert_key` paths are accepted together."""
    config = OpensearchOutputPluginConfig(
        hosts=['https://localhost:9200'],
        index='i',
        username='u',
        password='p',  # noqa: S106
        client_cert='certs/client.pem',
        client_cert_key='certs/client.key',
    )
    assert config.client_cert == Path('certs/client.pem')
    assert config.client_cert_key == Path('certs/client.key')
