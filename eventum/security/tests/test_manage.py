import pytest

from eventum.security.manage import (
    SecretConflictError,
    SecretNameError,
    SecretNotFoundError,
    get_secret,
    list_secrets,
    remove_secret,
    rename_secret,
    set_secret,
)


@pytest.fixture
def temp_keyring_file(tmp_path):
    # A path of this test alone. A fixed name under the temporary
    # directory is shared with every other run on the machine, and the
    # teardown of one removes the keyring another is still using.
    return tmp_path / 'test.cfg'


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


# A name is read back as an expression of a rendered configuration, so
# these are the shapes it may and may not take. The last one is the
# reason the rule is not advisory: it reads another secret instead of
# failing.
@pytest.mark.parametrize(
    'name',
    ['key', 'MY_SECRET', '_leading', 'a.b', 'a.b.c', 'with2digits'],
)
def test_set_secret_accepts_a_referenceable_name(name, temp_keyring_file):
    set_secret(name, 'value', temp_keyring_file)

    assert get_secret(name, temp_keyring_file) == 'value'


@pytest.mark.parametrize(
    'name',
    [
        'my-secret',
        'my key',
        'my@secret',
        '1secret',
        'a/b',
        'a.',
        'a..b',
        'a}b',
        '${secrets.a}',
    ],
)
def test_set_secret_rejects_a_name_that_cannot_be_referenced(
    name,
    temp_keyring_file,
):
    with pytest.raises(SecretNameError):
        set_secret(name, 'value', temp_keyring_file)

    assert list_secrets(temp_keyring_file) == []


def test_rename_secret_rejects_a_name_that_cannot_be_referenced(
    temp_keyring_file,
):
    set_secret('key', 'value', temp_keyring_file)

    with pytest.raises(SecretNameError):
        rename_secret('key', 'my-secret', temp_keyring_file)

    assert list_secrets(temp_keyring_file) == ['key']
    assert get_secret('key', temp_keyring_file) == 'value'


def test_rename_secret_checks_the_name_before_the_secret_exists(
    temp_keyring_file,
):
    # The new name is refused whether or not there is anything to
    # rename, so nothing is read before the request is known to be
    # answerable.
    with pytest.raises(SecretNameError):
        rename_secret('absent', 'my-secret', temp_keyring_file)
