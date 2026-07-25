"""Tests for generator configs API router."""

from unittest.mock import MagicMock, patch

import pytest
import yaml
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
from eventum.app.startup import Startup
from eventum.core.parameters import (
    GenerationParameters,
    GeneratorParameters,
)


@pytest.fixture
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


@pytest.fixture
def manager():
    return GeneratorManager()


@pytest.fixture
def startup(tmp_settings):
    tmp_settings.path.startup.write_text('')
    return Startup(
        file_path=tmp_settings.path.startup,
        generators_dir=tmp_settings.path.generators_dir,
        generation_parameters=tmp_settings.generation,
    )


@pytest.fixture
def client(tmp_settings, manager, startup):
    app = FastAPI()
    app.state.settings = tmp_settings
    app.state.generator_manager = manager
    app.state.startup = startup
    app.include_router(router, prefix='/configs')
    with TestClient(app) as c:
        yield c


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


def test_get_config_with_placeholders(client, tmp_settings):
    config_with_placeholders = {
        'input': [
            {
                'cron': {
                    'expression': '* * * * *',
                    'count': '${params.count}',
                }
            },
        ],
        'event': {'replay': {'path': 'events.log'}},
        'output': [
            {
                'opensearch': {
                    'hosts': ['${params.opensearch_host}'],
                    'username': '${params.opensearch_user}',
                    'password': '${secrets.opensearch_password}',
                    'index': '${params.opensearch_index}',
                    'verify': '${params.verify}',
                    'connect_timeout': '${params.timeout}',
                    'formatter': {'format': 'json'},
                },
            },
        ],
    }
    gen_dir = tmp_settings.path.generators_dir / 'placeholder_gen'
    gen_dir.mkdir()
    config_path = gen_dir / tmp_settings.path.generator_config_filename
    config_path.write_text(
        yaml.dump(config_with_placeholders, sort_keys=False)
    )
    response = client.get('/configs/placeholder_gen')
    assert response.status_code == 200
    data = response.json()

    # String fields preserve placeholders
    output_config = data['output'][0]['opensearch']
    assert output_config['hosts'] == ['${params.opensearch_host}']
    assert output_config['username'] == '${params.opensearch_user}'
    assert output_config['password'] == '${secrets.opensearch_password}'

    # Non-string fields (int, bool) also preserve placeholders
    assert output_config['verify'] == '${params.verify}'
    assert output_config['connect_timeout'] == '${params.timeout}'
    assert data['input'][0]['cron']['count'] == '${params.count}'


def test_create_config_with_placeholders(client, tmp_settings):
    config_with_placeholders = {
        'input': [
            {
                'cron': {
                    'expression': '* * * * *',
                    'count': '${params.count}',
                }
            },
        ],
        'event': {'replay': {'path': 'events.log'}},
        'output': [
            {
                'opensearch': {
                    'hosts': ['${params.opensearch_host}'],
                    'username': '${params.opensearch_user}',
                    'password': '${secrets.opensearch_password}',
                    'index': '${params.opensearch_index}',
                    'verify': '${params.verify}',
                    'formatter': {'format': 'json'},
                },
            },
        ],
    }
    response = client.post(
        '/configs/placeholder_post',
        json=config_with_placeholders,
    )
    assert response.status_code == 201

    # Verify persisted config preserves placeholders
    config_path = (
        tmp_settings.path.generators_dir
        / 'placeholder_post'
        / tmp_settings.path.generator_config_filename
    )
    saved = yaml.safe_load(config_path.read_text())
    assert saved['output'][0]['opensearch']['verify'] == '${params.verify}'
    assert saved['input'][0]['cron']['count'] == '${params.count}'


def test_get_config_invalid_yaml(client, tmp_settings):
    gen_dir = tmp_settings.path.generators_dir / 'bad_yaml'
    gen_dir.mkdir()
    config = gen_dir / tmp_settings.path.generator_config_filename
    config.write_text(': invalid: yaml: {{{\n')
    response = client.get('/configs/bad_yaml')
    assert response.status_code == 422


def test_get_config_expands_dotted_keys(
    client: TestClient,
    tmp_settings: Settings,
) -> None:
    """Dotted spelling is served identically to the nested form."""
    dotted_config = {
        'input': [{'cron.expression': '* * * * *', 'cron.count': 1}],
        'event': {'replay.path': 'events.log'},
        'output': [{'stdout.formatter.format': 'plain'}],
    }
    _create_config(tmp_settings, 'canonical_gen')
    gen_dir = tmp_settings.path.generators_dir / 'dotted_gen'
    gen_dir.mkdir()
    config_path = gen_dir / tmp_settings.path.generator_config_filename
    config_path.write_text(yaml.dump(dotted_config, sort_keys=False))

    dotted = client.get('/configs/dotted_gen')
    canonical = client.get('/configs/canonical_gen')

    assert dotted.status_code == 200  # noqa: PLR2004
    assert dotted.json() == canonical.json()


def test_get_config_conflicting_dotted_keys(
    client: TestClient,
    tmp_settings: Settings,
) -> None:
    """Conflicting spellings yield 422 naming the key path."""
    gen_dir = tmp_settings.path.generators_dir / 'conflict_gen'
    gen_dir.mkdir()
    config_path = gen_dir / tmp_settings.path.generator_config_filename
    config_path.write_text(
        'input:\n'
        '- cron:\n'
        "    expression: '* * * * *'\n"
        '    count: 1\n'
        'event:\n'
        '  replay.path: a.log\n'
        '  replay:\n'
        '    path: b.log\n'
        'output:\n'
        '- stdout:\n'
        '    formatter:\n'
        '      format: plain\n',
    )

    response = client.get('/configs/conflict_gen')

    assert response.status_code == 422  # noqa: PLR2004
    assert 'event.replay.path' in response.json()['detail']


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


# --- POST /{name}/rename ---


def test_rename_config(client, tmp_settings):
    _create_config(tmp_settings, 'ren_gen')

    response = client.post(
        '/configs/ren_gen/rename', json={'new_name': 'renamed'}
    )

    assert response.status_code == 200
    assert response.json() == []
    assert not (tmp_settings.path.generators_dir / 'ren_gen').exists()
    assert (
        tmp_settings.path.generators_dir
        / 'renamed'
        / tmp_settings.path.generator_config_filename
    ).is_file()


def test_rename_config_repoints_startup_entry(
    client,
    tmp_settings,
    startup,  # noqa: ARG001
):
    _create_config(tmp_settings, 'ren_gen')
    tmp_settings.path.startup.write_text(
        '- id: gen-1\n  path: ren_gen/generator.yml\n'
    )

    response = client.post(
        '/configs/ren_gen/rename', json={'new_name': 'renamed'}
    )

    assert response.status_code == 200
    assert yaml.safe_load(tmp_settings.path.startup.read_text()) == [
        {'id': 'gen-1', 'path': 'renamed/generator.yml'}
    ]


def test_rename_config_not_found(client):
    response = client.post(
        '/configs/missing/rename', json={'new_name': 'renamed'}
    )

    assert response.status_code == 404


def test_rename_config_name_taken(client, tmp_settings):
    _create_config(tmp_settings, 'ren_gen')
    _create_config(tmp_settings, 'taken')

    response = client.post(
        '/configs/ren_gen/rename', json={'new_name': 'taken'}
    )

    assert response.status_code == 409
    assert (tmp_settings.path.generators_dir / 'ren_gen').is_dir()


def test_rename_config_active_instance(client, tmp_settings, manager):
    _create_config(tmp_settings, 'ren_gen')
    with patch('eventum.app.manager.Generator') as generator_class:
        generator_class.return_value = MagicMock(
            params=GeneratorParameters(
                id='gen-1',
                path=(
                    tmp_settings.path.generators_dir
                    / 'ren_gen'
                    / 'generator.yml'
                ),
            ),
            is_initializing=False,
            is_running=True,
            is_stopping=False,
        )
        manager.add(
            GeneratorParameters(
                id='gen-1',
                path=(
                    tmp_settings.path.generators_dir
                    / 'ren_gen'
                    / 'generator.yml'
                ),
            )
        )

    response = client.post(
        '/configs/ren_gen/rename', json={'new_name': 'renamed'}
    )

    assert response.status_code == 409
    assert (tmp_settings.path.generators_dir / 'ren_gen').is_dir()


def test_rename_config_blank_name(client, tmp_settings):
    _create_config(tmp_settings, 'ren_gen')

    response = client.post('/configs/ren_gen/rename', json={'new_name': ''})

    assert response.status_code == 422


def test_rename_config_nested_name(client, tmp_settings):
    _create_config(tmp_settings, 'ren_gen')

    response = client.post(
        '/configs/ren_gen/rename', json={'new_name': 'nested/renamed'}
    )

    assert response.status_code == 422
    assert (tmp_settings.path.generators_dir / 'ren_gen').is_dir()
