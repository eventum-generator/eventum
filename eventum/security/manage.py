"""Module for securely storing and retrieving secrets using a keyring."""

import os
from configparser import ConfigParser
from functools import lru_cache
from pathlib import Path
from typing import TypedDict

import keyrings.cryptfile.cryptfile as crypt  # type: ignore[import-untyped]
import structlog
from keyrings.cryptfile.escape import unescape  # type: ignore[import-untyped]

DEFAULT_PASSWORD = 'eventum'  # noqa: S105
KEYRING_PASS_ENV_VAR = 'EVENTUM_KEYRING_PASSWORD'  # noqa: S105
KEYRING_SERVICE_NAME = 'eventum'


logger = structlog.stdlib.get_logger()


class SecretNotFoundError(ValueError):
    """Secret with the requested name is missing in keyring."""


class SecretConflictError(ValueError):
    """Secret with the requested name is already in keyring."""


@lru_cache
def get_keyring_password() -> str:
    """Get password for keyring.

    Password is searched in environment variable first, otherwise
    default password will be returned.

    Returns
    -------
    str
        Password for keyring.

    """
    password = os.getenv(KEYRING_PASS_ENV_VAR)

    if password is None:
        password = DEFAULT_PASSWORD
        logger.warning(
            'Environment variable with keyring password is not set, '
            'using default password for keyring',
        )

    return password


class SecuritySettings(TypedDict):
    """Security settings.

    Attributes
    ----------
    cryptfile_location : Path | None
        Absolute path to keyring cryptfile.

    """

    cryptfile_location: Path | None


SECURITY_SETTINGS = SecuritySettings(cryptfile_location=None)


def _get_keyring(path: Path | None = None) -> crypt.CryptFileKeyring:
    """Get keyring instance.

    path : Path | None, default=None
        Path to keyring file, default location is used if none is
        provided and security setting cryptfile_location is none.

    Returns
    -------
    crypt.CryptFileKeyring
        Keyring instance.

    """
    keyring = crypt.CryptFileKeyring()

    path = path or SECURITY_SETTINGS['cryptfile_location']
    if path is not None:
        keyring.file_path = path  # type: ignore[assignment]

    keyring.keyring_key = get_keyring_password()

    return keyring


def list_secrets(path: Path | None = None) -> list[str]:
    """Get secret names from keyring.

    Parameters
    ----------
    path : Path | None, default=None
        Path to keyring file, default location is used if none is
        provided and security setting cryptfile_location is none.

    Returns
    -------
    list[str]
        List with names of secrets.

    """
    keyring = _get_keyring(path)
    keyring_path = Path(str(keyring.file_path))

    if not keyring_path.exists():
        return []

    keyring_content = keyring_path.read_text()

    config = ConfigParser()
    config.read_string(keyring_content)

    try:
        service_section = config[KEYRING_SERVICE_NAME]
    except KeyError:
        return []

    return [unescape(secret_name) for secret_name in service_section]


def get_secret(name: str, path: Path | None = None) -> str:
    """Get secret from keyring.

    Parameters
    ----------
    name : str
        Name of the secret.

    path : Path | None, default=None
        Path to keyring file, default location is used if none is
        provided and security setting cryptfile_location is none.

    Returns
    -------
    str
        Secret.

    Raises
    ------
    ValueError
        If name of secret is blank or missing in keyring.

    EnvironmentError
        If any error occurs during obtaining secret from keyring.

    """
    logger.info('Secret is accessed', secret=name)
    if not name:
        msg = 'Name of secret cannot be blank'
        raise ValueError(msg)

    keyring = _get_keyring(path)

    try:
        secret = keyring.get_password(
            service=KEYRING_SERVICE_NAME,
            username=name,
        )
    except Exception as e:
        raise OSError(e) from e

    if secret is None:
        msg = 'Secret is missing'
        raise ValueError(msg)

    return secret


def set_secret(name: str, value: str, path: Path | None = None) -> None:
    """Set secret to keyring under specified name.

    Parameters
    ----------
    name : str
        Name of the secret.

    value : str
        Value of the secret.

    path : Path | None, default=None
        Path to keyring file, default location is used if none is
        provided and security setting cryptfile_location is none.

    Raises
    ------
    ValueError
        If name or value of secret are blank.

    EnvironmentError
        If any error occurs during setting secret to keyring.

    """
    logger.info('Secret is set', secret=name)

    if not name or not value:
        msg = 'Name and value of secret cannot be empty'
        raise ValueError(msg)

    keyring = _get_keyring(path)

    try:
        keyring.set_password(  # type: ignore[call-arg]
            system=KEYRING_SERVICE_NAME,
            username=name,
            password=value,
        )
    except Exception as e:
        raise OSError(e) from e


def remove_secret(name: str, path: Path | None = None) -> None:
    """Remove secret from keyring.

    Parameters
    ----------
    name : str
        Name of the secret to remove.

    path : Path | None, default=None
        Path to keyring file, default location is used if none is
        provided and security setting cryptfile_location is none.

    Raises
    ------
    ValueError
        If name of secret is blank.

    EnvironmentError
        If any error occurs during removing secret from keyring.

    """
    logger.info('Secret is removed', secret=name)

    if not name:
        msg = 'Name of secret cannot be blank'
        raise ValueError(msg)

    keyring = _get_keyring(path)

    try:
        keyring.delete_password(
            service=KEYRING_SERVICE_NAME,
            username=name,
        )
    except Exception as e:
        raise OSError(e) from e


def rename_secret(
    name: str,
    new_name: str,
    path: Path | None = None,
) -> None:
    """Rename secret in keyring, keeping its value.

    The secret is written under the new name before the old name is
    removed, so a failure never loses the value.

    Parameters
    ----------
    name : str
        Current name of the secret.

    new_name : str
        Name to rename the secret to.

    path : Path | None, default=None
        Path to keyring file, default location is used if none is
        provided and security setting cryptfile_location is none.

    Raises
    ------
    ValueError
        If name or new name of secret is blank.

    SecretNotFoundError
        If no secret with the provided name is in keyring.

    SecretConflictError
        If a secret with the new name is already in keyring, including
        the case when the new name equals the current one.

    EnvironmentError
        If any error occurs during accessing keyring.

    """
    logger.info('Secret is renamed', secret=name, value=new_name)

    if not name or not new_name:
        msg = 'Name of secret cannot be blank'
        raise ValueError(msg)

    existing_names = list_secrets(path)

    if name not in existing_names:
        msg = 'Secret is missing'
        raise SecretNotFoundError(msg)

    if new_name in existing_names:
        msg = 'Secret with this name already exists'
        raise SecretConflictError(msg)

    set_secret(
        name=new_name, value=get_secret(name=name, path=path), path=path
    )
    remove_secret(name=name, path=path)
