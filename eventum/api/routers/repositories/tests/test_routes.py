"""Tests of repositories endpoints."""

from datetime import UTC, datetime
from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from eventum.api.routers.repositories import router
from eventum.app.repositories import (
    Catalog,
    CatalogEntry,
    CatalogEntryNotFoundError,
    CatalogError,
    ConnectedRepository,
    DiscoveredRepository,
    Discovery,
    DiscoveryRate,
    InstallConflictError,
    InstallContentError,
    InstallError,
    InstallNameError,
    Repositories,
    Repository,
    RepositoryDiscoveryError,
    RepositoryDiscoveryLimitError,
    RepositoryError,
    RepositoryFetchError,
    RepositoryNotFoundError,
    RepositorySecretError,
    RepositoryStatus,
)

CATALOG = Catalog(
    revision='0' * 40,
    refreshed_at=datetime(2026, 1, 1, tzinfo=UTC),
    committed_at=datetime(2025, 12, 31, tzinfo=UTC),
    author='Tester',
    entries=[
        CatalogEntry(
            name='web-nginx',
            path='generators/web-nginx',
            tree='b' * 40,
            title='Nginx Access Logs',
            summary='Produces nginx access log entries.',
            file_count=3,
            size=1024,
        ),
    ],
)


def _build_client(repositories: Repositories) -> TestClient:
    app = FastAPI()
    app.state.repositories = repositories
    app.include_router(router, prefix='/repositories')
    return TestClient(app)


@pytest.fixture
def service(tmp_path):
    return Repositories(
        file_path=tmp_path / 'repositories.yml',
        generators_dir=tmp_path / 'generators',
        config_filename='generator.yml',
    )


@pytest.fixture
def client(service):
    with _build_client(service) as client:
        yield client


@pytest.fixture
def stub():
    return Mock(spec=Repositories)


@pytest.fixture
def stub_client(stub):
    with _build_client(stub) as client:
        yield client


# --- list, add and remove ---


def test_list_is_empty_initially(client):
    response = client.get('/repositories/')

    assert response.status_code == 200
    assert response.json() == []


def test_add_and_list(client):
    added = client.post(
        '/repositories/?verify=false',
        json={'name': 'packs', 'url': 'https://example.com/packs.git'},
    )

    assert added.status_code == 201

    listed = client.get('/repositories/')
    assert listed.status_code == 200
    assert [item['name'] for item in listed.json()] == ['packs']


def test_add_rejects_unsupported_url(client):
    response = client.post(
        '/repositories/?verify=false',
        json={'name': 'packs', 'url': 'ssh://git@example.com/packs.git'},
    )

    assert response.status_code == 422


def test_add_reports_duplicate(client):
    payload = {'name': 'packs', 'url': 'https://example.com/packs.git'}
    client.post('/repositories/?verify=false', json=payload)

    response = client.post('/repositories/?verify=false', json=payload)

    assert response.status_code == 409


def test_remove(client):
    client.post(
        '/repositories/?verify=false',
        json={'name': 'packs', 'url': 'https://example.com/packs.git'},
    )

    response = client.delete('/repositories/packs')

    assert response.status_code == 200
    assert client.get('/repositories/').json() == []


def test_remove_reports_a_broken_file(stub, stub_client):
    stub.remove.side_effect = RepositoryError('broken', context={})

    response = stub_client.delete('/repositories/packs')

    assert response.status_code == 500


def test_remove_reports_missing(client):
    response = client.delete('/repositories/absent')

    assert response.status_code == 404


def test_list_reports_broken_file(client, tmp_path):
    (tmp_path / 'repositories.yml').write_text('name: packs\n')

    response = client.get('/repositories/')

    assert response.status_code == 500


def test_add_checks_the_repository_by_default(stub, stub_client):
    stub_client.post(
        '/repositories/',
        json={'name': 'packs', 'url': 'https://example.com/packs.git'},
    )

    _, kwargs = stub.add.call_args
    assert kwargs == {'verify': True}


def test_add_can_skip_the_check(stub, stub_client):
    stub_client.post(
        '/repositories/?verify=false',
        json={'name': 'packs', 'url': 'https://example.com/packs.git'},
    )

    _, kwargs = stub.add.call_args
    assert kwargs == {'verify': False}


def test_add_reports_an_unreachable_repository(stub, stub_client):
    stub.add.side_effect = RepositoryFetchError(
        'Failed to reach repository',
        context={'reason': 'Connection refused'},
    )

    response = stub_client.post(
        '/repositories/',
        json={'name': 'packs', 'url': 'https://example.com/packs.git'},
    )

    assert response.status_code == 502
    assert response.json()['detail'].endswith('Connection refused')


def test_check_reports_status(stub, stub_client):
    stub.check.return_value = RepositoryStatus(
        state='unavailable',
        checked_at=datetime(2026, 1, 1, tzinfo=UTC),
        reason='Connection refused',
    )

    response = stub_client.post('/repositories/packs/check')

    assert response.status_code == 200
    assert response.json()['state'] == 'unavailable'


def test_check_reports_missing_repository(stub, stub_client):
    stub.check.side_effect = RepositoryNotFoundError('absent', context={})

    response = stub_client.post('/repositories/absent/check')

    assert response.status_code == 404


def test_list_carries_the_status(stub, stub_client):
    stub.get_all_with_status.return_value = [
        ConnectedRepository(
            name='packs',
            url='https://example.com/packs.git',
            status=RepositoryStatus(state='unknown'),
        ),
    ]

    response = stub_client.get('/repositories/')

    assert response.json()[0]['status']['state'] == 'unknown'


# --- catalog and refresh ---


def test_get_catalog(stub, stub_client):
    stub.get_catalog.return_value = CATALOG

    response = stub_client.get('/repositories/packs/catalog')

    assert response.status_code == 200
    assert response.json()['entries'][0]['name'] == 'web-nginx'


def test_refresh_catalog(stub, stub_client):
    stub.refresh.return_value = CATALOG

    response = stub_client.post('/repositories/packs/refresh')

    assert response.status_code == 200
    assert response.json()['revision'] == '0' * 40


@pytest.mark.parametrize(
    'error',
    [
        RepositoryFetchError('unreachable', context={}),
        CatalogError('no generators directory', context={}),
    ],
)
def test_get_catalog_reports_fetch_failure(stub, stub_client, error):
    stub.get_catalog.side_effect = error

    response = stub_client.get('/repositories/packs/catalog')

    assert response.status_code == 502


def test_a_failure_carries_no_secret_value(stub, stub_client):
    # The reason a remote gives may quote what was sent to it, and the
    # value of a secret is the one thing that may not come back out.
    stub.get_catalog.side_effect = RepositoryFetchError(
        'Failed to fetch repository',
        context={'reason': 'unexpected http resp 401 for https://host/p.git'},
    )

    response = stub_client.get('/repositories/packs/catalog')

    assert 'ghp_' not in response.text
    assert response.status_code == 502


def test_get_catalog_carries_the_reason(stub, stub_client):
    stub.get_catalog.side_effect = RepositoryFetchError(
        'Failed to fetch repository',
        context={'reason': 'Connection refused', 'url': 'https://host/p.git'},
    )

    response = stub_client.get('/repositories/packs/catalog')

    assert response.json()['detail'].endswith('Connection refused')
    assert 'https://host/p.git' not in response.json()['detail']


def test_get_catalog_reports_broken_file(stub, stub_client):
    stub.get_catalog.side_effect = RepositoryError(
        'Repositories file is not valid YAML',
        context={'reason': 'line 2: mapping values are not allowed'},
    )

    response = stub_client.get('/repositories/packs/catalog')

    assert response.status_code == 500
    assert response.json()['detail'].endswith(
        'mapping values are not allowed',
    )


def test_add_reports_a_missing_secret(stub, stub_client):
    stub.add.side_effect = RepositorySecretError(
        'Failed to read the secret of the repository',
        context={'hint': 'Add the secret using the eventum-keyring CLI'},
    )

    response = stub_client.post(
        '/repositories/',
        json={
            'name': 'packs',
            'url': 'https://example.com/packs.git',
            'secret': 'git_token',
        },
    )

    assert response.status_code == 424


def test_add_reports_a_broken_file(stub, stub_client):
    stub.add.side_effect = RepositoryError('broken', context={})

    response = stub_client.post(
        '/repositories/',
        json={'name': 'packs', 'url': 'https://example.com/packs.git'},
    )

    assert response.status_code == 500


def test_check_reports_a_missing_secret(stub, stub_client):
    stub.check.side_effect = RepositorySecretError('absent', context={})

    response = stub_client.post('/repositories/packs/check')

    assert response.status_code == 424


def test_check_reports_a_broken_file(stub, stub_client):
    stub.check.side_effect = RepositoryError('broken', context={})

    response = stub_client.post('/repositories/packs/check')

    assert response.status_code == 500


def test_get_catalog_reports_a_repository_that_is_not_connected(
    stub,
    stub_client,
):
    stub.get_catalog.side_effect = RepositoryNotFoundError(
        'absent',
        context={},
    )

    response = stub_client.get('/repositories/absent/catalog')

    assert response.status_code == 404


def test_get_catalog_reports_a_missing_secret(stub, stub_client):
    stub.get_catalog.side_effect = RepositorySecretError('absent', context={})

    response = stub_client.get('/repositories/packs/catalog')

    assert response.status_code == 424


@pytest.mark.parametrize(
    ('error', 'expected_status'),
    [
        (RepositoryNotFoundError('absent', context={}), 404),
        (RepositorySecretError('no secret', context={}), 424),
        (CatalogError('no catalog', context={}), 502),
        (RepositoryError('broken', context={}), 500),
    ],
)
def test_refresh_reports_failure(stub, stub_client, error, expected_status):
    stub.refresh.side_effect = error

    response = stub_client.post('/repositories/packs/refresh')

    assert response.status_code == expected_status


# --- install ---


def test_install(stub, stub_client):
    stub.install.return_value = 3

    response = stub_client.post(
        '/repositories/packs/catalog/web-nginx/install',
        json={'name': 'nginx'},
    )

    assert response.status_code == 201
    assert response.json() == {'name': 'nginx', 'file_count': 3}
    stub.install.assert_called_once_with('packs', 'web-nginx', 'nginx')


def test_install_reports_a_missing_secret(stub, stub_client):
    stub.install.side_effect = RepositorySecretError(
        'Failed to read the secret of the repository',
        context={'hint': 'Add the secret using the eventum-keyring CLI'},
    )

    response = stub_client.post(
        '/repositories/packs/catalog/web-nginx/install',
        json={'name': 'nginx'},
    )

    assert response.status_code == 424
    assert 'eventum-keyring' in response.json()['detail']


@pytest.mark.parametrize('name', ['..', '.', 'nested/name', ''])
def test_install_rejects_project_name(stub_client, name):
    response = stub_client.post(
        '/repositories/packs/catalog/web-nginx/install',
        json={'name': name},
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    ('error', 'expected_status'),
    [
        (CatalogEntryNotFoundError('absent', context={}), 404),
        (InstallNameError('bad name', context={}), 400),
        (InstallConflictError('exists', context={}), 409),
        (InstallContentError('too large', context={}), 502),
        (InstallError('cannot write', context={}), 500),
        (RepositoryFetchError('unreachable', context={}), 502),
        (RepositoryError('broken', context={}), 500),
    ],
)
def test_install_reports_failure(stub, stub_client, error, expected_status):
    stub.install.side_effect = error

    response = stub_client.post(
        '/repositories/packs/catalog/web-nginx/install',
        json={'name': 'nginx'},
    )

    assert response.status_code == expected_status


# --- discovery ---

DISCOVERY = Discovery(
    topic='eventum-generators',
    query='',
    entries=(
        DiscoveredRepository(
            name='content-packs',
            full_name='eventum-generator/content-packs',
            url='https://github.com/eventum-generator/content-packs.git',
            page_url='https://github.com/eventum-generator/content-packs',
            owner='eventum-generator',
            description='Ready-made generators',
            topics=('eventum-generators',),
            stars=42,
            updated_at=datetime(2026, 1, 1, tzinfo=UTC),
            license='Apache-2.0',
            official=True,
            connected=True,
        ),
    ),
    total_count=1,
    refreshed_at=datetime(2026, 1, 1, tzinfo=UTC),
    rate=DiscoveryRate(remaining=9, reset_at=datetime(2026, 1, 1, tzinfo=UTC)),
)


def test_discover_lists_published_repositories(stub, stub_client):
    stub.discover.return_value = DISCOVERY

    response = stub_client.get('/repositories/discover?query=nginx&page=2')

    assert response.status_code == 200
    body = response.json()
    assert body['topic'] == 'eventum-generators'
    assert body['entries'][0]['full_name'] == (
        'eventum-generator/content-packs'
    )
    assert body['entries'][0]['connected'] is True
    stub.discover.assert_called_once_with('nginx', 2)


def test_discover_is_not_read_as_a_repository_name(stub, stub_client):
    # The route sits beside "/{name}/catalog", so a repository named
    # "discover" must not take the path of the search.
    stub.discover.return_value = DISCOVERY

    assert stub_client.get('/repositories/discover').status_code == 200
    stub.get_catalog.assert_not_called()


def test_discover_rejects_a_page_out_of_range(stub_client):
    assert stub_client.get('/repositories/discover?page=0').status_code == 422
    assert stub_client.get('/repositories/discover?page=99').status_code == 422


def test_discover_reports_a_spent_quota(stub, stub_client):
    stub.discover.side_effect = RepositoryDiscoveryLimitError(
        'rate limited',
        context={'reason': 'API rate limit exceeded', 'seconds': 31},
    )

    response = stub_client.get('/repositories/discover')

    assert response.status_code == 429
    assert response.headers['retry-after'] == '31'


def test_discover_reports_a_spent_quota_without_a_delay(stub, stub_client):
    stub.discover.side_effect = RepositoryDiscoveryLimitError(
        'rate limited',
        context={'reason': 'API rate limit exceeded', 'seconds': None},
    )

    response = stub_client.get('/repositories/discover')

    assert response.status_code == 429
    assert 'retry-after' not in response.headers


def test_discover_reports_a_failed_search(stub, stub_client):
    stub.discover.side_effect = RepositoryDiscoveryError(
        'unreachable',
        context={'reason': 'connection refused'},
    )

    response = stub_client.get('/repositories/discover')

    assert response.status_code == 502
    assert 'connection refused' in response.json()['detail']


def test_discover_reports_an_unreadable_list(stub, stub_client):
    stub.discover.side_effect = RepositoryError('broken', context={})

    assert stub_client.get('/repositories/discover').status_code == 500
