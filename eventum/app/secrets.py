"""Transport-neutral operations over the secrets of the keyring.

A secret is referred to from two places at once - the configuration of
a project, as a `${secrets.<name>}` token, and the secret field of a
connected repository. Both kinds are answered here, so what a rename or
a removal would reach is known in one place, and renaming carries both
of them over to the new name.
"""

import threading
from pathlib import Path
from typing import NamedTuple

from eventum.app.renaming import (
    RenameConflictError,
    RenameError,
    RenameNotFoundError,
)
from eventum.app.repositories import Repositories, RepositoryError
from eventum.app.workspace import WorkspaceError, write_text
from eventum.core.config_loader import TOKEN_PATTERN, extract_secrets
from eventum.security.manage import SecretConflictError, SecretNotFoundError
from eventum.security.manage import rename_secret as rename_keyring_secret

# A rename moves a keyring entry and then rewrites the repositories
# holding it, and the two are locked separately - the keyring not at
# all. Two renames interleaving between those steps leave a repository
# holding a name whose value the other rename has already moved on, so
# every rename in this process takes its turn.
_RENAME_LOCK = threading.Lock()


class SecretReferences(NamedTuple):
    """Referrers of a secret, grouped by their kind.

    The two kinds differ in what a rename does to them, so they are
    kept apart rather than merged into one list of names.

    Attributes
    ----------
    projects : list[str]
        Names of the project directories whose configuration carries a
        `${secrets.<name>}` token for the secret.

    repositories : list[str]
        Names of the connected repositories authenticating with the
        secret.

    """

    projects: list[str]
    repositories: list[str]


class UpdatedReferences(NamedTuple):
    """Referrers a rename carried over to the new name, by kind.

    Attributes
    ----------
    projects : list[str]
        Names of the project directories whose configuration was
        rewritten.

    repositories : list[str]
        Names of the connected repositories that were repointed.

    """

    projects: list[str]
    repositories: list[str]


class _Rewrite(NamedTuple):
    """One configuration file, as it is and as it is to become."""

    path: Path
    project: str
    before: str
    after: str


def find_secret_references(
    *,
    generators_dir: Path,
    config_filename: Path,
    repositories: Repositories,
    secret: str,
) -> SecretReferences:
    """List everything that refers to a secret.

    Parameters
    ----------
    generators_dir : Path
        Root directory that contains project directories.

    config_filename : Path
        Name of the configuration file inside a project directory.

    repositories : Repositories
        Connected repositories service.

    secret : str
        Name of the secret to look for.

    Returns
    -------
    SecretReferences
        Referrers of the secret, by kind.

    Raises
    ------
    RepositoryError
        If the connected repositories cannot be read. A secret whose
        repositories are unknown is not reported as unreferenced - that
        answer is what makes a rename look safe when it is not.

    """
    return SecretReferences(
        projects=_find_project_references(
            generators_dir,
            config_filename,
            secret,
        ),
        repositories=repositories.find_secret_users(secret),
    )


def rename_secret(
    *,
    generators_dir: Path,
    config_filename: Path,
    repositories: Repositories,
    name: str,
    new_name: str,
) -> UpdatedReferences:
    """Rename a secret and carry its referrers over to the new name.

    Every referrer follows: the `${secrets.<name>}` token of a project
    is rewritten in its configuration, and a connected repository
    authenticating with the secret is pointed at the new name. The
    value is moved in the keyring first, and whatever is written after
    it is put back when a later step fails, so the three either move
    together or not at all. Renames of this process take their turn, so
    no step of one lands inside another.

    A configuration is rewritten as text, leaving its comments and its
    formatting as they were, and the token keeps the spacing it was
    written with. A configuration that cannot be read is skipped, as it
    is skipped when the referrers are listed.

    A generator already running is unaffected: it holds the
    configuration it loaded, and the value behind the secret does not
    change. It reads the new name the next time it starts.

    Parameters
    ----------
    generators_dir : Path
        Root directory that contains project directories.

    config_filename : Path
        Name of the configuration file inside a project directory.

    repositories : Repositories
        Connected repositories service.

    name : str
        Current name of the secret.

    new_name : str
        Name to rename the secret to.

    Returns
    -------
    UpdatedReferences
        Referrers carried over to the new name, by kind.

    Raises
    ------
    RenameNotFoundError
        If the secret is missing in the keyring.

    RenameConflictError
        If a secret with the new name already exists, or a repository
        already authenticates with that name.

    RenameError
        If the connected repositories cannot be read, the keyring
        cannot be reached, or the rename fails midway.

    """
    with _RENAME_LOCK:
        _reject_held_name(repositories, name, new_name)

        rewrites = _plan_project_rewrites(
            generators_dir,
            config_filename,
            name,
            new_name,
        )

        try:
            rename_keyring_secret(name, new_name)
        except SecretNotFoundError:
            msg = 'Secret is missing'
            raise RenameNotFoundError(msg, context={'secret': name}) from None
        except SecretConflictError:
            msg = 'Secret with this name already exists'
            raise RenameConflictError(
                msg,
                context={'secret': new_name},
            ) from None
        except (ValueError, OSError) as e:
            msg = 'Failed to rename secret'
            raise RenameError(
                msg,
                context={'secret': name, 'reason': str(e)},
            ) from None

        try:
            repointed = repositories.repoint_secret(name, new_name)
        except RepositoryError as e:
            _revert_keyring_rename(name, new_name)

            msg = 'Repositories using the secret cannot be repointed'
            raise RenameError(msg, context=e.context) from None

        # A failure that could not put the configurations back raises
        # on its own, and nothing else is undone after it: the keyring
        # and the repositories stay on the new name, which is the name
        # the configurations that were rewritten now carry.
        try:
            _apply_rewrites(rewrites)
        except WorkspaceError as e:
            _revert_repoint(repositories, name, new_name)
            _revert_keyring_rename(name, new_name)

            msg = 'Configurations reading the secret cannot be rewritten'
            raise RenameError(msg, context=e.context) from None

        return UpdatedReferences(
            projects=sorted(rewrite.project for rewrite in rewrites),
            repositories=repointed,
        )


def _plan_project_rewrites(
    generators_dir: Path,
    config_filename: Path,
    name: str,
    new_name: str,
) -> list[_Rewrite]:
    """Read the configurations to rewrite and what to write in them.

    Everything is read before anything is written, so a configuration
    that cannot be read is known before the keyring is touched.
    """
    rewrites: list[_Rewrite] = []
    old_token = f'secrets.{name}'
    new_token = f'secrets.{new_name}'

    for project in _find_project_references(
        generators_dir,
        config_filename,
        name,
    ):
        path = generators_dir / project / config_filename
        try:
            before = path.read_text(encoding='utf-8')
        except OSError, UnicodeDecodeError:
            continue

        after = TOKEN_PATTERN.sub(
            lambda match: (
                match.group(0).replace(old_token, new_token)
                if match.group(1) == old_token
                else match.group(0)
            ),
            before,
        )

        if after != before:
            rewrites.append(_Rewrite(path, project, before, after))

    return rewrites


def _apply_rewrites(rewrites: list[_Rewrite]) -> None:
    """Write the planned configurations, putting back what was written.

    Raises
    ------
    WorkspaceError
        If any of them cannot be written. What was written before the
        failure is restored, and a restore that fails too is reported
        in its place.

    """
    written: list[_Rewrite] = []

    for rewrite in rewrites:
        try:
            write_text(rewrite.path, rewrite.after)
        except WorkspaceError:
            _restore_rewrites(written)
            raise

        written.append(rewrite)


def _restore_rewrites(written: list[_Rewrite]) -> None:
    """Put the configurations back as they were.

    Raises
    ------
    RenameError
        If any of them cannot be put back, which leaves the secret
        renamed in some configurations and not in others.

    """
    for rewrite in written:
        try:
            write_text(rewrite.path, rewrite.before)
        except WorkspaceError as e:
            msg = (
                'Some configurations are rewritten for the new name and '
                'cannot be put back'
            )
            raise RenameError(msg, context=e.context) from None


def _reject_held_name(
    repositories: Repositories,
    name: str,
    new_name: str,
) -> None:
    """Refuse a new name a repository already authenticates with.

    The keyring holds one value per name, so a repository left on the
    new name would start authenticating with the value moved under it -
    the credential of one host reaching another, on an operation that
    reported success. The repositories on that name are named, since
    freeing it is what the caller has to do next.

    Raises
    ------
    RenameConflictError
        If any repository already holds the new name.

    RenameError
        If the connected repositories cannot be read.

    """
    if new_name == name:
        # The keyring refuses this one on its own, and with the right
        # message: the name is taken by the secret being renamed.
        return

    try:
        holders = repositories.find_secret_users(new_name)
    except RepositoryError as e:
        msg = 'Cannot tell which repositories hold the new name'
        raise RenameError(msg, context=e.context) from None

    if holders:
        msg = 'Repositories already authenticate with the new name'
        raise RenameConflictError(
            msg,
            context={'secret': new_name, 'reason': ', '.join(holders)},
        )


def _find_project_references(
    generators_dir: Path,
    config_filename: Path,
    secret: str,
) -> list[str]:
    """List project directories whose config references a secret.

    Only project configurations are scanned, since `${secrets.*}`
    tokens are substituted in them alone. Configurations that cannot
    be read are skipped - such a generator cannot run either.
    """
    if not generators_dir.exists():
        return []

    names: list[str] = []

    for config_path in generators_dir.glob(f'*/{config_filename}'):
        try:
            content = config_path.read_text(encoding='utf-8')
        except OSError, UnicodeDecodeError:
            continue

        if secret in extract_secrets(content):
            names.append(config_path.parent.name)

    return sorted(names)


def _revert_repoint(
    repositories: Repositories,
    name: str,
    new_name: str,
) -> None:
    """Point the repositories back at the old name.

    Raises
    ------
    RenameError
        If they cannot be pointed back, which leaves them on a name
        the keyring is about to stop holding.

    """
    try:
        repositories.repoint_secret(new_name, name)
    except RepositoryError as e:
        msg = 'Repositories are repointed and cannot be pointed back'
        raise RenameError(msg, context=e.context) from None


def _revert_keyring_rename(name: str, new_name: str) -> None:
    """Move a secret's value back, reporting a failed revert."""
    try:
        rename_keyring_secret(new_name, name)
    except (ValueError, OSError) as e:
        msg = (
            'Secret is renamed but the repositories using it still '
            'hold the old name'
        )
        raise RenameError(
            msg,
            context={'secret': new_name, 'reason': str(e)},
        ) from None
