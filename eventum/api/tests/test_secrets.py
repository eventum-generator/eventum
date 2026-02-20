"""Tests for secrets API router."""

from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from eventum.api.routers.secrets.routes import router

app = FastAPI()
app.include_router(router, prefix='/secrets')


@pytest.fixture
def client():
    return TestClient(app)


# --- GET /{name} ---


@patch('eventum.api.routers.secrets.routes.get_secret')
def test_get_secret_success(mock_get, client):
    mock_get.return_value = 'my_value'
    response = client.get('/secrets/api_key')
    assert response.status_code == 200
    assert response.json() == 'my_value'


@patch('eventum.api.routers.secrets.routes.get_secret')
def test_get_secret_not_found(mock_get, client):
    mock_get.side_effect = ValueError('not found')
    response = client.get('/secrets/missing_key')
    assert response.status_code == 404


@patch('eventum.api.routers.secrets.routes.get_secret')
def test_get_secret_os_error(mock_get, client):
    mock_get.side_effect = OSError('keyring error')
    response = client.get('/secrets/bad_key')
    assert response.status_code == 500


# --- GET / ---


@patch('eventum.api.routers.secrets.routes.list_secrets')
def test_list_secrets(mock_list, client):
    mock_list.return_value = ['key1', 'key2']
    response = client.get('/secrets/')
    assert response.status_code == 200
    assert response.json() == ['key1', 'key2']


# --- PUT /{name} ---


@patch('eventum.api.routers.secrets.routes.set_secret')
def test_set_secret(mock_set, client):
    response = client.put(
        '/secrets/api_key',
        content='"new_value"',
        headers={'Content-Type': 'application/json'},
    )
    assert response.status_code == 200


# --- DELETE /{name} ---


@patch('eventum.api.routers.secrets.routes.remove_secret')
def test_delete_secret(mock_remove, client):
    response = client.delete('/secrets/api_key')
    assert response.status_code == 200
