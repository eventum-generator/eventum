"""Tests for startup API router."""

from collections.abc import Iterator

import pytest
import yaml
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
from eventum.app.startup import Startup
from eventum.core.parameters import GenerationParameters


@pytest.fixture
def tmp_settings(tmp_path: object) -> Settings:
    """Build a minimal Settings pointing at tmp_path."""
    generators_dir = tmp_path / 'generators'  # type: ignore[operator]
    generators_dir.mkdir()
    startup_file = tmp_path / 'startup.yml'  # type: ignore[operator]
    startup_file.write_text(yaml.dump([], sort_keys=False))

    return Settings(
        server=ServerParameters(
            auth=AuthParameters(user='admin', password='secret'),  # noqa: S106
        ),
        generation=GenerationParameters(),
        log=LogParameters(),
        path=PathParameters(
            logs=tmp_path / 'logs',  # type: ignore[operator]
            startup=startup_file,
            generators_dir=generators_dir,
            keyring_cryptfile=tmp_path / 'keyring.dat',  # type: ignore[operator]
        ),
    )


@pytest.fixture
def client(tmp_settings: Settings) -> Iterator[TestClient]:
    """Build a TestClient with Startup wired to tmp_settings."""
    app = FastAPI()
    app.state.settings = tmp_settings
    app.state.startup = Startup(
        file_path=tmp_settings.path.startup,
        generators_dir=tmp_settings.path.generators_dir,
        generation_parameters=tmp_settings.generation,
    )
    app.include_router(router, prefix='/startup')
    with TestClient(app) as c:
        yield c


def _write_startup(settings: Settings, entries: list[dict]) -> None:
    settings.path.startup.write_text(yaml.dump(entries, sort_keys=False))


def _gen_entry(gen_id: str, path: str = 'gen/generator.yml') -> dict:
    return {
        'id': gen_id,
        'path': path,
    }


# --- GET / ---


def test_list_startup_empty(client: TestClient) -> None:
    """Empty startup file yields an empty list response."""
    response = client.get('/startup/')
    assert response.status_code == 200  # noqa: S101, PLR2004
    assert response.json() == []  # noqa: S101


def test_list_startup_with_entries(
    client: TestClient,
    tmp_settings: Settings,
) -> None:
    """Existing entries are returned in the listing."""
    _write_startup(tmp_settings, [_gen_entry('gen1')])
    response = client.get('/startup/')
    assert response.status_code == 200  # noqa: S101, PLR2004
    data = response.json()
    assert len(data) == 1  # noqa: S101
    assert data[0]['id'] == 'gen1'  # noqa: S101


# --- GET /{id} ---


def test_get_startup_entry(
    client: TestClient,
    tmp_settings: Settings,
) -> None:
    """Existing id returns the matching entry."""
    _write_startup(tmp_settings, [_gen_entry('gen1')])
    response = client.get('/startup/gen1')
    assert response.status_code == 200  # noqa: S101, PLR2004
    assert response.json()['id'] == 'gen1'  # noqa: S101


def test_get_startup_entry_not_found(
    client: TestClient,
    tmp_settings: Settings,
) -> None:
    """Unknown id returns 404."""
    _write_startup(tmp_settings, [_gen_entry('gen1')])
    response = client.get('/startup/missing')
    assert response.status_code == 404  # noqa: S101, PLR2004


# --- POST /{id} ---


def test_add_startup_entry(
    client: TestClient,
    tmp_settings: Settings,
) -> None:
    """New entry is added and persisted."""
    response = client.post(
        '/startup/new_gen',
        json=_gen_entry('new_gen'),
    )
    assert response.status_code == 201  # noqa: S101, PLR2004
    content = yaml.safe_load(tmp_settings.path.startup.read_text())
    assert any(e['id'] == 'new_gen' for e in content)  # noqa: S101


def test_add_startup_entry_duplicate(
    client: TestClient,
    tmp_settings: Settings,
) -> None:
    """Adding a duplicate id returns 409."""
    _write_startup(tmp_settings, [_gen_entry('dup_gen')])
    response = client.post(
        '/startup/dup_gen',
        json=_gen_entry('dup_gen'),
    )
    assert response.status_code == 409  # noqa: S101, PLR2004


# --- PUT /{id} ---


def test_update_startup_entry(
    client: TestClient,
    tmp_settings: Settings,
) -> None:
    """Existing entry is updated."""
    _write_startup(tmp_settings, [_gen_entry('upd_gen')])
    response = client.put(
        '/startup/upd_gen',
        json=_gen_entry('upd_gen', path='new_path/generator.yml'),
    )
    assert response.status_code == 200  # noqa: S101, PLR2004


# --- DELETE /{id} ---


def test_delete_startup_entry(
    client: TestClient,
    tmp_settings: Settings,
) -> None:
    """Existing entry is removed and the file reflects it."""
    _write_startup(tmp_settings, [_gen_entry('del_gen')])
    response = client.delete('/startup/del_gen')
    assert response.status_code == 200  # noqa: S101, PLR2004
    content = yaml.safe_load(tmp_settings.path.startup.read_text())
    assert content == [] or content is None  # noqa: S101


def test_delete_startup_entry_not_found(
    client: TestClient,
    tmp_settings: Settings,
) -> None:
    """Deleting an unknown id returns 404."""
    _write_startup(tmp_settings, [_gen_entry('gen1')])
    response = client.delete('/startup/missing')
    assert response.status_code == 404  # noqa: S101, PLR2004
