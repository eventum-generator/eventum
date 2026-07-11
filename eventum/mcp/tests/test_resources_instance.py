"""Tests for the instance resources and settings scrubbing."""

import json
from pathlib import Path
from typing import Any

from eventum.app.models.instance import InstanceInfo
from eventum.app.models.parameters.log import LogParameters
from eventum.app.models.parameters.path import PathParameters
from eventum.app.models.parameters.server import (
    AuthParameters,
    ServerParameters,
    SSLParameters,
)
from eventum.app.models.settings import Settings
from eventum.core.parameters import GenerationParameters
from eventum.mcp.resources.instance import safe_settings_view


def _settings(tmp_path: Path, **server: Any) -> Settings:
    return Settings(
        server=ServerParameters(**server),
        generation=GenerationParameters(),
        log=LogParameters(),
        path=PathParameters(
            logs=tmp_path / 'logs',
            startup=tmp_path / 'startup.yml',
            generators_dir=tmp_path / 'generators',
            keyring_cryptfile=tmp_path / 'secret-keyring.cfg',
        ),
    )


def test_safe_view_redacts_auth(tmp_path: Path) -> None:
    """Auth credentials are replaced with the redaction marker."""
    settings = _settings(
        tmp_path,
        auth=AuthParameters(user='admin', password='s3cret'),  # noqa: S106
    )

    view = safe_settings_view(settings)

    assert view['server']['auth']['user'] == '[redacted]'
    assert view['server']['auth']['password'] == '[redacted]'  # noqa: S105


def test_safe_view_reduces_paths_to_basenames(tmp_path: Path) -> None:
    """Absolute path settings are reduced to their file names."""
    view = safe_settings_view(_settings(tmp_path))

    assert view['path']['logs'] == 'logs'
    assert view['path']['startup'] == 'startup.yml'
    assert view['path']['generators_dir'] == 'generators'
    assert view['path']['keyring_cryptfile'] == 'secret-keyring.cfg'


def test_safe_view_reduces_ssl_cert_paths(tmp_path: Path) -> None:
    """SSL certificate paths are reduced to their file names."""
    settings = _settings(
        tmp_path,
        ssl=SSLParameters(
            ca_cert=tmp_path / 'ca.pem',
            cert=tmp_path / 'srv.pem',
            cert_key=tmp_path / 'srv.key',
        ),
    )

    view = safe_settings_view(settings)

    assert view['server']['ssl']['ca_cert'] == 'ca.pem'
    assert view['server']['ssl']['cert'] == 'srv.pem'
    assert view['server']['ssl']['cert_key'] == 'srv.key'


def test_safe_view_leaks_no_secret_or_absolute_path(tmp_path: Path) -> None:
    """No credential value and no absolute path reach the rendered view."""
    settings = _settings(
        tmp_path,
        auth=AuthParameters(user='admin', password='s3cret'),  # noqa: S106
    )

    blob = json.dumps(safe_settings_view(settings))

    assert 's3cret' not in blob
    assert 'admin' not in blob
    assert str(tmp_path) not in blob
    assert str(tmp_path / 'logs') not in blob


def test_instance_info_constructs_from_app_model() -> None:
    """InstanceInfo is importable from app and reports the app version."""
    info = InstanceInfo()

    assert info.app_version
    assert 'app_version' in info.model_dump()
