"""Tests of connected generator repositories."""

import base64
import os
import threading
from unittest.mock import patch
from pathlib import Path
from wsgiref.simple_server import WSGIRequestHandler, make_server

import pytest
from dulwich import porcelain
from dulwich.objects import Blob, Commit, Tree
from dulwich.repo import Repo
from dulwich.server import DictBackend
from dulwich.web import make_wsgi_chain
from pydantic import ValidationError

from eventum.app.repositories import (
    CatalogEntryNotFoundError,
    CatalogError,
    InstallConflictError,
    InstallContentError,
    InstallError,
    InstallNameError,
    Repositories,
    Repository,
    RepositoryConflictError,
    RepositoryError,
    RepositoryFetchError,
    RepositoryNotFoundError,
    RepositorySecretError,
)
from eventum.app.repositories.catalog import MAX_TREE_DEPTH, read_catalog
from eventum.app.repositories.models import (
    REDACTED_PASSWORD,
    redact_password,
    secret_reference,
)
from eventum.app.repositories.fetching import (
    _failure_context,
    fetch_repository,
    probe_repository,
)
from eventum.app.repositories.source import (
    SOURCE_FILENAME,
    build_source,
    read_source,
    write_source,
)
from eventum.app.repositories.installing import install_entry
from eventum.app.repositories.storage import RepositoriesFile
from eventum.security.manage import SECURITY_SETTINGS, set_secret

CONFIG_FILENAME = 'generator.yml'

SOURCE = build_source(
    repository='packs',
    url='https://example.com/packs.git',
    ref=None,
    entry='web-nginx',
    revision='0' * 40,
    tree='b' * 40,
)

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
def unauthorized_url():
    """Serve a host that asks every caller who they are."""

    def application(environ, start_response):  # noqa: ANN001, ANN202, ARG001
        start_response(
            '401 Unauthorized',
            [
                ('WWW-Authenticate', 'Basic realm="git"'),
                ('Content-Type', 'text/plain'),
            ],
        )
        return [b'unauthorized']

    server = make_server(
        '127.0.0.1',
        0,
        application,
        handler_class=_QuietHandler,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        yield f'http://127.0.0.1:{server.server_address[1]}/packs.git'
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


@pytest.fixture
def credentials_url():
    """Serve a host that records what every caller authenticates as."""
    seen: list[str] = []

    def application(environ, start_response):  # noqa: ANN001, ANN202
        seen.append(environ.get('HTTP_AUTHORIZATION', ''))
        start_response(
            '401 Unauthorized',
            [
                ('WWW-Authenticate', 'Basic realm="git"'),
                ('Content-Type', 'text/plain'),
            ],
        )
        return [b'unauthorized']

    server = make_server(
        '127.0.0.1',
        0,
        application,
        handler_class=_QuietHandler,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        yield f'http://127.0.0.1:{server.server_address[1]}/packs.git', seen
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


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


def test_repository_rejects_an_url_without_a_host():
    with pytest.raises(ValidationError):
        Repository(name='packs', url='https:///packs.git')


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
    assert repository.password is None


@pytest.mark.parametrize(
    'password',
    ['ghp_token', '${secrets.git_token}', 'prefix-${secrets.git_token}'],
)
def test_repository_accepts_password(password):
    repository = Repository(
        name='packs',
        url='https://example.com/packs.git',
        password=password,
    )

    assert repository.password == password


@pytest.mark.parametrize(
    'password',
    ['${params.git_token}', '${git_token}', '${secrets.}', 'a${b}c'],
)
def test_repository_rejects_a_token_of_another_kind(password):
    with pytest.raises(ValidationError):
        Repository(
            name='packs',
            url='https://example.com/packs.git',
            password=password,
        )


@pytest.mark.parametrize(
    ('password', 'expected'),
    [
        (None, None),
        ('ghp_token', None),
        ('${secrets.git_token}', 'git_token'),
        ('${ secrets.git_token }', 'git_token'),
        ('${secrets.git.token}', 'git.token'),
        ('prefix-${secrets.git_token}', None),
        ('${secrets.git_token}-suffix', None),
        ('${secrets.a}b}', None),
        ('${params.git_token}', None),
    ],
)
def test_secret_reference_reads_the_referenced_name(password, expected):
    assert secret_reference(password) == expected


@pytest.mark.parametrize(
    ('password', 'expected'),
    [
        (None, None),
        ('ghp_token', REDACTED_PASSWORD),
        ('prefix-${secrets.git_token}', REDACTED_PASSWORD),
        ('${secrets.a}b}', REDACTED_PASSWORD),
        ('${params.git_token}', REDACTED_PASSWORD),
        ('${secrets.git_token}', '${secrets.git_token}'),
    ],
)
def test_redact_password_hides_only_a_carried_credential(password, expected):
    assert redact_password(password) == expected


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

    service.add(repository, verify=False)

    assert service.get_all().root == (repository,)
    assert service.get('packs') == repository


def test_service_rejects_duplicate_name(service):
    repository = Repository(name='packs', url='https://example.com/p.git')
    service.add(repository, verify=False)

    with pytest.raises(RepositoryConflictError):
        service.add(repository, verify=False)


def test_service_removes(service):
    service.add(
        Repository(name='packs', url='https://example.com/p.git'),
        verify=False,
    )

    service.remove('packs')

    assert service.get_all().root == ()


def test_service_reports_missing_repository(service):
    with pytest.raises(RepositoryNotFoundError):
        service.get('absent')

    with pytest.raises(RepositoryNotFoundError):
        service.remove('absent')


def test_service_persists_without_unset_fields(service, tmp_path):
    service.add(
        Repository(name='packs', url='https://example.com/p.git'),
        verify=False,
    )

    content = (tmp_path / 'repositories.yml').read_text()

    assert 'password' not in content
    assert 'ref' not in content


def test_service_rejects_invalid_stored_entry(service, tmp_path):
    (tmp_path / 'repositories.yml').write_text('- name: packs\n')

    with pytest.raises(RepositoryError):
        service.get_all()


# --- secrets a repository holds ---


def _with_secret(service, name, secret):
    """Connect a repository authenticating with the given secret."""
    service.add(
        Repository(
            name=name,
            url=f'https://example.com/{name}.git',
            secret=secret,
        ),
        verify=False,
    )


def test_service_finds_the_repositories_holding_a_secret(service):
    _with_secret(service, 'mirror', 'git_token')
    _with_secret(service, 'internal', 'git_token')
    _with_secret(service, 'other', 'another_token')
    _with_secret(service, 'public', None)

    assert service.find_secret_users('git_token') == ['internal', 'mirror']
    assert service.find_secret_users('absent') == []


def test_service_repoints_only_the_repositories_holding_a_secret(service):
    _with_secret(service, 'mirror', 'git_token')
    _with_secret(service, 'internal', 'git_token')
    _with_secret(service, 'other', 'another_token')

    repointed = service.repoint_secret('git_token', 'forge_token')

    assert repointed == ['internal', 'mirror']
    assert service.get('internal').secret == 'forge_token'
    assert service.get('mirror').secret == 'forge_token'
    assert service.get('other').secret == 'another_token'


def test_service_repoints_nothing_when_no_repository_holds_it(
    service,
    tmp_path,
):
    _with_secret(service, 'other', 'another_token')
    path = tmp_path / 'repositories.yml'
    written = path.read_text()

    assert service.repoint_secret('git_token', 'forge_token') == []
    assert service.get('other').secret == 'another_token'
    assert path.read_text() == written


def test_service_refuses_a_secret_name_it_cannot_hold(service):
    _with_secret(service, 'internal', 'git_token')

    with pytest.raises(RepositoryError):
        service.repoint_secret('git_token', 'x' * 256)

    assert service.get('internal').secret == 'git_token'


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


def test_probe_hints_at_a_private_repository(unauthorized_url):
    repository = Repository(name='packs', url=unauthorized_url)

    with pytest.raises(RepositoryFetchError) as info:
        probe_repository(repository, timeout=15.0)

    assert 'hint' in info.value.context


def test_probe_does_not_hint_when_credentials_are_named(unauthorized_url):
    repository = Repository(
        name='packs',
        url=unauthorized_url,
        username='someone',
    )

    with pytest.raises(RepositoryFetchError) as info:
        probe_repository(repository, password='token', timeout=15.0)

    assert 'hint' not in info.value.context


def test_failure_hides_the_secret_it_was_given():
    repository = Repository(name='packs', url='https://example.com/p.git')

    context = _failure_context(
        repository,
        'ghp_secret_token',
        RuntimeError('rejected ghp_secret_token for packs'),
    )

    assert 'ghp_secret_token' not in context['reason']
    assert '***' in context['reason']


def test_catalog_reads_a_tree_that_lists_one_subtree_twice(tmp_path):
    # A tree that names the same subtree from many places is a graph,
    # not a hierarchy: walking every path through it costs 2^n, so
    # what has been walked is remembered. Without that, this never
    # returns.
    source = tmp_path / 'looping'
    source.mkdir()
    repo = Repo.init(str(source))
    store = repo.object_store

    blob = Blob.from_string(b'x')
    store.add_object(blob)

    level = Tree()
    level.add(b'generator.yml', 0o100644, blob.id)
    store.add_object(level)

    for _ in range(40):
        nested = Tree()
        nested.add(b'a', 0o040000, level.id)
        nested.add(b'b', 0o040000, level.id)
        store.add_object(nested)
        level = nested

    entry = Tree()
    entry.add(b'generator.yml', 0o100644, blob.id)
    entry.add(b'templates', 0o040000, level.id)
    store.add_object(entry)

    generators = Tree()
    generators.add(b'web-nginx', 0o040000, entry.id)
    store.add_object(generators)

    root = Tree()
    root.add(b'generators', 0o040000, generators.id)
    store.add_object(root)

    commit = Commit()
    commit.tree = root.id
    commit.author = commit.committer = b'Tester <tester@example.com>'
    commit.commit_time = commit.author_time = 0
    commit.commit_timezone = commit.author_timezone = 0
    commit.message = b'looping'
    store.add_object(commit)
    revision = commit.id.decode()
    repo.close()

    catalog = read_catalog(source, revision, config_filename=CONFIG_FILENAME)

    assert [entry.name for entry in catalog.entries] == ['web-nginx']


def test_catalog_refuses_a_tree_nested_too_deeply(tmp_path):
    source = tmp_path / 'deep'
    source.mkdir()
    repo = Repo.init(str(source))
    store = repo.object_store

    blob = Blob.from_string(b'x')
    store.add_object(blob)

    level = Tree()
    level.add(b'generator.yml', 0o100644, blob.id)
    store.add_object(level)

    for depth in range(MAX_TREE_DEPTH + 2):
        nested = Tree()
        nested.add(f'level-{depth}'.encode(), 0o040000, level.id)
        store.add_object(nested)
        level = nested

    entry = Tree()
    entry.add(b'generator.yml', 0o100644, blob.id)
    entry.add(b'templates', 0o040000, level.id)
    store.add_object(entry)

    generators = Tree()
    generators.add(b'web-nginx', 0o040000, entry.id)
    store.add_object(generators)

    root = Tree()
    root.add(b'generators', 0o040000, generators.id)
    store.add_object(root)

    commit = Commit()
    commit.tree = root.id
    commit.author = commit.committer = b'Tester <tester@example.com>'
    commit.commit_time = commit.author_time = 0
    commit.commit_timezone = commit.author_timezone = 0
    commit.message = b'deep'
    store.add_object(commit)
    revision = commit.id.decode()
    repo.close()

    with pytest.raises(CatalogError):
        read_catalog(source, revision, config_filename=CONFIG_FILENAME)


def test_catalog_refuses_a_directory_that_is_absent(tmp_path):
    source = tmp_path / 'missing'
    source.mkdir()
    repo = Repo.init(str(source))
    store = repo.object_store

    blob = Blob.from_string(b'x')
    store.add_object(blob)

    entry = Tree()
    entry.add(b'generator.yml', 0o100644, blob.id)
    # A directory entry naming an object the repository does not hold.
    entry.add(b'templates', 0o040000, b'a' * 40)
    store.add_object(entry)

    generators = Tree()
    generators.add(b'web-nginx', 0o040000, entry.id)
    store.add_object(generators)

    root = Tree()
    root.add(b'generators', 0o040000, generators.id)
    store.add_object(root)

    commit = Commit()
    commit.tree = root.id
    commit.author = commit.committer = b'Tester <tester@example.com>'
    commit.commit_time = commit.author_time = 0
    commit.commit_timezone = commit.author_timezone = 0
    commit.message = b'missing'
    store.add_object(commit)
    revision = commit.id.decode()
    repo.close()

    with pytest.raises(CatalogError):
        read_catalog(source, revision, config_filename=CONFIG_FILENAME)


def test_catalog_refuses_a_directory_that_is_not_one(tmp_path):
    source = tmp_path / 'confused'
    source.mkdir()
    repo = Repo.init(str(source))
    store = repo.object_store

    blob = Blob.from_string(b'not a tree')
    store.add_object(blob)

    entry = Tree()
    entry.add(b'generator.yml', 0o100644, blob.id)
    # A blob behind an entry that claims to be a directory.
    entry.add(b'templates', 0o040000, blob.id)
    store.add_object(entry)

    generators = Tree()
    generators.add(b'web-nginx', 0o040000, entry.id)
    store.add_object(generators)

    root = Tree()
    root.add(b'generators', 0o040000, generators.id)
    store.add_object(root)

    commit = Commit()
    commit.tree = root.id
    commit.author = commit.committer = b'Tester <tester@example.com>'
    commit.commit_time = commit.author_time = 0
    commit.commit_timezone = commit.author_timezone = 0
    commit.message = b'confused'
    store.add_object(commit)
    revision = commit.id.decode()
    repo.close()

    with pytest.raises(CatalogError):
        read_catalog(source, revision, config_filename=CONFIG_FILENAME)


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


def test_probe_accepts_reachable_repository(repository):
    probe_repository(repository, timeout=15.0)


def test_probe_reports_unknown_ref(git_url):
    repository = Repository(name='packs', url=git_url, ref='absent')

    with pytest.raises(RepositoryFetchError):
        probe_repository(repository, timeout=15.0)


def test_probe_reports_unreachable_remote():
    repository = Repository(name='packs', url='http://127.0.0.1:1/p.git')

    with pytest.raises(RepositoryFetchError):
        probe_repository(repository, timeout=5.0)


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
        source=SOURCE,
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
        source=SOURCE,
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
            source=SOURCE,
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
            source=SOURCE,
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
            source=SOURCE,
        )


def test_catalog_refuses_a_tree_wider_than_can_be_read(fetched):
    path, revision = fetched

    with (
        patch('eventum.app.repositories.catalog.MAX_TREE_NODES', 1),
        pytest.raises(CatalogError),
    ):
        read_catalog(path, revision, config_filename=CONFIG_FILENAME)


def test_catalog_leaves_out_a_readme_too_large_to_read(fetched):
    path, revision = fetched

    with patch('eventum.app.repositories.catalog.MAX_README_SIZE', 1):
        catalog = read_catalog(
            path,
            revision,
            config_filename=CONFIG_FILENAME,
        )

    entry = next(e for e in catalog.entries if e.name == 'web-nginx')
    assert entry.title is None
    assert entry.summary is None


def test_catalog_clips_a_summary_that_runs_on(fetched):
    path, revision = fetched

    with patch('eventum.app.repositories.catalog.MAX_SUMMARY_LENGTH', 20):
        catalog = read_catalog(
            path,
            revision,
            config_filename=CONFIG_FILENAME,
        )

    entry = next(e for e in catalog.entries if e.name == 'web-nginx')
    assert entry.summary is not None
    assert entry.summary.endswith('...')


def test_catalog_takes_no_title_from_a_readme_without_a_heading(
    source_repo,
    tmp_path,
):
    readme = source_repo / 'generators' / 'linux-auditd' / 'README.md'
    readme.write_text('Produces audit records.\n\n- a list item\n')
    repo = Repo(str(source_repo))
    porcelain.add(repo, [str(readme)])
    porcelain.commit(
        repo,
        message=b'add a readme without a heading',
        committer=b'Tester <tester@example.com>',
        author=b'Tester <tester@example.com>',
    )
    revision = repo.head().decode()
    repo.close()

    catalog = read_catalog(
        source_repo,
        revision,
        config_filename=CONFIG_FILENAME,
    )
    entry = next(e for e in catalog.entries if e.name == 'linux-auditd')

    assert entry.title is None
    assert entry.summary == 'Produces audit records.'


def test_catalog_reads_a_generator_without_a_readme(fetched):
    path, revision = fetched

    catalog = read_catalog(path, revision, config_filename=CONFIG_FILENAME)
    entry = next(e for e in catalog.entries if e.name == 'linux-auditd')

    assert entry.title is None
    assert entry.summary is None


# --- failures of the file system and of the repository ---


def test_storage_reports_an_unwritable_file(tmp_path):
    directory = tmp_path / 'locked'
    directory.mkdir()
    file = RepositoriesFile(file_path=directory / 'repositories.yml')
    directory.chmod(0o500)

    try:
        with pytest.raises(RepositoryError) as info:
            file.write([{'name': 'packs', 'url': 'https://example.com/p'}])
    finally:
        directory.chmod(0o700)

    assert 'reason' in info.value.context


def test_storage_reports_a_file_that_is_not_utf8(tmp_path):
    path = tmp_path / 'repositories.yml'
    path.write_bytes(b'- name: \xff\xfe\n')

    with pytest.raises(RepositoryError):
        RepositoriesFile(file_path=path).read()


def test_source_of_a_project_without_one_is_none(tmp_path):
    project = tmp_path / 'project'
    project.mkdir()

    assert read_source(project) is None


def test_source_that_no_longer_parses_is_none(tmp_path):
    project = tmp_path / 'project'
    project.mkdir()
    (project / SOURCE_FILENAME).write_text('- not: a mapping\n')

    assert read_source(project) is None


def test_source_reports_a_project_that_cannot_be_written(tmp_path):
    project = tmp_path / 'project'
    project.mkdir()
    project.chmod(0o500)

    try:
        with pytest.raises(RepositoryError):
            write_source(project, SOURCE)
    finally:
        project.chmod(0o700)


def test_catalog_reports_a_directory_that_is_not_a_repository(tmp_path):
    with pytest.raises(CatalogError):
        read_catalog(
            tmp_path / 'absent',
            '0' * 40,
            config_filename=CONFIG_FILENAME,
        )


def test_catalog_reports_a_revision_the_repository_lacks(fetched):
    path, _ = fetched

    with pytest.raises(CatalogError):
        read_catalog(path, 'a' * 40, config_filename=CONFIG_FILENAME)


def test_install_refuses_a_generator_with_too_many_files(fetched, tmp_path):
    path, revision = fetched

    with (
        patch('eventum.app.repositories.installing.MAX_ARCHIVE_ENTRIES', 1),
        pytest.raises(InstallContentError),
    ):
        install_entry(
            repo_path=path,
            revision=revision,
            entry='web-nginx',
            generators_dir=tmp_path / 'generators',
            project_name='nginx',
            config_filename=CONFIG_FILENAME,
            source=SOURCE,
        )


def test_install_refuses_a_generator_over_the_size_limit(fetched, tmp_path):
    path, revision = fetched

    with (
        patch('eventum.app.repositories.installing.MAX_UNPACKED_SIZE', 1),
        pytest.raises(InstallContentError),
    ):
        install_entry(
            repo_path=path,
            revision=revision,
            entry='web-nginx',
            generators_dir=tmp_path / 'generators',
            project_name='nginx',
            config_filename=CONFIG_FILENAME,
            source=SOURCE,
        )


def test_install_refuses_a_directory_that_is_not_a_generator(
    fetched,
    tmp_path,
):
    # A directory of the repository that holds no generator
    # configuration is not published, and cannot be installed either.
    path, revision = fetched

    with pytest.raises(InstallContentError):
        install_entry(
            repo_path=path,
            revision=revision,
            entry='not-a-generator',
            generators_dir=tmp_path / 'generators',
            project_name='notes',
            config_filename=CONFIG_FILENAME,
            source=SOURCE,
        )


def test_install_reports_an_unwritable_workspace(fetched, tmp_path):
    path, revision = fetched
    generators_dir = tmp_path / 'generators'
    generators_dir.mkdir()
    generators_dir.chmod(0o500)

    try:
        with pytest.raises(InstallError):
            install_entry(
                repo_path=path,
                revision=revision,
                entry='web-nginx',
                generators_dir=generators_dir,
                project_name='nginx',
                config_filename=CONFIG_FILENAME,
                source=SOURCE,
            )
    finally:
        generators_dir.chmod(0o700)


def test_service_refuses_to_fetch_once_closed(service, repository):
    service.add(repository, verify=False)
    service.close()

    with pytest.raises(RepositoryError):
        service.get_catalog('packs')


def test_service_reports_an_entry_the_catalog_lacks(service, repository):
    service.add(repository)
    service.get_catalog('packs')

    with pytest.raises(CatalogEntryNotFoundError):
        service.install('packs', 'absent', 'nginx')


def test_service_marks_a_repository_that_stopped_answering(service, git_url):
    service.add(Repository(name='packs', url=git_url, ref='master'))
    service.get_catalog('packs')

    # The remote is gone by the time the catalog is read again.
    service._fetch_timeout = 5.0  # noqa: SLF001
    broken = Repository(name='packs', url='http://127.0.0.1:1/p.git')
    service._write((broken,))  # noqa: SLF001

    with pytest.raises(RepositoryFetchError):
        service.refresh('packs')

    assert service.get_all_with_status()[0].status.state == 'unavailable'


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


def test_catalog_follows_the_repository_it_reads(
    service, repository, source_repo
):
    service.add(repository)
    before = service.get_catalog('packs')

    # A generator added to the repository after the catalog was read
    # appears once the catalog is read again, and not before.
    added = source_repo / 'generators' / 'windows-security'
    added.mkdir()
    (added / CONFIG_FILENAME).write_text('input: []\n')
    repo = Repo(str(source_repo))
    porcelain.add(repo, [str(added / CONFIG_FILENAME)])
    porcelain.commit(
        repo,
        message=b'add a generator',
        committer=b'Tester <tester@example.com>',
        author=b'Tester <tester@example.com>',
    )
    repo.close()

    assert 'windows-security' not in [e.name for e in before.entries]

    after = service.refresh('packs')

    assert 'windows-security' in [e.name for e in after.entries]
    assert after.revision != before.revision


def test_catalog_marks_a_generator_the_repository_changed(
    service,
    repository,
    source_repo,
):
    service.add(repository)
    service.install('packs', 'web-nginx', 'nginx')

    changed = source_repo / 'generators' / 'web-nginx' / 'templates'
    (changed / 'event.jinja').write_text('{{ timestamp }} changed')
    repo = Repo(str(source_repo))
    porcelain.add(repo, [str(changed / 'event.jinja')])
    porcelain.commit(
        repo,
        message=b'change the generator',
        committer=b'Tester <tester@example.com>',
        author=b'Tester <tester@example.com>',
    )
    repo.close()

    catalog = service.refresh('packs')
    entry = next(e for e in catalog.entries if e.name == 'web-nginx')

    assert [item.outdated for item in entry.installed_as] == [True]


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
    cache_dir = service._cache_dir  # noqa: SLF001

    service.close()

    assert cache_dir is not None
    assert not cache_dir.exists()


# --- checking and duplicates ---


def test_service_verifies_a_repository_before_connecting(service):
    repository = Repository(name='packs', url='http://127.0.0.1:1/p.git')

    with pytest.raises(RepositoryFetchError):
        service.add(repository)

    assert service.get_all().root == ()


def test_service_connects_a_reachable_repository(service, repository):
    service.add(repository)

    assert service.get_all().root == (repository,)


def test_service_rejects_the_same_remote_at_the_same_ref(service):
    service.add(
        Repository(name='packs', url='https://example.com/p.git'),
        verify=False,
    )

    with pytest.raises(RepositoryConflictError):
        service.add(
            Repository(name='other', url='https://example.com/p/'),
            verify=False,
        )


def test_service_accepts_the_same_remote_at_another_ref(service):
    service.add(
        Repository(name='stable', url='https://example.com/p.git', ref='v1'),
        verify=False,
    )
    service.add(
        Repository(name='main', url='https://example.com/p.git', ref='main'),
        verify=False,
    )

    assert len(service.get_all().root) == 2


def test_service_reports_status_of_a_checked_repository(service, repository):
    service.add(repository)

    status = service.check('packs')

    assert status.state == 'available'
    assert status.checked_at is not None
    assert service.get_all_with_status()[0].status.state == 'available'


def test_service_reports_an_unreachable_repository(service):
    service.add(
        Repository(name='packs', url='http://127.0.0.1:1/p.git'),
        verify=False,
    )

    status = service.check('packs')

    assert status.state == 'unavailable'
    assert status.reason


def test_service_reports_unknown_status_until_checked(service):
    service.add(
        Repository(name='packs', url='https://example.com/p.git'),
        verify=False,
    )

    assert service.get_all_with_status()[0].status.state == 'unknown'


def test_service_hides_a_carried_password_in_the_listing(service, tmp_path):
    service.add(
        Repository(
            name='packs',
            url='https://example.com/p.git',
            password='ghp_token',
        ),
        verify=False,
    )

    listed = service.get_all_with_status()[0]

    assert listed.password == REDACTED_PASSWORD
    # The credential itself stays where the repository is kept, or the
    # next fetch would authenticate with the redaction.
    assert 'ghp_token' in (tmp_path / 'repositories.yml').read_text()
    assert service.get_all().root[0].password == 'ghp_token'


def test_service_shows_a_referenced_password_in_the_listing(service):
    service.add(
        Repository(
            name='packs',
            url='https://example.com/p.git',
            password='${secrets.git_token}',
        ),
        verify=False,
    )

    assert service.get_all_with_status()[0].password == '${secrets.git_token}'


def test_service_resolves_a_referenced_password(service, tmp_path):
    SECURITY_SETTINGS['cryptfile_location'] = tmp_path / 'keyring.cfg'
    repository = Repository(
        name='packs',
        url='https://example.com/p.git',
        password='${secrets.git_token}',
    )

    try:
        set_secret('git_token', 'ghp_token')

        assert service._resolve_password(repository) == 'ghp_token'
    finally:
        SECURITY_SETTINGS['cryptfile_location'] = None


def test_service_takes_a_carried_password_as_written(service, tmp_path):
    # An empty keyring is enough: a password that refers to nothing is
    # never looked up.
    SECURITY_SETTINGS['cryptfile_location'] = tmp_path / 'keyring.cfg'
    repository = Repository(
        name='packs',
        url='https://example.com/p.git',
        password='ghp_token',
    )

    try:
        assert service._resolve_password(repository) == 'ghp_token'
    finally:
        SECURITY_SETTINGS['cryptfile_location'] = None


def test_service_authenticates_with_the_resolved_password(
    service,
    credentials_url,
    tmp_path,
):
    # What the remote receives is the point of the resolution, and the
    # only place it can be observed is the request itself.
    url, seen = credentials_url
    SECURITY_SETTINGS['cryptfile_location'] = tmp_path / 'keyring.cfg'

    try:
        set_secret('git_token', 'ghp_token')
        service.add(
            Repository(
                name='packs',
                url=url,
                username='eventum',
                password='${secrets.git_token}',
            ),
            verify=False,
        )

        with pytest.raises(RepositoryFetchError):
            service.get_catalog('packs')
    finally:
        SECURITY_SETTINGS['cryptfile_location'] = None

    assert seen
    scheme, _, encoded = seen[0].partition(' ')
    assert scheme == 'Basic'
    assert base64.b64decode(encoded).decode() == 'eventum:ghp_token'


def test_service_authenticates_with_a_password_written_in_place(
    service,
    credentials_url,
):
    url, seen = credentials_url
    service.add(
        Repository(
            name='packs',
            url=url,
            username='eventum',
            password='ghp_token',
        ),
        verify=False,
    )

    with pytest.raises(RepositoryFetchError):
        service.get_catalog('packs')

    assert seen
    _, _, encoded = seen[0].partition(' ')
    assert base64.b64decode(encoded).decode() == 'eventum:ghp_token'


def test_service_hides_a_rejected_password_of_the_file(service, tmp_path):
    # A rejected value is quoted back in the reason, and the reason
    # travels to whoever asked.
    (tmp_path / 'repositories.yml').write_text(
        '- name: packs\n'
        '  url: https://example.com/p.git\n'
        '  password: "ghp_token${params.leak}"\n',
    )

    with pytest.raises(RepositoryError) as info:
        service.get_all()

    assert 'ghp_token' not in info.value.context['reason']
    assert 'password' in info.value.context['reason']


def test_service_hides_a_password_of_an_entry_rejected_as_a_whole(
    service,
    tmp_path,
):
    # A field reported as missing quotes the whole entry back, so the
    # password of an entry rejected for another reason travels too.
    (tmp_path / 'repositories.yml').write_text(
        '- url: https://example.com/p.git\n  password: ghp_token\n',
    )

    with pytest.raises(RepositoryError) as info:
        service.get_all()

    assert 'ghp_token' not in info.value.context['reason']


def test_service_names_no_secret_of_a_composed_password(service, tmp_path):
    # A password that only holds a reference among other text refers
    # to no single secret, so nothing of it is named in the failure.
    SECURITY_SETTINGS['cryptfile_location'] = tmp_path / 'keyring.cfg'
    repository = Repository(
        name='packs',
        url='https://example.com/p.git',
        password='prefix-${secrets.git_token}',
    )

    try:
        with pytest.raises(RepositorySecretError) as info:
            service._resolve_password(repository)
    finally:
        SECURITY_SETTINGS['cryptfile_location'] = None

    assert 'secret' not in info.value.context
    assert 'prefix-' not in str(info.value.context)


def test_service_names_the_missing_secret_of_a_password(service, tmp_path):
    SECURITY_SETTINGS['cryptfile_location'] = tmp_path / 'keyring.cfg'
    repository = Repository(
        name='packs',
        url='https://example.com/p.git',
        password='${secrets.git_token}',
    )

    try:
        with pytest.raises(RepositorySecretError) as info:
            service._resolve_password(repository)
    finally:
        SECURITY_SETTINGS['cryptfile_location'] = None

    assert info.value.context['secret'] == 'git_token'
    assert 'ghp' not in str(info.value.context)


# --- origin of an installed project ---


def test_install_records_the_origin(service, repository, tmp_path):
    service.add(repository)

    service.install('packs', 'web-nginx', 'nginx')

    source = read_source(tmp_path / 'generators' / 'nginx')
    assert source is not None
    assert source.repository == 'packs'
    assert source.entry == 'web-nginx'
    assert source.url == repository.url
    assert len(source.tree) == 40


def test_catalog_marks_an_installed_generator(service, repository):
    service.add(repository)
    service.install('packs', 'web-nginx', 'nginx')

    catalog = service.get_catalog('packs')
    entry = next(e for e in catalog.entries if e.name == 'web-nginx')

    assert [item.project for item in entry.installed_as] == ['nginx']
    assert not entry.installed_as[0].outdated


def test_catalog_marks_an_outdated_project(service, repository, tmp_path):
    service.add(repository)
    service.install('packs', 'web-nginx', 'nginx')

    project = tmp_path / 'generators' / 'nginx'
    source = (project / SOURCE_FILENAME).read_text()
    (project / SOURCE_FILENAME).write_text(
        source.replace(read_source(project).tree, 'a' * 40),
    )

    catalog = service.get_catalog('packs')
    entry = next(e for e in catalog.entries if e.name == 'web-nginx')

    assert entry.installed_as[0].outdated


def test_catalog_recognizes_a_renamed_project(service, repository, tmp_path):
    service.add(repository)
    service.install('packs', 'web-nginx', 'nginx')
    (tmp_path / 'generators' / 'nginx').rename(
        tmp_path / 'generators' / 'renamed',
    )

    catalog = service.get_catalog('packs')
    entry = next(e for e in catalog.entries if e.name == 'web-nginx')

    assert [item.project for item in entry.installed_as] == ['renamed']


def test_catalog_ignores_a_project_that_only_shares_a_name(
    service,
    repository,
    tmp_path,
):
    service.add(repository)
    project = tmp_path / 'generators' / 'web-nginx'
    project.mkdir(parents=True)
    (project / CONFIG_FILENAME).write_text('input: []\n')

    catalog = service.get_catalog('packs')
    entry = next(e for e in catalog.entries if e.name == 'web-nginx')

    assert entry.installed_as == ()


def test_catalog_ignores_an_origin_of_another_repository(
    service,
    repository,
    tmp_path,
):
    service.add(repository)
    service.install('packs', 'web-nginx', 'nginx')
    project = tmp_path / 'generators' / 'nginx'
    (project / SOURCE_FILENAME).write_text(
        (project / SOURCE_FILENAME)
        .read_text()
        .replace(repository.url, 'https://elsewhere.example.com/packs.git'),
    )

    catalog = service.get_catalog('packs')
    entry = next(e for e in catalog.entries if e.name == 'web-nginx')

    assert entry.installed_as == ()


def test_service_reports_missing_secret(service, git_url, tmp_path):
    # The keyring of the machine running the tests is not the one
    # under test: an empty file of its own is.
    SECURITY_SETTINGS['cryptfile_location'] = tmp_path / 'keyring.cfg'
    service.add(
        Repository(
            name='packs',
            url=git_url,
            password='${secrets.absent-secret}',
        ),
        verify=False,
    )

    try:
        with pytest.raises(RepositorySecretError):
            service.get_catalog('packs')
    finally:
        SECURITY_SETTINGS['cryptfile_location'] = None
