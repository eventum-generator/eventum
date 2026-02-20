"""Tests for auth API router."""

import base64

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from eventum.api.dependencies.app import get_settings
from eventum.api.dependencies.authentication import (
    clear_all_sessions,
    get_session_user,
)
from eventum.api.routers.auth.routes import router
from eventum.app.models.parameters.log import LogParameters
from eventum.app.models.parameters.path import PathParameters
from eventum.app.models.parameters.server import (
    AuthParameters,
    ServerParameters,
)
from eventum.app.models.settings import Settings
from eventum.core.parameters import GenerationParameters


def _make_settings(tmp_path):
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


@pytest.fixture(autouse=True)
def _clean_sessions():
    yield
    clear_all_sessions()


@pytest.fixture()
def client(tmp_path):
    app = FastAPI()
    settings = _make_settings(tmp_path)
    app.state.settings = settings
    app.include_router(router, prefix='/auth')
    return TestClient(app)


def _basic_auth_header(user, password):
    creds = base64.b64encode(f'{user}:{password}'.encode()).decode()
    return {'Authorization': f'Basic {creds}'}


def test_login_valid_creds(client):
    response = client.post(
        '/auth/login', headers=_basic_auth_header('admin', 'secret')
    )
    assert response.status_code == 200
    assert response.json() == 'admin'
    assert 'session_id' in response.cookies


def test_login_invalid_creds(client):
    response = client.post(
        '/auth/login', headers=_basic_auth_header('admin', 'wrong')
    )
    assert response.status_code == 401


def test_me_with_session(client):
    login_resp = client.post(
        '/auth/login', headers=_basic_auth_header('admin', 'secret')
    )
    session_cookie = login_resp.cookies.get('session_id')
    response = client.get('/auth/me', cookies={'session_id': session_cookie})
    assert response.status_code == 200
    assert response.json() == 'admin'


def test_me_with_basic_auth(client):
    response = client.get(
        '/auth/me', headers=_basic_auth_header('admin', 'secret')
    )
    assert response.status_code == 200
    assert response.json() == 'admin'


def test_me_without_auth(client):
    response = client.get('/auth/me')
    assert response.status_code == 401


def test_logout_clears_session(client):
    login_resp = client.post(
        '/auth/login', headers=_basic_auth_header('admin', 'secret')
    )
    session_cookie = login_resp.cookies.get('session_id')
    assert get_session_user(session_cookie) == 'admin'

    client.post('/auth/logout', cookies={'session_id': session_cookie})
    assert get_session_user(session_cookie) is None


def test_logout_without_session(client):
    response = client.post('/auth/logout')
    assert response.status_code == 200
