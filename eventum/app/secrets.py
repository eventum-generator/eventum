"""Transport-neutral operations over the secrets of the keyring.

A secret is referred to from two places at once - the configuration of
a project, as a `${secrets.<name>}` token, and the secret field of a
connected repository. Both kinds are answered here, so what a rename or
a removal would reach is known in one place, and renaming repoints the
referrers that can be repointed.
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
from eventum.core.config_loader import extract_secrets
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
    repositories: Repositories,
    name: str,
    new_name: str,
) -> list[str]:
    """Rename a secret and repoint the repositories holding it.

    The value is moved to the new name in the keyring first, then every
    connected repository authenticating with the secret is pointed at
    it; a repointing that fails moves the value back. Renames of this
    process take their turn, so neither step of one lands inside the
    other. Project configurations are not rewritten - a `${secrets.*}`
    token is part of the configuration text and belongs to whoever
    edits it.

    Parameters
    ----------
    repositories : Repositories
        Connected repositories service.

    name : str
        Current name of the secret.

    new_name : str
        Name to rename the secret to.

    Returns
    -------
    list[str]
        Names of the repositories that were repointed.

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
            return repositories.repoint_secret(name, new_name)
        except RepositoryError as e:
            _revert_keyring_rename(name, new_name)

            msg = 'Repositories using the secret cannot be repointed'
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
