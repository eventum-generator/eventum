"""Tests for generator configs API router."""

import yaml

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from eventum.api.routers.generator_configs.routes import router
from eventum.app.manager import GeneratorManager
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
def client(tmp_settings, manager):
    app = FastAPI()
    app.state.settings = tmp_settings
    app.state.generator_manager = manager
    app.include_router(router, prefix='/configs')
    return TestClient(app)


VALID_CONFIG = {
    'input': [{'cron': {'expression': '* * * * *', 'count': 1}}],
    'event': {'replay': {'path': 'events.log'}},
    'output': [{'stdout': {'formatter': {'format': 'plain'}}}],
}


def _create_config(settings, name='gen1'):
    gen_dir = settings.path.generators_dir / name
    gen_dir.mkdir(exist_ok=True)
    config_path = gen_dir / settings.path.generator_config_filename
    config_path.write_text(yaml.dump(VALID_CONFIG, sort_keys=False))
    return gen_dir


# --- GET / ---


def test_list_dirs_empty(client):
    response = client.get('/configs/')
    assert response.status_code == 200
    assert response.json() == []


def test_list_dirs_with_configs(client, tmp_settings):
    _create_config(tmp_settings, 'gen1')
    response = client.get('/configs/')
    assert response.status_code == 200
    assert 'gen1' in response.json()


# --- GET /{name} ---


def test_get_config_success(client, tmp_settings):
    _create_config(tmp_settings, 'gen_read')
    response = client.get('/configs/gen_read')
    assert response.status_code == 200
    data = response.json()
    assert 'input' in data
    assert 'event' in data
    assert 'output' in data


def test_get_config_not_found(client):
    response = client.get('/configs/nonexistent')
    assert response.status_code == 404


def test_get_config_invalid_yaml(client, tmp_settings):
    gen_dir = tmp_settings.path.generators_dir / 'bad_yaml'
    gen_dir.mkdir()
    config = gen_dir / tmp_settings.path.generator_config_filename
    config.write_text(': invalid: yaml: {{{\n')
    response = client.get('/configs/bad_yaml')
    assert response.status_code == 422


# --- POST /{name} ---


def test_create_config(client, tmp_settings):
    response = client.post('/configs/new_gen', json=VALID_CONFIG)
    assert response.status_code == 201
    config_path = (
        tmp_settings.path.generators_dir
        / 'new_gen'
        / tmp_settings.path.generator_config_filename
    )
    assert config_path.exists()


def test_create_config_already_exists(client, tmp_settings):
    _create_config(tmp_settings, 'existing')
    response = client.post('/configs/existing', json=VALID_CONFIG)
    assert response.status_code == 409


# --- PUT /{name} ---


def test_update_config(client, tmp_settings):
    _create_config(tmp_settings, 'upd_gen')
    updated_config = {
        'input': [{'cron': {'expression': '*/5 * * * *', 'count': 2}}],
        'event': {'replay': {'path': 'updated.log'}},
        'output': [{'stdout': {'formatter': {'format': 'plain'}}}],
    }
    response = client.put('/configs/upd_gen', json=updated_config)
    assert response.status_code == 200


# --- DELETE /{name} ---


def test_delete_config(client, tmp_settings):
    _create_config(tmp_settings, 'del_gen')
    response = client.delete('/configs/del_gen')
    assert response.status_code == 200
    assert not (tmp_settings.path.generators_dir / 'del_gen').exists()


def test_delete_config_not_found(client):
    response = client.delete('/configs/missing')
    assert response.status_code == 404


# --- GET /{name}/path ---


def test_get_config_path(client, tmp_settings):
    _create_config(tmp_settings, 'path_gen')
    response = client.get('/configs/path_gen/path')
    assert response.status_code == 200
    assert 'path_gen' in response.json()


# --- GET /{name}/file-tree ---


def test_get_file_tree(client, tmp_settings):
    gen_dir = _create_config(tmp_settings, 'tree_gen')
    (gen_dir / 'templates').mkdir()
    (gen_dir / 'templates' / 'event.jinja').write_text('{{ ts }}')
    response = client.get('/configs/tree_gen/file-tree')
    assert response.status_code == 200
    data = response.json()
    names = {node['name'] for node in data}
    assert tmp_settings.path.generator_config_filename.name in names
    assert 'templates' in names


# --- Directory traversal ---


def test_directory_traversal_blocked(client):
    response = client.get('/configs/..%2F..%2Fetc')
    assert response.status_code in (403, 404, 422)
