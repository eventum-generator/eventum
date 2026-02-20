"""Tests for app parameter models."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from eventum.app.models.parameters.log import LogParameters
from eventum.app.models.parameters.path import PathParameters
from eventum.app.models.parameters.server import (
    AuthParameters,
    ServerParameters,
    SSLParameters,
)


# --- PathParameters ---


def test_path_parameters_all_absolute_passes():
    params = PathParameters(
        logs=Path('/var/log/eventum'),
        startup=Path('/etc/eventum/startup.yml'),
        generators_dir=Path('/etc/eventum/generators'),
        keyring_cryptfile=Path('/etc/eventum/keyring.cfg'),
    )
    assert params.logs == Path('/var/log/eventum')


def test_path_parameters_relative_path_raises():
    with pytest.raises(ValidationError, match='Path must be absolute'):
        PathParameters(
            logs=Path('relative/logs'),
            startup=Path('/etc/eventum/startup.yml'),
            generators_dir=Path('/etc/eventum/generators'),
            keyring_cryptfile=Path('/etc/eventum/keyring.cfg'),
        )


def test_path_parameters_generator_config_filename_default():
    params = PathParameters(
        logs=Path('/var/log'),
        startup=Path('/etc/startup.yml'),
        generators_dir=Path('/etc/generators'),
        keyring_cryptfile=Path('/etc/keyring.cfg'),
    )
    assert params.generator_config_filename == Path('generator.yml')


def test_path_parameters_generator_config_filename_yml_passes():
    params = PathParameters(
        logs=Path('/var/log'),
        startup=Path('/etc/startup.yml'),
        generators_dir=Path('/etc/generators'),
        keyring_cryptfile=Path('/etc/keyring.cfg'),
        generator_config_filename=Path('config.yaml'),
    )
    assert params.generator_config_filename == Path('config.yaml')


def test_path_parameters_generator_config_filename_json_raises():
    with pytest.raises(ValidationError, match='yml'):
        PathParameters(
            logs=Path('/var/log'),
            startup=Path('/etc/startup.yml'),
            generators_dir=Path('/etc/generators'),
            keyring_cryptfile=Path('/etc/keyring.cfg'),
            generator_config_filename=Path('config.json'),
        )


def test_path_parameters_generator_config_filename_absolute_raises():
    with pytest.raises(ValidationError, match='Only filename'):
        PathParameters(
            logs=Path('/var/log'),
            startup=Path('/etc/startup.yml'),
            generators_dir=Path('/etc/generators'),
            keyring_cryptfile=Path('/etc/keyring.cfg'),
            generator_config_filename=Path('/abs/config.yml'),
        )


def test_path_parameters_generator_config_filename_nested_raises():
    with pytest.raises(ValidationError, match='Only filename'):
        PathParameters(
            logs=Path('/var/log'),
            startup=Path('/etc/startup.yml'),
            generators_dir=Path('/etc/generators'),
            keyring_cryptfile=Path('/etc/keyring.cfg'),
            generator_config_filename=Path('sub/config.yml'),
        )


# --- SSLParameters ---


def test_ssl_parameters_default_disabled():
    params = SSLParameters()
    assert params.enabled is False
    assert params.cert is None
    assert params.cert_key is None


def test_ssl_parameters_enabled_without_certs_raises():
    with pytest.raises(
        ValidationError, match='certificate and key must be provided',
    ):
        SSLParameters(enabled=True)


def test_ssl_parameters_cert_without_key_raises():
    with pytest.raises(
        ValidationError, match='provided together',
    ):
        SSLParameters(cert=Path('/etc/ssl/cert.pem'))


def test_ssl_parameters_key_without_cert_raises():
    with pytest.raises(
        ValidationError, match='provided together',
    ):
        SSLParameters(cert_key=Path('/etc/ssl/key.pem'))


def test_ssl_parameters_relative_cert_path_raises():
    with pytest.raises(ValidationError, match='Path must be absolute'):
        SSLParameters(
            cert=Path('relative/cert.pem'),
            cert_key=Path('/etc/ssl/key.pem'),
        )


def test_ssl_parameters_full_valid():
    params = SSLParameters(
        enabled=True,
        verify_mode='required',
        ca_cert=Path('/etc/ssl/ca.pem'),
        cert=Path('/etc/ssl/cert.pem'),
        cert_key=Path('/etc/ssl/key.pem'),
    )
    assert params.enabled is True
    assert params.verify_mode == 'required'


# --- AuthParameters ---


def test_auth_parameters_defaults():
    params = AuthParameters()
    assert params.user == 'eventum'
    assert params.password == 'eventum'


def test_auth_parameters_empty_user_raises():
    with pytest.raises(ValidationError):
        AuthParameters(user='')


def test_auth_parameters_empty_password_raises():
    with pytest.raises(ValidationError):
        AuthParameters(password='')


# --- ServerParameters ---


def test_server_parameters_defaults():
    params = ServerParameters()
    assert params.port == 9474
    assert params.host == '0.0.0.0'
    assert params.ui_enabled is True
    assert params.api_enabled is True


def test_server_parameters_port_zero_raises():
    with pytest.raises(ValidationError):
        ServerParameters(port=0)


def test_server_parameters_port_one_passes():
    params = ServerParameters(port=1)
    assert params.port == 1


# --- LogParameters ---


def test_log_parameters_defaults():
    params = LogParameters()
    assert params.level == 'info'
    assert params.format == 'plain'
    assert params.max_bytes == 10 * 1024 * 1024
    assert params.backups == 5


def test_log_parameters_all_valid_levels():
    for level in ('debug', 'info', 'warning', 'error', 'critical'):
        params = LogParameters(level=level)
        assert params.level == level


def test_log_parameters_invalid_level_raises():
    with pytest.raises(ValidationError):
        LogParameters(level='trace')


def test_log_parameters_max_bytes_below_minimum_raises():
    with pytest.raises(ValidationError):
        LogParameters(max_bytes=1023)


def test_log_parameters_max_bytes_minimum_passes():
    params = LogParameters(max_bytes=1024)
    assert params.max_bytes == 1024


def test_log_parameters_backups_zero_raises():
    with pytest.raises(ValidationError):
        LogParameters(backups=0)


def test_log_parameters_backups_one_passes():
    params = LogParameters(backups=1)
    assert params.backups == 1
