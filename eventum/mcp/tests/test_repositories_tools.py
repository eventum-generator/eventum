"""Tests for the connected repository tools."""

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock

import anyio
import pytest

from eventum.app.repositories import (
    Catalog,
    CatalogEntry,
    CatalogEntryNotFoundError,
    InstallConflictError,
    InstalledProject,
    Repositories,
    Repository,
    RepositoryError,
    RepositoryFetchError,
    RepositoryNotFoundError,
    RepositorySecretError,
)
from eventum.mcp.context import AuthoringContext, FileAuthoringContext
from eventum.mcp.errors import ToolFailure
from eventum.mcp.server import build_server
from eventum.mcp.tools.repositories import (
    get_repository_catalog,
    install_generator,
    list_repositories,
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
            installed_as=(
                InstalledProject(
                    project='nginx',
                    revision='0' * 40,
                    installed_at=datetime(2026, 1, 1, tzinfo=UTC),
                    outdated=True,
                ),
            ),
        ),
    ],
)


@dataclass(frozen=True)
class _StubContext:
    """Authoring context serving an injected repositories service."""

    generators_dir: Path
    read_only: bool
    repositories: Repositories
    config_filename: str = 'generator.yml'

    def is_live_managed(self, generator_id: str) -> bool:  # noqa: ARG002
        return False


@pytest.fixture
def stub() -> Mock:
    """Return a repositories service that answers what a test sets."""
    return Mock(spec=Repositories)


@pytest.fixture
def ctx(tmp_path: Path, stub: Mock) -> _StubContext:
    """Return a writable context serving the stub service."""
    return _StubContext(
        generators_dir=tmp_path / 'generators',
        read_only=False,
        repositories=stub,
    )


def _file_ctx(tmp_path: Path) -> FileAuthoringContext:
    """Return a context serving a real, file-backed service."""
    return FileAuthoringContext(
        generators_dir=tmp_path / 'generators',
        read_only=False,
        repositories_file=tmp_path / 'repositories.yml',
    )


# --- listing ---


async def test_list_is_empty_without_a_file(tmp_path: Path) -> None:
    """An instance that connected nothing lists no repositories."""
    assert await list_repositories(_file_ctx(tmp_path)) == []


async def test_list_reports_connected_repositories(tmp_path: Path) -> None:
    """A connected repository is listed with its unchecked status."""
    context = _file_ctx(tmp_path)
    context.repositories.add(
        Repository(
            name='packs',
            url='https://example.com/packs.git',
            username='eventum',
            secret='packs_token',
        ),
        verify=False,
    )

    listed = await list_repositories(context)

    assert listed == [
        {
            'name': 'packs',
            'url': 'https://example.com/packs.git',
            'ref': None,
            'username': 'eventum',
            'secret': 'packs_token',
            'status': {
                'state': 'unknown',
                'checked_at': None,
                'reason': None,
            },
        },
    ]


async def test_list_fails_on_unreadable_file(
    ctx: _StubContext,
    stub: Mock,
) -> None:
    """A list that cannot be read is reported as a failure."""
    stub.get_all_with_status.side_effect = RepositoryError(
        'Failed to read the repositories file',
        context={'file_path': '/abs/repositories.yml', 'reason': 'broken'},
    )

    result = await list_repositories(ctx)

    assert isinstance(result, ToolFailure)
    assert result.error == 'Failed to read the repositories file'
    assert result.details['reason'] == 'broken'
    assert result.details['file_path'] == 'repositories.yml'


# --- catalog ---


async def test_catalog_reports_published_generators(
    ctx: _StubContext,
    stub: Mock,
) -> None:
    """The catalog names the repository, the commit and the entries."""
    stub.get_catalog.return_value = CATALOG

    result = await get_repository_catalog(ctx, 'packs')

    assert not isinstance(result, ToolFailure)
    assert result['repository'] == 'packs'
    assert result['revision'] == '0' * 40
    assert result['author'] == 'Tester'
    assert [entry['name'] for entry in result['entries']] == ['web-nginx']
    assert result['entries'][0]['installed_as'] == [
        {
            'project': 'nginx',
            'revision': '0' * 40,
            'installed_at': '2026-01-01T00:00:00Z',
            'outdated': True,
        },
    ]
    stub.get_catalog.assert_called_once_with('packs')


async def test_catalog_hides_the_content_hash(
    ctx: _StubContext,
    stub: Mock,
) -> None:
    """The content hash of an entry stays inside the service."""
    stub.get_catalog.return_value = CATALOG

    result = await get_repository_catalog(ctx, 'packs')

    assert not isinstance(result, ToolFailure)
    assert 'tree' not in result['entries'][0]


async def test_catalog_refresh_fetches_anew(
    ctx: _StubContext,
    stub: Mock,
) -> None:
    """A refresh reads the repository instead of what was read before."""
    stub.refresh.return_value = CATALOG

    result = await get_repository_catalog(ctx, 'packs', refresh=True)

    assert not isinstance(result, ToolFailure)
    stub.refresh.assert_called_once_with('packs')
    stub.get_catalog.assert_not_called()


async def test_catalog_of_unconnected_repository_fails(
    ctx: _StubContext,
    stub: Mock,
) -> None:
    """A repository that is not connected is reported by name."""
    stub.get_catalog.side_effect = RepositoryNotFoundError(
        'Repository with this name is not connected',
        context={'name': 'other'},
    )

    result = await get_repository_catalog(ctx, 'other')

    assert isinstance(result, ToolFailure)
    assert result.details == {'name': 'other'}


async def test_catalog_failure_carries_the_hint_but_not_the_url(
    ctx: _StubContext,
    stub: Mock,
) -> None:
    """A fetch failure forwards what to act on and nothing else."""
    stub.get_catalog.side_effect = RepositoryFetchError(
        'Failed to fetch the repository',
        context={
            'name': 'packs',
            'url': 'https://user@example.com/packs.git',
            'reason': 'unexpected http resp 401',
            'hint': 'Repository requires credentials',
        },
    )

    result = await get_repository_catalog(ctx, 'packs')

    assert isinstance(result, ToolFailure)
    assert result.details == {
        'name': 'packs',
        'reason': 'unexpected http resp 401',
        'hint': 'Repository requires credentials',
    }


# --- installing ---


async def test_install_writes_the_project(
    ctx: _StubContext,
    stub: Mock,
) -> None:
    """An installed generator is reported with its file count."""
    stub.install.return_value = 7

    result = await install_generator(ctx, 'packs', 'web-nginx', 'nginx')

    assert result == {'installed': 'nginx', 'files': 7}
    stub.install.assert_called_once_with('packs', 'web-nginx', 'nginx')


async def test_install_is_refused_on_a_read_only_server(
    tmp_path: Path,
    stub: Mock,
) -> None:
    """A read-only server writes nothing and says so."""
    context = _StubContext(
        generators_dir=tmp_path / 'generators',
        read_only=True,
        repositories=stub,
    )

    result = await install_generator(context, 'packs', 'web-nginx', 'nginx')

    assert isinstance(result, ToolFailure)
    assert result.error == 'Server is read-only; writes are disabled'
    assert result.details == {'name': 'nginx'}
    stub.install.assert_not_called()


async def test_install_into_a_taken_name_fails(
    ctx: _StubContext,
    stub: Mock,
) -> None:
    """An existing project is never overwritten."""
    stub.install.side_effect = InstallConflictError(
        'Generator directory already exists',
        context={'name': 'nginx'},
    )

    result = await install_generator(ctx, 'packs', 'web-nginx', 'nginx')

    assert isinstance(result, ToolFailure)
    assert result.error == 'Generator directory already exists'
    assert result.details == {'name': 'nginx'}


async def test_install_of_an_unpublished_generator_fails(
    ctx: _StubContext,
    stub: Mock,
) -> None:
    """A generator the repository does not publish is reported."""
    stub.install.side_effect = CatalogEntryNotFoundError(
        'Repository publishes no such generator',
        context={'name': 'web-apache'},
    )

    result = await install_generator(ctx, 'packs', 'web-apache', 'apache')

    assert isinstance(result, ToolFailure)
    assert result.details == {'name': 'web-apache'}


async def test_install_without_the_secret_fails(
    ctx: _StubContext,
    stub: Mock,
) -> None:
    """A missing keyring secret is reported with what to do about it."""
    stub.install.side_effect = RepositorySecretError(
        'Failed to read the secret of the repository',
        context={
            'name': 'packs',
            'value': 'packs_token',
            'reason': 'no such secret',
            'hint': 'Add the secret using the eventum-keyring CLI',
        },
    )

    result = await install_generator(ctx, 'packs', 'web-nginx', 'nginx')

    assert isinstance(result, ToolFailure)
    assert result.details['value'] == 'packs_token'
    assert result.details['hint'] == (
        'Add the secret using the eventum-keyring CLI'
    )


# --- context and registration ---


def test_stdio_context_keeps_the_list_next_to_the_generators(
    tmp_path: Path,
) -> None:
    """The stdio context reads the file an instance keeps."""
    (tmp_path / 'generators').mkdir()
    (tmp_path / 'repositories.yml').write_text(
        '- name: packs\n  url: https://example.com/packs.git\n',
    )
    context = FileAuthoringContext(
        generators_dir=tmp_path / 'generators',
        read_only=True,
    )

    listed = context.repositories.get_all()

    assert [repository.name for repository in listed.root] == ['packs']


def test_registered_tools_hide_the_context(tmp_path: Path) -> None:
    """The injected context is no part of the agent-facing schema."""
    context: AuthoringContext = _file_ctx(tmp_path)
    server = build_server(context, transport='stdio')

    tools = {tool.name: tool for tool in anyio.run(server.list_tools)}

    for name in (
        'list_repositories',
        'get_repository_catalog',
        'install_generator',
    ):
        assert 'context' not in tools[name].inputSchema.get('properties', {})

    catalog_properties = tools['get_repository_catalog'].inputSchema[
        'properties'
    ]
    assert set(catalog_properties) == {'name', 'refresh'}
    assert set(tools['install_generator'].inputSchema['properties']) == {
        'repository',
        'generator',
        'name',
    }
