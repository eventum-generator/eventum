"""Tests for generators API router."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml
from fastapi import FastAPI
from fastapi.testclient import TestClient

from eventum.api.routers.generators.routes import router
from eventum.app.manager import GeneratorManager, ManagingError
from eventum.app.models.parameters.log import LogParameters
from eventum.app.models.parameters.path import PathParameters
from eventum.app.models.parameters.server import (
    AuthParameters,
    ServerParameters,
)
from eventum.app.models.settings import Settings
from eventum.app.startup import Startup
from eventum.core.parameters import GenerationParameters, GeneratorParameters


@pytest.fixture()
def tmp_settings(tmp_path):
    generators_dir = tmp_path / 'generators'
    generators_dir.mkdir()
    return Settings(
        server=ServerParameters(
            auth=AuthParameters(user='admin', password='secret'),
        ),
        generation=GenerationParameters(),
        log=LogParameters(),
        path=PathParameters(
            logs=tmp_path / 'logs',
            startup=tmp_path / 'startup.yml',
            generators_dir=generators_dir,
            keyring_cryptfile=tmp_path / 'keyring.dat',
        ),
    )


@pytest.fixture()
def manager():
    return GeneratorManager()


@pytest.fixture()
def startup(tmp_settings):
    tmp_settings.path.startup.write_text('')
    return Startup(
        file_path=tmp_settings.path.startup,
        generators_dir=tmp_settings.path.generators_dir,
        generation_parameters=tmp_settings.generation,
    )


@pytest.fixture()
def client(tmp_settings, manager, startup):
    app = FastAPI()
    app.state.settings = tmp_settings
    app.state.generator_manager = manager
    app.state.startup = startup
    app.include_router(router, prefix='/generators')
    with TestClient(app) as c:
        yield c


def _make_config_file(settings, name='test_gen'):
    gen_dir = settings.path.generators_dir / name
    gen_dir.mkdir(exist_ok=True)
    config = gen_dir / settings.path.generator_config_filename
    config.write_text('input: []\nevent: {}\noutput: []\n')
    return str(gen_dir / settings.path.generator_config_filename)


# --- GET / ---


def test_list_generators_empty(client):
    response = client.get('/generators/')
    assert response.status_code == 200
    assert response.json() == []


def test_list_generators_with_entries(client, manager, tmp_settings):
    config_path = _make_config_file(tmp_settings, 'gen1')
    params = GeneratorParameters(
        id='gen1',
        path=Path(config_path),
    )
    manager.add(params)
    response = client.get('/generators/')
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]['id'] == 'gen1'


# --- POST /{id} ---


def test_add_generator(client, tmp_settings):
    _make_config_file(tmp_settings, 'new_gen')
    response = client.post(
        '/generators/new_gen',
        json={
            'id': 'new_gen',
            'path': str(
                tmp_settings.path.generators_dir
                / 'new_gen'
                / tmp_settings.path.generator_config_filename
            ),
        },
    )
    assert response.status_code == 201


def test_add_generator_duplicate(client, manager, tmp_settings):
    config_path = _make_config_file(tmp_settings, 'dup_gen')
    params = GeneratorParameters(id='dup_gen', path=Path(config_path))
    manager.add(params)
    response = client.post(
        '/generators/dup_gen',
        json={
            'id': 'dup_gen',
            'path': str(config_path),
        },
    )
    assert response.status_code == 409


# --- GET /{id} ---


def test_get_generator_found(client, manager, tmp_settings):
    config_path = _make_config_file(tmp_settings, 'gen_get')
    params = GeneratorParameters(id='gen_get', path=Path(config_path))
    manager.add(params)
    response = client.get('/generators/gen_get')
    assert response.status_code == 200
    data = response.json()
    assert data['id'] == 'gen_get'


def test_get_generator_not_found(client):
    response = client.get('/generators/nonexistent')
    assert response.status_code == 404


# --- GET /{id}/status ---


def test_get_generator_status(client, manager, tmp_settings):
    config_path = _make_config_file(tmp_settings, 'gen_st')
    params = GeneratorParameters(id='gen_st', path=Path(config_path))
    manager.add(params)
    response = client.get('/generators/gen_st/status')
    assert response.status_code == 200
    data = response.json()
    assert data['is_running'] is False
    assert data['is_initializing'] is False


# --- POST /{id}/start ---


def test_start_generator_not_found(client):
    response = client.post('/generators/missing/start')
    assert response.status_code == 404


# --- POST /{id}/stop ---


def test_stop_generator_not_found(client):
    response = client.post('/generators/missing/stop')
    assert response.status_code == 404


# --- DELETE /{id} ---


def test_delete_generator(client, manager, tmp_settings):
    config_path = _make_config_file(tmp_settings, 'gen_del')
    params = GeneratorParameters(id='gen_del', path=Path(config_path))
    manager.add(params)
    response = client.delete('/generators/gen_del')
    assert response.status_code == 200
    assert 'gen_del' not in manager.generator_ids


def test_delete_generator_not_found(client):
    response = client.delete('/generators/missing')
    assert response.status_code == 404


# --- POST /group-actions/bulk-start ---


def test_bulk_start(client, manager, tmp_settings):
    config_path = _make_config_file(tmp_settings, 'bulk1')
    params = GeneratorParameters(id='bulk1', path=Path(config_path))
    manager.add(params)

    with patch.object(manager, 'bulk_start', return_value=(['bulk1'], [])):
        response = client.post(
            '/generators/group-actions/bulk-start',
            json=['bulk1'],
        )
    assert response.status_code == 200
    data = response.json()
    assert 'running_generator_ids' in data


# --- POST /group-actions/bulk-stop ---


def test_bulk_stop(client, manager, tmp_settings):
    config_path = _make_config_file(tmp_settings, 'bulk2')
    params = GeneratorParameters(id='bulk2', path=Path(config_path))
    manager.add(params)

    with patch.object(manager, 'bulk_stop'):
        response = client.post(
            '/generators/group-actions/bulk-stop',
            json=['bulk2'],
        )
    assert response.status_code == 200


# --- POST /{id}/rename ---


def test_rename_generator(client, manager, tmp_settings):
    config_path = _make_config_file(tmp_settings, 'ren_gen')
    manager.add(GeneratorParameters(id='ren_gen', path=Path(config_path)))

    response = client.post(
        '/generators/ren_gen/rename', json={'new_id': 'renamed'}
    )

    assert response.status_code == 200
    assert manager.generator_ids == ['renamed']


def test_rename_generator_renames_startup_entry(client, manager, tmp_settings):
    config_path = _make_config_file(tmp_settings, 'ren_gen')
    manager.add(GeneratorParameters(id='ren_gen', path=Path(config_path)))
    tmp_settings.path.startup.write_text(
        '- id: ren_gen\n  path: ren_gen/generator.yml\n'
    )

    response = client.post(
        '/generators/ren_gen/rename', json={'new_id': 'renamed'}
    )

    assert response.status_code == 200
    assert yaml.safe_load(tmp_settings.path.startup.read_text()) == [
        {'id': 'renamed', 'path': 'ren_gen/generator.yml'}
    ]


def test_rename_generator_not_found(client):
    response = client.post(
        '/generators/missing/rename', json={'new_id': 'renamed'}
    )

    assert response.status_code == 404


def test_rename_generator_id_taken(client, manager, tmp_settings):
    config_path = _make_config_file(tmp_settings, 'ren_gen')
    manager.add(GeneratorParameters(id='ren_gen', path=Path(config_path)))
    manager.add(GeneratorParameters(id='taken', path=Path(config_path)))

    response = client.post(
        '/generators/ren_gen/rename', json={'new_id': 'taken'}
    )

    assert response.status_code == 409
    assert manager.generator_ids == ['ren_gen', 'taken']


def test_rename_generator_active(client, manager, tmp_settings):
    config_path = _make_config_file(tmp_settings, 'ren_gen')
    manager.add(GeneratorParameters(id='ren_gen', path=Path(config_path)))

    with patch.object(
        type(manager.get_generator('ren_gen')),
        'is_running',
        new_callable=lambda: property(lambda self: True),
    ):
        response = client.post(
            '/generators/ren_gen/rename', json={'new_id': 'renamed'}
        )

    assert response.status_code == 409
    assert manager.generator_ids == ['ren_gen']


def test_rename_generator_blank_id(client, manager, tmp_settings):
    config_path = _make_config_file(tmp_settings, 'ren_gen')
    manager.add(GeneratorParameters(id='ren_gen', path=Path(config_path)))

    response = client.post('/generators/ren_gen/rename', json={'new_id': ''})

    assert response.status_code == 422
