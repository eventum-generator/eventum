"""Tests for secrets API router."""

from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from eventum.api.routers.secrets.routes import router
from eventum.app.models.parameters.log import LogParameters
from eventum.app.models.parameters.path import PathParameters
from eventum.app.models.parameters.server import ServerParameters
from eventum.app.models.settings import Settings
from eventum.app.renaming import (
    RenameConflictError,
    RenameError,
    RenameNotFoundError,
)
from eventum.app.repositories import Repositories, Repository
from eventum.core.parameters import GenerationParameters


@pytest.fixture
def app(tmp_path):
    fastapi_app = FastAPI()
    fastapi_app.state.settings = Settings(
        server=ServerParameters(),
        generation=GenerationParameters(),
        log=LogParameters(),
        path=PathParameters(
            logs=tmp_path / 'logs',
            startup=tmp_path / 'startup.yml',
            generators_dir=tmp_path / 'generators',
            keyring_cryptfile=tmp_path / 'keyring.cfg',
        ),
    )
    settings = fastapi_app.state.settings
    settings.path.generators_dir.mkdir()
    repositories = Repositories(
        file_path=settings.path.repositories_file,
        generators_dir=settings.path.generators_dir,
        config_filename=settings.path.generator_config_filename.name,
    )
    fastapi_app.state.repositories = repositories
    fastapi_app.include_router(router, prefix='/secrets')
    yield fastapi_app
    repositories.close()


@pytest.fixture
def generators_dir(app) -> Path:
    return app.state.settings.path.generators_dir


@pytest.fixture
def client(app):
    with TestClient(app) as c:
        yield c


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


# --- GET /{name}/references ---


def _write_config(generators_dir: Path, name: str, content: str) -> None:
    config_path = generators_dir / name / 'generator.yml'
    config_path.parent.mkdir(parents=True)
    config_path.write_text(content)


def _connect(app, name: str, secret: str) -> None:
    app.state.repositories.add(
        Repository(
            name=name,
            url=f'https://git.example.com/{name}.git',
            secret=secret,
        ),
        verify=False,
    )


def test_list_secret_references(client, generators_dir):
    _write_config(generators_dir, 'gen-a', 'token: ${secrets.api_key}\n')
    _write_config(generators_dir, 'gen-b', 'token: ${secrets.other}\n')

    response = client.get('/secrets/api_key/references')

    assert response.status_code == 200
    assert response.json() == {'projects': ['gen-a'], 'repositories': []}


def test_list_secret_references_reports_repositories(client, app):
    _connect(app, 'internal', 'api_key')
    _connect(app, 'other', 'another_key')

    response = client.get('/secrets/api_key/references')

    assert response.status_code == 200
    assert response.json() == {
        'projects': [],
        'repositories': ['internal'],
    }


def test_list_secret_references_none(client):
    response = client.get('/secrets/api_key/references')

    assert response.status_code == 200
    assert response.json() == {'projects': [], 'repositories': []}


def test_list_secret_references_unreadable_repositories(client, app):
    app.state.settings.path.repositories_file.write_text('name: broken\n')

    response = client.get('/secrets/api_key/references')

    assert response.status_code == 500


# --- POST /{name}/rename ---


@patch('eventum.api.routers.secrets.routes.rename_secret', autospec=True)
def test_rename_secret(mock_rename, client, app):
    mock_rename.return_value = ['internal']

    response = client.post(
        '/secrets/api_key/rename',
        json={'new_name': 'renamed'},
    )

    assert response.status_code == 200
    assert response.json() == ['internal']
    mock_rename.assert_called_once_with(
        repositories=app.state.repositories,
        name='api_key',
        new_name='renamed',
    )


@patch('eventum.api.routers.secrets.routes.rename_secret', autospec=True)
def test_rename_secret_not_found(mock_rename, client):
    mock_rename.side_effect = RenameNotFoundError(
        'Secret is missing',
        context={},
    )

    response = client.post(
        '/secrets/absent/rename',
        json={'new_name': 'renamed'},
    )

    assert response.status_code == 404


@patch('eventum.api.routers.secrets.routes.rename_secret', autospec=True)
def test_rename_secret_conflict(mock_rename, client):
    mock_rename.side_effect = RenameConflictError(
        'Already exists',
        context={},
    )

    response = client.post(
        '/secrets/api_key/rename',
        json={'new_name': 'taken'},
    )

    assert response.status_code == 409


@patch('eventum.api.routers.secrets.routes.rename_secret', autospec=True)
def test_rename_secret_failed_midway(mock_rename, client):
    mock_rename.side_effect = RenameError('keyring error', context={})

    response = client.post(
        '/secrets/api_key/rename',
        json={'new_name': 'renamed'},
    )

    assert response.status_code == 500


def test_rename_secret_blank_name(client):
    response = client.post(
        '/secrets/api_key/rename',
        json={'new_name': ''},
    )

    assert response.status_code == 422
