"""Tests for startup API router."""

from pathlib import Path

import yaml

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from eventum.api.routers.startup.routes import router
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
    startup_file = tmp_path / 'startup.yml'
    startup_file.write_text(yaml.dump([], sort_keys=False))

    return Settings(
        server=ServerParameters(
            auth=AuthParameters(user='admin', password='secret'),
        ),
        generation=GenerationParameters(),
        log=LogParameters(),
        path=PathParameters(
            logs=tmp_path / 'logs',
            startup=startup_file,
            generators_dir=generators_dir,
            keyring_cryptfile=tmp_path / 'keyring.dat',
        ),
    )


@pytest.fixture()
def client(tmp_settings):
    app = FastAPI()
    app.state.settings = tmp_settings
    app.include_router(router, prefix='/startup')
    return TestClient(app)


def _write_startup(settings, entries):
    settings.path.startup.write_text(yaml.dump(entries, sort_keys=False))


def _gen_entry(gen_id, path='gen/generator.yml'):
    return {
        'id': gen_id,
        'path': path,
    }


# --- GET / ---


def test_list_startup_empty(client):
    response = client.get('/startup/')
    assert response.status_code == 200
    assert response.json() == []


def test_list_startup_with_entries(client, tmp_settings):
    _write_startup(tmp_settings, [_gen_entry('gen1')])
    response = client.get('/startup/')
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]['id'] == 'gen1'


# --- GET /{id} ---


def test_get_startup_entry(client, tmp_settings):
    _write_startup(tmp_settings, [_gen_entry('gen1')])
    response = client.get('/startup/gen1')
    assert response.status_code == 200
    assert response.json()['id'] == 'gen1'


def test_get_startup_entry_not_found(client, tmp_settings):
    _write_startup(tmp_settings, [_gen_entry('gen1')])
    response = client.get('/startup/missing')
    assert response.status_code == 404


# --- POST /{id} ---


def test_add_startup_entry(client, tmp_settings):
    response = client.post(
        '/startup/new_gen',
        json=_gen_entry('new_gen'),
    )
    assert response.status_code == 201
    content = yaml.safe_load(tmp_settings.path.startup.read_text())
    assert any(e['id'] == 'new_gen' for e in content)


def test_add_startup_entry_duplicate(client, tmp_settings):
    _write_startup(tmp_settings, [_gen_entry('dup_gen')])
    response = client.post(
        '/startup/dup_gen',
        json=_gen_entry('dup_gen'),
    )
    assert response.status_code == 409


# --- PUT /{id} ---


def test_update_startup_entry(client, tmp_settings):
    _write_startup(tmp_settings, [_gen_entry('upd_gen')])
    response = client.put(
        '/startup/upd_gen',
        json=_gen_entry('upd_gen', path='new_path/generator.yml'),
    )
    assert response.status_code == 200


# --- DELETE /{id} ---


def test_delete_startup_entry(client, tmp_settings):
    _write_startup(tmp_settings, [_gen_entry('del_gen')])
    response = client.delete('/startup/del_gen')
    assert response.status_code == 200
    content = yaml.safe_load(tmp_settings.path.startup.read_text())
    assert content == [] or content is None


def test_delete_startup_entry_not_found(client, tmp_settings):
    _write_startup(tmp_settings, [_gen_entry('gen1')])
    response = client.delete('/startup/missing')
    assert response.status_code == 404
