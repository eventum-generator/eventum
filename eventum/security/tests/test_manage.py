import os
import tempfile
from pathlib import Path

import pytest

from eventum.security.manage import (
    get_secret,
    list_secrets,
    remove_secret,
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
