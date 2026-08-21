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
    ['key', 'my_secret', '_leading', 'a.b', 'a.b.c', 'with2digits'],
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
        'MY_SECRET',
        'Api_Token',
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


def test_a_name_the_keyring_accepts_is_read_back_by_the_name_it_lists(
    temp_keyring_file,
):
    # The rule exists to keep these three in step: what was written,
    # what the listing reports, and what can be read.
    set_secret('api_token', 'value', temp_keyring_file)

    assert list_secrets(temp_keyring_file) == ['api_token']
    assert get_secret('api_token', temp_keyring_file) == 'value'


def test_a_name_holding_a_capital_is_refused_because_it_could_not_be(
    temp_keyring_file,
):
    # Why the rule is lowercase: the keyring folds the case of a name
    # while encrypting the value against the name as given, so a
    # capital would be listed in a spelling that cannot read it.
    with pytest.raises(SecretNameError):
        set_secret('API_TOKEN', 'value', temp_keyring_file)

    assert list_secrets(temp_keyring_file) == []


def test_two_names_differing_only_in_case_cannot_both_be_written(
    temp_keyring_file,
):
    # The second write would land on the entry of the first and leave
    # it unreadable, which the rule prevents by refusing the capital.
    set_secret('api_token', 'first', temp_keyring_file)

    with pytest.raises(SecretNameError):
        set_secret('API_TOKEN', 'second', temp_keyring_file)

    assert get_secret('api_token', temp_keyring_file) == 'first'
