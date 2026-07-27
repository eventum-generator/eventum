"""Tests for docs API router."""

from unittest.mock import MagicMock

import pytest
import yaml
from fastapi.testclient import TestClient

import eventum
from eventum.api.main import build_api_app
from eventum.api.routers.docs.routes import STATIC_DIR
from eventum.app.manager import GeneratorManager
from eventum.app.models.parameters.log import LogParameters
from eventum.app.models.parameters.path import PathParameters
from eventum.app.models.parameters.server import (
    AuthParameters,
    ServerParameters,
)
from eventum.app.models.settings import Settings
from eventum.core.parameters import GenerationParameters


@pytest.fixture
def build_settings(tmp_path):
    def factory(host='0.0.0.0', port=9474):  # noqa: S104
        return Settings(
            server=ServerParameters(
                auth=AuthParameters(user='admin', password='secret'),
                host=host,
                port=port,
            ),
            generation=GenerationParameters(),
            log=LogParameters(),
            path=PathParameters(
                logs=tmp_path / 'logs',
                startup=tmp_path / 'startup.yml',
                generators_dir=tmp_path / 'generators',
                keyring_cryptfile=tmp_path / 'keyring.dat',
            ),
        )

    return factory


@pytest.fixture
def hooks(tmp_path):
    return {
        'get_settings_file_path': lambda: tmp_path / 'settings.yml',
        'terminate': MagicMock(),
        'restart': MagicMock(),
    }


@pytest.fixture
def build_client(build_settings, hooks):
    def factory(host='0.0.0.0', port=9474):  # noqa: S104
        app = build_api_app(
            generator_manager=GeneratorManager(),
            settings=build_settings(host=host, port=port),
            instance_hooks=hooks,
        )
        return TestClient(app)

    return factory


# --- GET /asyncapi.yml ---


def test_get_asyncapi_spec(build_client):
    with build_client() as client:
        response = client.get('/asyncapi.yml')

    assert response.status_code == 200
    assert response.headers['content-type'].startswith('text/plain')

    schema = yaml.safe_load(response.text)
    assert schema['asyncapi'] == '3.0.0'
    assert schema['channels']


def test_get_asyncapi_spec_uses_settings_address(build_client):
    with build_client(host='127.0.0.1', port=9999) as client:
        response = client.get('/asyncapi.yml')

    schema = yaml.safe_load(response.text)
    assert schema['servers']['local']['host'] == '127.0.0.1:9999'


def test_get_asyncapi_spec_uses_package_version(build_client):
    with build_client() as client:
        response = client.get('/asyncapi.yml')

    schema = yaml.safe_load(response.text)
    assert schema['info']['version'] == eventum.__version__


def test_get_asyncapi_spec_is_isolated_per_app(build_client):
    with (
        build_client(host='10.0.0.1', port=1111) as first_client,
        build_client(host='10.0.0.2', port=2222) as second_client,
    ):
        second_schema = yaml.safe_load(
            second_client.get('/asyncapi.yml').text,
        )
        first_schema = yaml.safe_load(first_client.get('/asyncapi.yml').text)

    assert first_schema['servers']['local']['host'] == '10.0.0.1:1111'
    assert second_schema['servers']['local']['host'] == '10.0.0.2:2222'


# --- Static assets ---


def test_build_api_app_keeps_static_dir_untouched(build_client):
    before = {
        path.name: path.stat().st_mtime_ns for path in STATIC_DIR.iterdir()
    }

    build_client(host='127.0.0.1', port=9999)

    after = {
        path.name: path.stat().st_mtime_ns for path in STATIC_DIR.iterdir()
    }
    assert before == after


def test_get_asyncapi_html(build_client):
    with build_client() as client:
        response = client.get('/asyncapi')

    assert response.status_code == 200
    assert response.headers['content-type'].startswith('text/html')
