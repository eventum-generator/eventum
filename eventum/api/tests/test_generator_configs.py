"""Tests for generator configs API router."""

import io
import zipfile
from unittest.mock import MagicMock, patch

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

# 'sobytiya.log' spelled in Cyrillic
NON_ASCII_VALUE = 'события.log'

NON_ASCII_CONFIG = {
    'input': [{'cron': {'expression': '* * * * *', 'count': 1}}],
    'event': {'replay': {'path': NON_ASCII_VALUE}},
    'output': [{'stdout': {'formatter': {'format': 'plain'}}}],
}


def _create_config(settings, name='gen1'):
    gen_dir = settings.path.generators_dir / name
    gen_dir.mkdir(exist_ok=True)
    config_path = gen_dir / settings.path.generator_config_filename
    config_path.write_text(yaml.dump(VALID_CONFIG, sort_keys=False))
    return gen_dir


def _read_config(settings, name):
    config_path = (
        settings.path.generators_dir
        / name
        / settings.path.generator_config_filename
    )
    return config_path.read_text(encoding='utf-8')


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


def test_get_config_with_non_ascii(client):
    client.post('/configs/non_ascii_read_gen', json=NON_ASCII_CONFIG)

    response = client.get('/configs/non_ascii_read_gen')

    assert response.status_code == 200
    assert response.json()['event']['replay']['path'] == NON_ASCII_VALUE


def test_get_config_invalid_encoding(client, tmp_settings):
    gen_dir = tmp_settings.path.generators_dir / 'bad_encoding'
    gen_dir.mkdir()
    config = gen_dir / tmp_settings.path.generator_config_filename
    config.write_bytes(b'event:\n  replay:\n    path: \xff\xfe.log\n')

    response = client.get('/configs/bad_encoding')

    assert response.status_code == 422
    assert 'encoding error' in response.json()['detail']


def test_get_config_with_fsm_conditions(
    client: TestClient,
    tmp_settings: Settings,
) -> None:
    """Condition state fields and param names are served as written."""
    condition = {'ge': {'shared.step': 5}}
    fsm_config = {
        'input': [{'cron': {'expression': '* * * * *', 'count': 1}}],
        'event': {
            'template': {
                'mode': 'fsm',
                'params': {'host.name': 'srv-01'},
                'templates': [
                    {
                        'login': {
                            'template': 'login.jinja',
                            'initial': True,
                            'transitions': [
                                {'to': 'logout', 'when': condition},
                            ],
                        },
                    },
                    {'logout': {'template': 'logout.jinja'}},
                ],
            },
        },
        'output': [{'stdout': {'formatter': {'format': 'plain'}}}],
    }
    gen_dir = tmp_settings.path.generators_dir / 'fsm_gen'
    gen_dir.mkdir()
    config_path = gen_dir / tmp_settings.path.generator_config_filename
    config_path.write_text(yaml.dump(fsm_config, sort_keys=False))

    response = client.get('/configs/fsm_gen')

    assert response.status_code == 200  # noqa: PLR2004
    template_config = response.json()['event']['template']
    assert template_config['params'] == {'host.name': 'srv-01'}

    transitions = template_config['templates'][0]['login']['transitions']
    assert transitions[0]['when'] == condition


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


def test_create_config_keeps_non_ascii_unescaped(client, tmp_settings):
    response = client.post('/configs/non_ascii_gen', json=NON_ASCII_CONFIG)
    assert response.status_code == 201

    content = _read_config(tmp_settings, 'non_ascii_gen')
    assert NON_ASCII_VALUE in content
    assert '\\u' not in content


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


def test_update_config_keeps_non_ascii_unescaped(client, tmp_settings):
    _create_config(tmp_settings, 'upd_non_ascii_gen')

    response = client.put('/configs/upd_non_ascii_gen', json=NON_ASCII_CONFIG)
    assert response.status_code == 200

    content = _read_config(tmp_settings, 'upd_non_ascii_gen')
    assert NON_ASCII_VALUE in content
    assert '\\u' not in content


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


# --- GET /{name}/export ---


def _archive_names(content: bytes) -> set[str]:
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        return {name.rstrip('/') for name in archive.namelist()}


def _build_archive(entries: dict[str, str]) -> bytes:
    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, mode='w') as archive:
        for name, content in entries.items():
            archive.writestr(name, content)

    return buffer.getvalue()


def test_export_config(client, tmp_settings):
    gen_dir = _create_config(tmp_settings, 'gen1')
    (gen_dir / 'templates').mkdir()
    (gen_dir / 'templates' / 'event.jinja').write_text('{}')

    response = client.get('/configs/gen1/export')

    assert response.status_code == 200
    assert response.headers['content-type'] == 'application/zip'
    assert 'gen1.zip' in response.headers['content-disposition']
    assert _archive_names(response.content) == {
        'generator.yml',
        'templates',
        'templates/event.jinja',
    }


def test_export_config_excludes_entries(client, tmp_settings):
    gen_dir = _create_config(tmp_settings, 'gen1')
    (gen_dir / 'output').mkdir()
    (gen_dir / 'output' / 'events.log').write_text('event')

    response = client.get('/configs/gen1/export', params={'exclude': 'output'})

    assert response.status_code == 200
    assert _archive_names(response.content) == {'generator.yml'}


def test_export_config_rejects_excluded_configuration(client, tmp_settings):
    _create_config(tmp_settings, 'gen1')

    response = client.get(
        '/configs/gen1/export', params={'exclude': 'generator.yml'}
    )

    assert response.status_code == 400


def test_export_config_rejects_nested_exclude(client, tmp_settings):
    _create_config(tmp_settings, 'gen1')

    response = client.get(
        '/configs/gen1/export', params={'exclude': 'output/events.log'}
    )

    assert response.status_code == 400


def test_export_config_not_found(client):
    response = client.get('/configs/absent/export')

    assert response.status_code == 404


# --- POST /{name}/import ---


def test_import_config(client, tmp_settings):
    archive = _build_archive(
        {
            'generator.yml': 'input: []',
            'templates/event.jinja': '{}',
        },
    )

    response = client.post(
        '/configs/imported/import',
        files={'content': ('project.zip', archive, 'application/zip')},
    )

    assert response.status_code == 201

    gen_dir = tmp_settings.path.generators_dir / 'imported'
    assert (gen_dir / 'generator.yml').read_text() == 'input: []'
    assert (gen_dir / 'templates' / 'event.jinja').read_text() == '{}'


def test_import_config_strips_wrapping_directory(client, tmp_settings):
    archive = _build_archive({'web-nginx/generator.yml': 'input: []'})

    response = client.post(
        '/configs/imported/import',
        files={'content': ('project.zip', archive, 'application/zip')},
    )

    assert response.status_code == 201
    assert (
        tmp_settings.path.generators_dir / 'imported' / 'generator.yml'
    ).is_file()


def test_import_config_leaves_no_staging_directory(client, tmp_settings):
    archive = _build_archive({'generator.yml': 'input: []'})

    client.post(
        '/configs/imported/import',
        files={'content': ('project.zip', archive, 'application/zip')},
    )

    assert [
        path.name for path in tmp_settings.path.generators_dir.iterdir()
    ] == ['imported']


def test_import_config_already_exists(client, tmp_settings):
    _create_config(tmp_settings, 'gen1')
    archive = _build_archive({'generator.yml': 'input: []'})

    response = client.post(
        '/configs/gen1/import',
        files={'content': ('project.zip', archive, 'application/zip')},
    )

    assert response.status_code == 409


def test_import_config_directory_exists(client, tmp_settings):
    (tmp_settings.path.generators_dir / 'gen1').mkdir()
    archive = _build_archive({'generator.yml': 'input: []'})

    response = client.post(
        '/configs/gen1/import',
        files={'content': ('project.zip', archive, 'application/zip')},
    )

    assert response.status_code == 409


def test_import_config_not_an_archive(client, tmp_settings):
    response = client.post(
        '/configs/imported/import',
        files={
            'content': ('project.zip', b'not an archive', 'application/zip')
        },
    )

    assert response.status_code == 422
    assert not (tmp_settings.path.generators_dir / 'imported').exists()
    assert list(tmp_settings.path.generators_dir.iterdir()) == []


def test_import_config_without_configuration(client, tmp_settings):
    archive = _build_archive({'templates/event.jinja': '{}'})

    response = client.post(
        '/configs/imported/import',
        files={'content': ('project.zip', archive, 'application/zip')},
    )

    assert response.status_code == 422
