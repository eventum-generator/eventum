"""Tests of connected generator repositories."""

import os
import threading
from pathlib import Path
from wsgiref.simple_server import WSGIRequestHandler, make_server

import pytest
from dulwich import porcelain
from dulwich.repo import Repo
from dulwich.server import DictBackend
from dulwich.web import make_wsgi_chain
from pydantic import ValidationError

from eventum.app.repositories import (
    CatalogEntryNotFoundError,
    CatalogError,
    InstallConflictError,
    InstallNameError,
    Repositories,
    Repository,
    RepositoryConflictError,
    RepositoryError,
    RepositoryFetchError,
    RepositoryNotFoundError,
)
from eventum.app.repositories.catalog import read_catalog
from eventum.app.repositories.fetching import fetch_repository
from eventum.app.repositories.installing import install_entry
from eventum.app.repositories.storage import RepositoriesFile

CONFIG_FILENAME = 'generator.yml'

README = (
    '# Nginx Access Logs\n'
    '\n'
    '![badge](/badge.png)\n'
    '\n'
    'Produces **nginx** access log entries matching the '
    '[Elastic nginx integration](https://example.com/nginx).\n'
    'Follows the Elastic Common Schema.\n'
    '\n'
    '## Event types\n'
)


class _QuietHandler(WSGIRequestHandler):
    """Request handler that keeps the test output clean."""

    def log_message(self, *args: object) -> None:  # noqa: D102
        pass


def _build_source_repo(root: Path) -> Path:
    """Build a repository holding two published generators."""
    source = root / 'source'
    nginx = source / 'generators' / 'web-nginx'
    nginx.mkdir(parents=True)
    (nginx / CONFIG_FILENAME).write_text('input: []\n')
    (nginx / 'README.md').write_text(README)
    (nginx / 'templates').mkdir()
    (nginx / 'templates' / 'event.jinja').write_text('{{ timestamp }}')
    os.symlink('/etc/passwd', nginx / 'passwd')

    auditd = source / 'generators' / 'linux-auditd'
    auditd.mkdir(parents=True)
    (auditd / CONFIG_FILENAME).write_text('input: []\n')

    # A directory without a generator configuration is not published.
    docs = source / 'generators' / 'not-a-generator'
    docs.mkdir(parents=True)
    (docs / 'notes.md').write_text('notes\n')

    (source / 'README.md').write_text('# Content packs\n')

    repo = Repo.init(str(source))
    porcelain.add(
        repo,
        [
            str(path)
            for path in source.rglob('*')
            if path.is_symlink() or path.is_file()
        ],
    )
    porcelain.commit(
        repo,
        message=b'init',
        committer=b'Tester <tester@example.com>',
        author=b'Tester <tester@example.com>',
    )
    repo.close()

    return source


@pytest.fixture
def source_repo(tmp_path):
    return _build_source_repo(tmp_path)


@pytest.fixture
def git_url(source_repo):
    """Serve the source repository over HTTP and yield its URL."""
    repo = Repo(str(source_repo))
    server = make_server(
        '127.0.0.1',
        0,
        make_wsgi_chain(DictBackend({b'/': repo})),
        handler_class=_QuietHandler,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        yield f'http://127.0.0.1:{server.server_address[1]}/'
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()
        repo.close()


@pytest.fixture
def repository(git_url):
    return Repository(name='packs', url=git_url, ref='master')


@pytest.fixture
def service(tmp_path):
    service = Repositories(
        file_path=tmp_path / 'repositories.yml',
        generators_dir=tmp_path / 'generators',
        config_filename=CONFIG_FILENAME,
        fetch_timeout=15.0,
    )
    yield service
    service.close()


# --- models ---


@pytest.mark.parametrize(
    'url',
    [
        'ssh://git@example.com/packs.git',
        'git://example.com/packs.git',
        'file:///srv/packs',
        'ext::sh -c whoami',
        '/srv/packs',
    ],
)
def test_repository_rejects_url_scheme(url):
    with pytest.raises(ValidationError):
        Repository(name='packs', url=url)


def test_repository_rejects_url_with_credentials():
    with pytest.raises(ValidationError):
        Repository(name='packs', url='https://user:token@example.com/p.git')


def test_repository_rejects_name_with_separator():
    with pytest.raises(ValidationError):
        Repository(name='../packs', url='https://example.com/p.git')


@pytest.mark.parametrize('ref', ['../master', 'master/', 'branch.lock'])
def test_repository_rejects_ref(ref):
    with pytest.raises(ValidationError):
        Repository(name='packs', url='https://example.com/p.git', ref=ref)


def test_repository_accepts_https_url():
    repository = Repository(
        name='packs',
        url='https://example.com/packs.git',
        ref='v1.0',
    )

    assert repository.ref == 'v1.0'
    assert repository.secret is None


# --- storage ---


def test_storage_reads_missing_file_as_empty(tmp_path):
    file = RepositoriesFile(file_path=tmp_path / 'absent.yml')

    assert file.read() == []


def test_storage_round_trip(tmp_path):
    file = RepositoriesFile(file_path=tmp_path / 'repositories.yml')
    entries = [{'name': 'packs', 'url': 'https://example.com/p.git'}]

    file.write(entries)

    assert file.read() == entries


def test_storage_rejects_non_list_root(tmp_path):
    path = tmp_path / 'repositories.yml'
    path.write_text('name: packs\n')

    with pytest.raises(RepositoryError):
        RepositoriesFile(file_path=path).read()


def test_storage_rejects_broken_yaml(tmp_path):
    path = tmp_path / 'repositories.yml'
    path.write_text('- name: [packs\n')

    with pytest.raises(RepositoryError):
        RepositoriesFile(file_path=path).read()


# --- service CRUD ---


def test_service_adds_and_lists(service):
    repository = Repository(name='packs', url='https://example.com/p.git')

    service.add(repository)

    assert service.get_all().root == (repository,)
    assert service.get('packs') == repository


def test_service_rejects_duplicate_name(service):
    repository = Repository(name='packs', url='https://example.com/p.git')
    service.add(repository)

    with pytest.raises(RepositoryConflictError):
        service.add(repository)


def test_service_removes(service):
    service.add(Repository(name='packs', url='https://example.com/p.git'))

    service.remove('packs')

    assert service.get_all().root == ()


def test_service_reports_missing_repository(service):
    with pytest.raises(RepositoryNotFoundError):
        service.get('absent')

    with pytest.raises(RepositoryNotFoundError):
        service.remove('absent')


def test_service_persists_without_unset_fields(service, tmp_path):
    service.add(Repository(name='packs', url='https://example.com/p.git'))

    content = (tmp_path / 'repositories.yml').read_text()

    assert 'secret' not in content
    assert 'ref' not in content


def test_service_rejects_invalid_stored_entry(service, tmp_path):
    (tmp_path / 'repositories.yml').write_text('- name: packs\n')

    with pytest.raises(RepositoryError):
        service.get_all()


# --- fetching ---


def test_fetch_returns_revision(repository, tmp_path):
    revision = fetch_repository(
        repository,
        tmp_path / 'bare',
        timeout=15.0,
    )

    assert len(revision) == 40


def test_fetch_default_ref(git_url, tmp_path):
    repository = Repository(name='packs', url=git_url)

    revision = fetch_repository(repository, tmp_path / 'bare', timeout=15.0)

    assert len(revision) == 40


def test_fetch_by_tag(source_repo, git_url, tmp_path):
    repo = Repo(str(source_repo))
    repo.refs[b'refs/tags/v1.0'] = repo.head()
    repo.close()

    repository = Repository(name='packs', url=git_url, ref='v1.0')

    revision = fetch_repository(repository, tmp_path / 'bare', timeout=15.0)

    assert len(revision) == 40


def test_fetch_reports_unknown_ref(git_url, tmp_path):
    repository = Repository(name='packs', url=git_url, ref='absent')

    with pytest.raises(RepositoryFetchError):
        fetch_repository(repository, tmp_path / 'bare', timeout=15.0)


def test_fetch_reports_empty_remote(tmp_path):
    source = tmp_path / 'empty'
    source.mkdir()
    repo = Repo.init(str(source))
    server = make_server(
        '127.0.0.1',
        0,
        make_wsgi_chain(DictBackend({b'/': repo})),
        handler_class=_QuietHandler,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    repository = Repository(
        name='packs',
        url=f'http://127.0.0.1:{server.server_address[1]}/',
    )

    try:
        with pytest.raises(RepositoryFetchError):
            fetch_repository(repository, tmp_path / 'bare', timeout=15.0)
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()
        repo.close()


def test_fetch_reports_unreachable_remote(tmp_path):
    repository = Repository(
        name='packs',
        url='http://127.0.0.1:1/packs.git',
    )

    with pytest.raises(RepositoryFetchError):
        fetch_repository(repository, tmp_path / 'bare', timeout=5.0)


# --- catalog ---


@pytest.fixture
def fetched(repository, tmp_path):
    path = tmp_path / 'bare'
    revision = fetch_repository(repository, path, timeout=15.0)
    return path, revision


def test_catalog_lists_published_generators(fetched):
    path, revision = fetched

    catalog = read_catalog(path, revision, config_filename=CONFIG_FILENAME)

    assert [entry.name for entry in catalog.entries] == [
        'linux-auditd',
        'web-nginx',
    ]
    assert catalog.revision == revision


def test_catalog_reads_title_and_summary(fetched):
    path, revision = fetched

    catalog = read_catalog(path, revision, config_filename=CONFIG_FILENAME)
    entry = next(e for e in catalog.entries if e.name == 'web-nginx')

    assert entry.title == 'Nginx Access Logs'
    assert entry.summary == (
        'Produces nginx access log entries matching the Elastic nginx '
        'integration. Follows the Elastic Common Schema.'
    )


def test_catalog_counts_regular_files_only(fetched):
    path, revision = fetched

    catalog = read_catalog(path, revision, config_filename=CONFIG_FILENAME)
    entry = next(e for e in catalog.entries if e.name == 'web-nginx')

    # The generator holds a configuration, a readme, a template and a
    # symbolic link, and the link is not installed.
    assert entry.file_count == 3
    assert entry.size > 0


def test_catalog_reports_missing_generators_dir(tmp_path):
    source = tmp_path / 'plain'
    source.mkdir()
    (source / 'README.md').write_text('# plain\n')
    repo = Repo.init(str(source))
    porcelain.add(repo, [str(source / 'README.md')])
    porcelain.commit(
        repo,
        message=b'init',
        committer=b'Tester <tester@example.com>',
        author=b'Tester <tester@example.com>',
    )
    revision = repo.head().decode()
    repo.close()

    with pytest.raises(CatalogError):
        read_catalog(source, revision, config_filename=CONFIG_FILENAME)


# --- installing ---


def test_install_writes_project(fetched, tmp_path):
    path, revision = fetched
    generators_dir = tmp_path / 'generators'

    installed = install_entry(
        repo_path=path,
        revision=revision,
        entry='web-nginx',
        generators_dir=generators_dir,
        project_name='nginx',
        config_filename=CONFIG_FILENAME,
    )

    project = generators_dir / 'nginx'
    assert installed == 3
    assert (project / CONFIG_FILENAME).read_text() == 'input: []\n'
    assert (project / 'templates' / 'event.jinja').exists()
    assert not (project / 'passwd').exists()


def test_install_leaves_no_staging_behind(fetched, tmp_path):
    path, revision = fetched
    generators_dir = tmp_path / 'generators'

    install_entry(
        repo_path=path,
        revision=revision,
        entry='web-nginx',
        generators_dir=generators_dir,
        project_name='nginx',
        config_filename=CONFIG_FILENAME,
    )

    assert [item.name for item in generators_dir.iterdir()] == ['nginx']


def test_install_reports_existing_project(fetched, tmp_path):
    path, revision = fetched
    generators_dir = tmp_path / 'generators'
    (generators_dir / 'nginx').mkdir(parents=True)

    with pytest.raises(InstallConflictError):
        install_entry(
            repo_path=path,
            revision=revision,
            entry='web-nginx',
            generators_dir=generators_dir,
            project_name='nginx',
            config_filename=CONFIG_FILENAME,
        )


@pytest.mark.parametrize('name', ['..', '.', 'nested/name'])
def test_install_rejects_project_name(fetched, tmp_path, name):
    path, revision = fetched

    with pytest.raises(InstallNameError):
        install_entry(
            repo_path=path,
            revision=revision,
            entry='web-nginx',
            generators_dir=tmp_path / 'generators',
            project_name=name,
            config_filename=CONFIG_FILENAME,
        )


def test_install_reports_unknown_entry(fetched, tmp_path):
    path, revision = fetched

    with pytest.raises(CatalogEntryNotFoundError):
        install_entry(
            repo_path=path,
            revision=revision,
            entry='absent',
            generators_dir=tmp_path / 'generators',
            project_name='nginx',
            config_filename=CONFIG_FILENAME,
        )


# --- service operations ---


def test_service_reads_catalog_on_demand(service, repository):
    service.add(repository)

    catalog = service.get_catalog('packs')

    assert [entry.name for entry in catalog.entries] == [
        'linux-auditd',
        'web-nginx',
    ]


def test_service_serves_cached_catalog(service, repository):
    service.add(repository)

    first = service.get_catalog('packs')
    second = service.get_catalog('packs')

    assert first.refreshed_at == second.refreshed_at


def test_service_refresh_rereads_catalog(service, repository):
    service.add(repository)

    first = service.get_catalog('packs')
    second = service.refresh('packs')

    assert second.refreshed_at > first.refreshed_at
    assert second.revision == first.revision


def test_service_installs_entry(service, repository, tmp_path):
    service.add(repository)

    installed = service.install('packs', 'web-nginx', 'nginx')

    assert installed == 3
    assert (tmp_path / 'generators' / 'nginx' / CONFIG_FILENAME).exists()


def test_service_drops_fetched_repository_on_remove(service, repository):
    service.add(repository)
    service.get_catalog('packs')
    fetched_path = service._fetched['packs'].path  # noqa: SLF001

    service.remove('packs')

    assert not fetched_path.exists()


def test_service_close_drops_everything(service, repository):
    service.add(repository)
    service.get_catalog('packs')

    service.close()

    assert service._cache_dir is None  # noqa: SLF001


def test_service_reports_missing_secret(service, git_url):
    service.add(
        Repository(name='packs', url=git_url, secret='absent-secret'),
    )

    with pytest.raises(RepositoryFetchError):
        service.get_catalog('packs')
