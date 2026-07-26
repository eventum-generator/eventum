"""Tests for http output plugin config."""

from pathlib import Path

from eventum.plugins.output.plugins.http.config import (
    HttpOutputPluginConfig,
)


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
