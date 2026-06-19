"""Tests for scenarios router helpers and endpoints."""

from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from eventum.api.routers.scenarios import router
from eventum.api.routers.scenarios.routes import _collect_globals_usage
from eventum.app.models.parameters.log import LogParameters
from eventum.app.models.parameters.path import PathParameters
from eventum.app.models.parameters.server import ServerParameters
from eventum.app.models.settings import Settings
from eventum.core.parameters import GenerationParameters

# --- _collect_globals_usage ---


def test_collect_finds_templates_recursively(tmp_path):
    (tmp_path / 'root.jinja').write_text('{%- do globals.set("a", 1) -%}')
    sub = tmp_path / 'sub'
    sub.mkdir()
    (sub / 'nested.j2').write_text('{%- set x = globals.get("b", 0) -%}')

    usage = _collect_globals_usage(tmp_path)

    assert {w.key for w in usage.writes} == {'a'}
    assert {r.key for r in usage.reads} == {'b'}
    templates = {w.template for w in usage.writes}
    templates |= {r.template for r in usage.reads}
    assert templates == {'root.jinja', str(Path('sub') / 'nested.j2')}


def test_collect_skips_non_template_files(tmp_path):
    (tmp_path / 'data.txt').write_text('{%- do globals.set("x", 1) -%}')
    (tmp_path / 'config.yml').write_text('{%- do globals.set("y", 1) -%}')

    usage = _collect_globals_usage(tmp_path)

    assert usage.writes == []
    assert usage.reads == []


def test_collect_empty_dir(tmp_path):
    usage = _collect_globals_usage(tmp_path)

    assert usage.writes == []
    assert usage.reads == []
    assert usage.warnings == []


def test_collect_merges_warnings(tmp_path):
    (tmp_path / 'template.j2').write_text('{%- do globals.update(data) -%}')

    usage = _collect_globals_usage(tmp_path)

    assert len(usage.warnings) == 1
    assert usage.warnings[0].type == 'update_call'


def test_collect_skips_unreadable_file(tmp_path):
    (tmp_path / 'good.j2').write_text('{%- do globals.set("a", 1) -%}')
    (tmp_path / 'bad.j2').write_text('{%- do globals.set("b", 1) -%}')

    real_read_text = Path.read_text

    def fake_read_text(self, *args, **kwargs):
        if self.name == 'bad.j2':
            raise OSError('boom')
        return real_read_text(self, *args, **kwargs)

    with patch.object(Path, 'read_text', fake_read_text):
        usage = _collect_globals_usage(tmp_path)

    assert {w.key for w in usage.writes} == {'a'}


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
