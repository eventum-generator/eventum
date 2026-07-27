import os
import tempfile
from pathlib import Path

import pytest

from eventum.security.manage import (
    SecretConflictError,
    SecretNotFoundError,
    get_secret,
    list_secrets,
    remove_secret,
    rename_secret,
    set_secret,
)


@pytest.fixture
def temp_keyring_file():
    filename = Path(tempfile.gettempdir(), 'test.cfg')
    yield filename
    if filename.exists():
        os.remove(filename)


def test_get_secret(temp_keyring_file):
    with pytest.raises(ValueError):
        get_secret('key', temp_keyring_file)


def test_set_secret(temp_keyring_file):
    set_secret('key', 'value', temp_keyring_file)
    assert get_secret('key', temp_keyring_file) == 'value'


def test_list_secrets(temp_keyring_file):
    assert list_secrets(temp_keyring_file) == []

    set_secret('key', 'value', temp_keyring_file)
    assert list_secrets(temp_keyring_file) == ['key']

    set_secret('key2', 'value', temp_keyring_file)
    assert list_secrets(temp_keyring_file) == ['key', 'key2']


def test_remove_secret(temp_keyring_file):
    set_secret('key', 'value', temp_keyring_file)
    assert get_secret('key', temp_keyring_file) == 'value'

    remove_secret('key', temp_keyring_file)

    with pytest.raises(ValueError):
        get_secret('key', temp_keyring_file)


def test_rename_secret_keeps_value(temp_keyring_file):
    set_secret('key', 'value', temp_keyring_file)

    rename_secret('key', 'renamed', temp_keyring_file)

    assert list_secrets(temp_keyring_file) == ['renamed']
    assert get_secret('renamed', temp_keyring_file) == 'value'


def test_rename_secret_missing_raises(temp_keyring_file):
    with pytest.raises(SecretNotFoundError):
        rename_secret('absent', 'renamed', temp_keyring_file)


def test_rename_secret_taken_name_raises(temp_keyring_file):
    set_secret('key', 'value', temp_keyring_file)
    set_secret('other', 'other-value', temp_keyring_file)

    with pytest.raises(SecretConflictError):
        rename_secret('key', 'other', temp_keyring_file)

    assert list_secrets(temp_keyring_file) == ['key', 'other']
    assert get_secret('other', temp_keyring_file) == 'other-value'


def test_rename_secret_to_same_name_raises(temp_keyring_file):
    set_secret('key', 'value', temp_keyring_file)

    with pytest.raises(SecretConflictError):
        rename_secret('key', 'key', temp_keyring_file)

    assert get_secret('key', temp_keyring_file) == 'value'


def test_rename_secret_blank_name_raises(temp_keyring_file):
    set_secret('key', 'value', temp_keyring_file)

    with pytest.raises(ValueError, match='cannot be blank'):
        rename_secret('key', '', temp_keyring_file)
