"""Tests for generator configs API router."""

import aiofiles
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
from eventum.core.parameters import GenerationParameters


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
def client(tmp_settings, manager):
    app = FastAPI()
    app.state.settings = tmp_settings
    app.state.generator_manager = manager
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


def test_get_file_tree_reports_sizes(client, tmp_settings):
    gen_dir = _create_config(tmp_settings, 'size_gen')
    (gen_dir / 'sample.csv').write_bytes(b'a,b,c')

    response = client.get('/configs/size_gen/file-tree')
    assert response.status_code == 200

    nodes = {node['name']: node for node in response.json()}
    assert nodes['sample.csv']['size_in_bytes'] == len(b'a,b,c')


# --- GET /{name}/file/{filepath} ---


def test_get_file(client, tmp_settings):
    gen_dir = _create_config(tmp_settings, 'read_gen')
    (gen_dir / 'notes.txt').write_text('file content')

    response = client.get('/configs/read_gen/file/notes.txt')
    assert response.status_code == 200
    assert response.text == 'file content'
    assert response.headers['content-type'] == 'text/plain; charset=utf-8'


def test_get_file_declares_no_length(client, tmp_settings):
    # A file a generator is writing to changes its size at any moment,
    # so a declared length stops matching the body being sent and the
    # response is aborted mid-body.
    gen_dir = _create_config(tmp_settings, 'length_gen')
    (gen_dir / 'output.ndjson').write_text('{"a": 1}\n')

    response = client.get('/configs/length_gen/file/output.ndjson')
    assert response.status_code == 200
    assert 'content-length' not in response.headers


def test_get_file_not_found(client, tmp_settings):
    _create_config(tmp_settings, 'missing_file_gen')

    response = client.get('/configs/missing_file_gen/file/absent.txt')
    assert response.status_code == 404


def test_get_file_os_error(client, tmp_settings, monkeypatch):
    gen_dir = _create_config(tmp_settings, 'error_gen')
    (gen_dir / 'notes.txt').write_text('file content')

    def raise_os_error(*args, **kwargs):
        raise OSError('permission denied')

    monkeypatch.setattr(aiofiles, 'open', raise_os_error)

    response = client.get('/configs/error_gen/file/notes.txt')
    assert response.status_code == 500
    assert 'OS error' in response.json()['detail']


# --- Directory traversal ---


def test_directory_traversal_blocked(client):
    response = client.get('/configs/..%2F..%2Fetc')
    assert response.status_code in (403, 404, 422)
