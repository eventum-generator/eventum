"""Tests for instance API router."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from eventum.api.routers.instance.routes import router
from eventum.app.models.parameters.log import LogParameters
from eventum.app.models.parameters.path import PathParameters
from eventum.app.models.parameters.server import (
    AuthParameters,
    ServerParameters,
)
from eventum.app.models.settings import Settings
from eventum.core.parameters import GenerationParameters


@pytest.fixture()
def tmp_settings(tmp_path):
    return Settings(
        server=ServerParameters(
            auth=AuthParameters(user='admin', password='secret'),
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


@pytest.fixture()
def hooks(tmp_path):
    return {
        'get_settings_file_path': lambda: tmp_path / 'settings.yml',
        'terminate': MagicMock(),
        'restart': MagicMock(),
    }


@pytest.fixture()
def client(tmp_settings, hooks):
    app = FastAPI()
    app.state.settings = tmp_settings
    app.state.instance_hooks = hooks
    app.include_router(router, prefix='/instance')
    return TestClient(app)


# --- GET /info ---


def test_get_info(client):
    response = client.get('/instance/info')
    assert response.status_code == 200
    data = response.json()
    assert 'app_version' in data
    assert 'host_name' in data
    assert 'cpu_count' in data


# --- GET /settings ---


def test_get_settings(client, tmp_settings):
    response = client.get('/instance/settings')
    assert response.status_code == 200
    data = response.json()
    assert data['server']['auth']['user'] == 'admin'


# --- PUT /settings ---


def test_update_settings(client, tmp_settings, tmp_path):
    new_settings = tmp_settings.model_dump(mode='json')
    response = client.put(
        '/instance/settings',
        json=new_settings,
    )
    assert response.status_code == 200
    settings_file = tmp_path / 'settings.yml'
    assert settings_file.exists()


def test_update_settings_hook_error(client, hooks, tmp_settings):
    hooks['get_settings_file_path'] = MagicMock(
        side_effect=RuntimeError('fail')
    )
    new_settings = tmp_settings.model_dump(mode='json')
    response = client.put('/instance/settings', json=new_settings)
    assert response.status_code == 500


# --- POST /stop ---


def test_stop_instance(client, hooks):
    response = client.post('/instance/stop')
    assert response.status_code == 200
    hooks['terminate'].assert_called_once()


def test_stop_instance_error(client, hooks):
    hooks['terminate'] = MagicMock(side_effect=RuntimeError('fail'))
    response = client.post('/instance/stop')
    assert response.status_code == 500


# --- POST /restart ---


def test_restart_instance(client, hooks):
    response = client.post('/instance/restart')
    assert response.status_code == 200
    hooks['restart'].assert_called_once()


def test_restart_instance_error(client, hooks):
    hooks['restart'] = MagicMock(side_effect=RuntimeError('fail'))
    response = client.post('/instance/restart')
    assert response.status_code == 500
