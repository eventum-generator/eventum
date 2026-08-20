"""Tests for the transport-neutral operations over secrets."""

from pathlib import Path
from unittest.mock import patch

import pytest

from eventum.app import secrets as secrets_module
from eventum.app.renaming import (
    RenameConflictError,
    RenameError,
    RenameNotFoundError,
)
from eventum.app.repositories import (
    Repositories,
    Repository,
    RepositoryError,
)
from eventum.app.secrets import find_secret_references, rename_secret
from eventum.security.manage import (
    SECURITY_SETTINGS,
    get_secret,
    list_secrets,
    set_secret,
)

_CONFIG_FILENAME = Path('generator.yml')


@pytest.fixture
def generators_dir(tmp_path: Path) -> Path:
    path = tmp_path / 'generators'
    path.mkdir()
    return path


@pytest.fixture
def repositories(tmp_path: Path, generators_dir: Path):
    service = Repositories(
        file_path=tmp_path / 'repositories.yml',
        generators_dir=generators_dir,
        config_filename=str(_CONFIG_FILENAME),
    )
    yield service
    service.close()


@pytest.fixture
def keyring(tmp_path: Path):
    """Point the keyring at a file of its own for the test.

    The keyring of the machine running the tests is not the one under
    test.
    """
    SECURITY_SETTINGS['cryptfile_location'] = tmp_path / 'keyring.cfg'
    yield
    SECURITY_SETTINGS['cryptfile_location'] = None


def _write_config(generators_dir: Path, name: str, content: str) -> None:
    """Create a project directory holding the given config content."""
    config_path = generators_dir / name / _CONFIG_FILENAME
    config_path.parent.mkdir(parents=True)
    config_path.write_text(content)


def _connect(
    repositories: Repositories,
    name: str,
    secret: str | None,
) -> None:
    """Connect a repository authenticating with the given secret."""
    repositories.add(
        Repository(
            name=name,
            url=f'https://git.example.com/{name}.git',
            username='eventum',
            secret=secret,
        ),
        verify=False,
    )


def _references(
    generators_dir: Path,
    repositories: Repositories,
    secret: str,
):
    return find_secret_references(
        generators_dir=generators_dir,
        config_filename=_CONFIG_FILENAME,
        repositories=repositories,
        secret=secret,
    )


# --- project references ---


def test_matches_referencing_projects(generators_dir, repositories):
    _write_config(generators_dir, 'gen-a', 'token: ${secrets.api_key}\n')
    _write_config(generators_dir, 'gen-b', 'token: ${ secrets.api_key }\n')
    _write_config(generators_dir, 'gen-c', 'token: ${secrets.other}\n')
    _write_config(generators_dir, 'gen-d', 'host: ${params.host}\n')

    references = _references(generators_dir, repositories, 'api_key')

    assert references.projects == ['gen-a', 'gen-b']


def test_ignores_dirs_without_config(generators_dir, repositories):
    (generators_dir / 'not-a-generator').mkdir()
    (generators_dir / 'not-a-generator' / 'other.yml').write_text(
        'token: ${secrets.api_key}\n',
    )

    references = _references(generators_dir, repositories, 'api_key')

    assert references.projects == []


def test_skips_unreadable_config(generators_dir, repositories):
    _write_config(generators_dir, 'gen-a', 'token: ${secrets.api_key}\n')
    (generators_dir / 'gen-b').mkdir()
    (generators_dir / 'gen-b' / _CONFIG_FILENAME).write_bytes(
        b'\xff\xfe\x00',
    )

    references = _references(generators_dir, repositories, 'api_key')

    assert references.projects == ['gen-a']


def test_missing_generators_dir_reports_no_project(tmp_path, repositories):
    references = _references(tmp_path / 'absent', repositories, 'api_key')

    assert references.projects == []


# --- repository references ---


def test_reports_repositories_holding_the_secret(
    generators_dir,
    repositories,
):
    _connect(repositories, 'internal', 'git_token')
    _connect(repositories, 'mirror', 'git_token')
    _connect(repositories, 'other', 'another_token')
    _connect(repositories, 'public', None)

    references = _references(generators_dir, repositories, 'git_token')

    assert references.repositories == ['internal', 'mirror']


def test_keeps_the_two_kinds_apart(generators_dir, repositories):
    _write_config(generators_dir, 'web-nginx', 'token: ${secrets.git_token}\n')
    _connect(repositories, 'internal', 'git_token')

    references = _references(generators_dir, repositories, 'git_token')

    assert references.projects == ['web-nginx']
    assert references.repositories == ['internal']


def test_unreadable_repositories_are_not_reported_as_none(
    generators_dir,
    repositories,
    tmp_path,
):
    (tmp_path / 'repositories.yml').write_text('name: not-a-list\n')

    with pytest.raises(RepositoryError):
        _references(generators_dir, repositories, 'git_token')


# --- renaming ---


def test_rename_repoints_the_repositories_using_the_secret(
    repositories,
    keyring,
):
    set_secret('git_token', 'value')
    _connect(repositories, 'internal', 'git_token')
    _connect(repositories, 'mirror', 'git_token')
    _connect(repositories, 'other', 'another_token')

    repointed = rename_secret(
        repositories=repositories,
        name='git_token',
        new_name='forge_token',
    )

    assert repointed == ['internal', 'mirror']
    assert repositories.get('internal').secret == 'forge_token'
    assert repositories.get('mirror').secret == 'forge_token'
    assert repositories.get('other').secret == 'another_token'


def test_rename_keeps_the_value_under_the_new_name(repositories, keyring):
    set_secret('git_token', 'value')
    _connect(repositories, 'internal', 'git_token')

    rename_secret(
        repositories=repositories,
        name='git_token',
        new_name='forge_token',
    )

    assert list_secrets() == ['forge_token']
    assert get_secret('forge_token') == 'value'


def test_rename_reports_nothing_when_no_repository_uses_it(
    repositories,
    keyring,
):
    set_secret('git_token', 'value')

    assert (
        rename_secret(
            repositories=repositories,
            name='git_token',
            new_name='forge_token',
        )
        == []
    )


def test_rename_missing_secret_is_not_found(repositories, keyring):
    with pytest.raises(RenameNotFoundError):
        rename_secret(
            repositories=repositories,
            name='absent',
            new_name='forge_token',
        )


def test_rename_to_taken_name_conflicts(repositories, keyring):
    set_secret('git_token', 'value')
    set_secret('forge_token', 'other')

    with pytest.raises(RenameConflictError):
        rename_secret(
            repositories=repositories,
            name='git_token',
            new_name='forge_token',
        )


def test_rename_moves_the_value_back_when_repointing_fails(
    repositories,
    keyring,
):
    set_secret('git_token', 'value')
    _connect(repositories, 'internal', 'git_token')

    with (
        patch.object(
            Repositories,
            'repoint_secret',
            side_effect=RepositoryError('broken', context={}),
        ),
        pytest.raises(RenameError, match='cannot be repointed'),
    ):
        rename_secret(
            repositories=repositories,
            name='git_token',
            new_name='forge_token',
        )

    assert list_secrets() == ['git_token']
    assert get_secret('git_token') == 'value'
    assert repositories.get('internal').secret == 'git_token'


def test_rename_to_a_name_no_repository_can_hold_is_refused(
    repositories,
    keyring,
):
    set_secret('git_token', 'value')
    _connect(repositories, 'internal', 'git_token')

    with pytest.raises(RenameError, match='cannot be repointed'):
        rename_secret(
            repositories=repositories,
            name='git_token',
            new_name='x' * 256,
        )

    assert list_secrets() == ['git_token']
    assert repositories.get('internal').secret == 'git_token'


def test_rename_reports_a_revert_that_fails_too(repositories, keyring):
    _connect(repositories, 'internal', 'git_token')

    with (
        patch.object(
            Repositories,
            'repoint_secret',
            side_effect=RepositoryError('broken', context={}),
        ),
        patch(
            'eventum.app.secrets.rename_keyring_secret',
            side_effect=[None, OSError('keyring is gone')],
        ),
        pytest.raises(RenameError, match='still hold the old name'),
    ):
        rename_secret(
            repositories=repositories,
            name='git_token',
            new_name='forge_token',
        )


def test_rename_reports_a_keyring_that_cannot_be_reached(
    repositories,
    keyring,
):
    with (
        patch(
            'eventum.app.secrets.rename_keyring_secret',
            side_effect=OSError('keyring is gone'),
        ),
        pytest.raises(RenameError, match='Failed to rename secret'),
    ):
        rename_secret(
            repositories=repositories,
            name='git_token',
            new_name='forge_token',
        )


def test_rename_holds_its_turn_across_both_steps(repositories, keyring):
    """No second rename can start while one is between its two steps."""
    set_secret('git_token', 'value')
    _connect(repositories, 'internal', 'git_token')
    free_while_repointing: list[bool] = []

    def _repoint(self, secret: str, new_name: str) -> list[str]:  # noqa: ANN001, ARG001
        acquired = secrets_module._RENAME_LOCK.acquire(blocking=False)
        free_while_repointing.append(acquired)
        if acquired:
            secrets_module._RENAME_LOCK.release()
        return []

    with patch.object(Repositories, 'repoint_secret', _repoint):
        rename_secret(
            repositories=repositories,
            name='git_token',
            new_name='forge_token',
        )

    assert free_while_repointing == [False]


def test_rename_onto_a_name_a_repository_holds_conflicts(
    repositories,
    keyring,
):
    """The value must not move under a name another repository holds."""
    set_secret('gl_token', 'GITLAB-TOKEN')
    _connect(repositories, 'gitlab', 'gl_token')
    _connect(repositories, 'github', 'gh_token')

    with pytest.raises(RenameConflictError, match='already authenticate'):
        rename_secret(
            repositories=repositories,
            name='gl_token',
            new_name='gh_token',
        )

    assert list_secrets() == ['gl_token']
    assert get_secret('gl_token') == 'GITLAB-TOKEN'
    assert repositories.get('gitlab').secret == 'gl_token'
    assert repositories.get('github').secret == 'gh_token'


def test_rename_conflict_names_the_repositories_holding_it(
    repositories,
    keyring,
):
    set_secret('gl_token', 'value')
    _connect(repositories, 'gitlab', 'gl_token')
    _connect(repositories, 'mirror', 'gh_token')
    _connect(repositories, 'github', 'gh_token')

    with pytest.raises(RenameConflictError) as info:
        rename_secret(
            repositories=repositories,
            name='gl_token',
            new_name='gh_token',
        )

    assert info.value.context['reason'] == 'github, mirror'


def test_rename_to_the_same_name_reports_the_secret_not_the_repository(
    repositories,
    keyring,
):
    """The keyring answers this one, and names the right holder."""
    set_secret('git_token', 'value')
    _connect(repositories, 'internal', 'git_token')

    with pytest.raises(RenameConflictError, match='already exists'):
        rename_secret(
            repositories=repositories,
            name='git_token',
            new_name='git_token',
        )


def test_rename_stops_when_the_repositories_cannot_be_read(
    repositories,
    keyring,
    tmp_path,
):
    set_secret('git_token', 'value')
    (tmp_path / 'repositories.yml').write_text('name: not-a-list\n')

    with pytest.raises(RenameError, match='Cannot tell which repositories'):
        rename_secret(
            repositories=repositories,
            name='git_token',
            new_name='forge_token',
        )

    assert list_secrets() == ['git_token']
