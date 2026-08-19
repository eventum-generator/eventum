"""Tests for scenarios router helpers and endpoints."""

from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from eventum.api.routers.scenarios import router
from eventum.app.models.parameters.log import LogParameters
from eventum.app.models.parameters.path import PathParameters
from eventum.app.models.parameters.server import ServerParameters
from eventum.app.models.settings import Settings
from eventum.core.parameters import GenerationParameters

# --- GET /{name}/generators/{generator_name}/globals-usage ---


@pytest.fixture
def client(tmp_path):
    settings = Settings(
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
    settings.path.generators_dir.mkdir()
    settings.path.startup.write_text(
        '- id: gen-1\n'
        '  path: gen-1/generator.yml\n'
        '  scenarios:\n'
        '    - myscenario\n'
    )
    gen_dir = settings.path.generators_dir / 'gen-1'
    gen_dir.mkdir()
    (gen_dir / 'event.j2').write_text('{%- do globals.set("users", x) -%}')

    app = FastAPI()
    app.state.settings = settings
    app.include_router(router, prefix='/scenarios')
    with TestClient(app) as c:
        yield c


def test_globals_usage_endpoint_returns_usage(client):
    response = client.get(
        '/scenarios/myscenario/generators/gen-1/globals-usage'
    )

    assert response.status_code == 200
    data = response.json()
    assert [w['key'] for w in data['writes']] == ['users']
    assert data['reads'] == []


def test_globals_usage_endpoint_unknown_scenario(client):
    response = client.get('/scenarios/absent/generators/gen-1/globals-usage')

    assert response.status_code == 404


def test_globals_usage_endpoint_missing_generator(client):
    response = client.get(
        '/scenarios/myscenario/generators/absent/globals-usage'
    )

    assert response.status_code == 404
