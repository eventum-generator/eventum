"""Unit tests for config_loader helper functions."""

import string
from unittest.mock import patch

import pytest

from eventum.core.config_loader import (
    _prepare_params,
    _prepare_secrets,
    _strip_yaml_comments,
    _substitute_tokens,
    extract_params,
    extract_secrets,
    extract_tokens,
    repoint_secret_token,
    resolve_secrets,
)
from eventum.security.manage import (
    SECRET_NAME_PATTERN,
    SecretNameError,
    validate_secret_name,
)

# --- extract_tokens ---


def test_extract_tokens_no_tokens():
    assert extract_tokens('plain yaml content') == []


def test_extract_tokens_finds_all():
    content = '${foo} and ${bar}'
    result = extract_tokens(content)
    assert result == ['foo', 'bar']


def test_extract_tokens_with_prefix_filter():
    content = '${params.x} ${secrets.y} ${params.z}'
    result = extract_tokens(content, prefix='params')
    assert result == ['params.x', 'params.z']


def test_extract_tokens_with_prefix_filter_no_match():
    content = '${secrets.y}'
    result = extract_tokens(content, prefix='params')
    assert result == []


def test_extract_tokens_whitespace_in_token():
    content = '${ params.x }'
    result = extract_tokens(content, prefix='params')
    assert result == ['params.x']


# --- extract_params ---


def test_extract_params_happy_path():
    content = '${params.host} and ${params.port}'
    result = extract_params(content)
    assert sorted(result) == ['host', 'port']


def test_extract_params_no_params():
    content = '${secrets.api_key}'
    result = extract_params(content)
    assert result == []


def test_extract_params_no_tokens():
    content = 'plain: yaml'
    result = extract_params(content)
    assert result == []


# --- extract_secrets ---


def test_extract_secrets_happy_path():
    content = '${secrets.api_key} and ${secrets.db_pass}'
    result = extract_secrets(content)
    assert sorted(result) == ['api_key', 'db_pass']


def test_extract_secrets_no_secrets():
    content = '${params.x}'
    result = extract_secrets(content)
    assert result == []


# --- _prepare_params ---


def test_prepare_params_all_provided():
    result = _prepare_params(
        used_params=['host', 'port'],
        provided_params={'host': 'localhost', 'port': 8080, 'extra': 'val'},
    )
    assert result == {'host': 'localhost', 'port': 8080}


def test_prepare_params_missing_raises():
    with pytest.raises(ValueError, match='missing'):
        _prepare_params(
            used_params=['host', 'port'],
            provided_params={'host': 'localhost'},
        )


def test_prepare_params_empty_used():
    result = _prepare_params(used_params=[], provided_params={'x': 1})
    assert result == {}


def test_prepare_params_resolves_nested_path():
    result = _prepare_params(
        used_params=['opensearch.host'],
        provided_params={'opensearch': {'host': 'localhost', 'port': 9200}},
    )
    assert result == {'opensearch': {'host': 'localhost'}}


def test_prepare_params_resolves_dotted_name():
    result = _prepare_params(
        used_params=['opensearch.host'],
        provided_params={'opensearch.host': 'localhost'},
    )
    assert result == {'opensearch': {'host': 'localhost'}}


def test_prepare_params_prefers_exact_name():
    result = _prepare_params(
        used_params=['a.b'],
        provided_params={'a.b': 1, 'a': {'b': 2}},
    )
    assert result == {'a': {'b': 1}}


def test_prepare_params_keeps_dotted_keys_of_value():
    result = _prepare_params(
        used_params=['headers'],
        provided_params={'headers': {'x.trace': 'id'}},
    )
    assert result == {'headers': {'x.trace': 'id'}}


def test_prepare_params_missing_nested_path_raises():
    with pytest.raises(ValueError, match='missing'):
        _prepare_params(used_params=['a.b'], provided_params={'a': 1})


def test_prepare_params_overlapping_names_raise():
    with pytest.raises(ValueError, match='overlaps'):
        _prepare_params(
            used_params=['a', 'a.b'],
            provided_params={'a': 1, 'a.b': 2},
        )


# --- _prepare_secrets ---


@patch('eventum.core.config_loader.get_secret')
def test_prepare_secrets_success(mock_get_secret):
    mock_get_secret.return_value = 'secret_value'
    result = _prepare_secrets(used_secrets=['api_key'])
    assert result == {'api_key': 'secret_value'}
    mock_get_secret.assert_called_once_with('api_key')


@patch('eventum.core.config_loader.get_secret')
def test_prepare_secrets_dotted_name(mock_get_secret):
    mock_get_secret.return_value = 'secret_value'
    result = _prepare_secrets(used_secrets=['db.password'])
    assert result == {'db': {'password': 'secret_value'}}
    mock_get_secret.assert_called_once_with('db.password')


@patch('eventum.core.config_loader.get_secret')
def test_prepare_secrets_missing_raises(mock_get_secret):
    mock_get_secret.side_effect = ValueError('not found')
    with pytest.raises(ValueError, match='Cannot obtain secret'):
        _prepare_secrets(used_secrets=['api_key'])


@patch('eventum.core.config_loader.get_secret')
def test_prepare_secrets_os_error_raises(mock_get_secret):
    mock_get_secret.side_effect = OSError('keyring error')
    with pytest.raises(ValueError, match='Cannot obtain secret'):
        _prepare_secrets(used_secrets=['api_key'])


@patch('eventum.core.config_loader.get_secret')
def test_prepare_secrets_empty_used(mock_get_secret):
    result = _prepare_secrets(used_secrets=[])
    assert result == {}
    mock_get_secret.assert_not_called()


# --- _substitute_tokens ---


def test_substitute_tokens_basic():
    result = _substitute_tokens(
        params={'x': 'hello'},
        secrets={},
        content='value: ${params.x}',
    )
    assert result == 'value: hello'


def test_substitute_tokens_mixed():
    result = _substitute_tokens(
        params={'host': 'localhost'},
        secrets={'pass': 's3cret'},
        content='host=${params.host} pass=${secrets.pass}',
    )
    assert 'host=localhost' in result
    assert 'pass=s3cret' in result


def test_substitute_tokens_malformed_raises():
    with pytest.raises(ValueError, match='malformed'):
        _substitute_tokens(
            params={},
            secrets={},
            content='${params.x',
        )


# --- _strip_yaml_comments ---


def test_strip_yaml_comments_removes_full_line_comments():
    content = (
        'output:\n'
        '  - stdout:\n'
        '      formatter:\n'
        '        format: json\n'
        '  # - opensearch:\n'
        '  #     hosts:\n'
        '  #       - ${params.opensearch_host}\n'
    )
    result = _strip_yaml_comments(content)
    assert '${params.opensearch_host}' not in result
    assert 'stdout' in result


def test_strip_yaml_comments_preserves_active_tokens():
    content = 'hosts:\n  - ${params.host}\n# - ${params.commented_host}\n'
    result = _strip_yaml_comments(content)
    assert '${params.host}' in result
    assert '${params.commented_host}' not in result


def test_strip_yaml_comments_no_comments():
    content = 'key: ${params.value}\n'
    assert _strip_yaml_comments(content) == content.rstrip('\n')


def test_extract_params_ignores_commented_tokens():
    active_content = _strip_yaml_comments(
        'host: ${params.host}\n# backup: ${params.backup_host}\n'
    )
    result = extract_params(active_content)
    assert result == ['host']


# --- resolve_secrets ---


@patch('eventum.core.config_loader.get_secret')
def test_resolve_secrets_substitutes_a_reference(mock_get_secret):
    mock_get_secret.return_value = 'ghp_token'

    assert resolve_secrets('${secrets.git_token}') == 'ghp_token'
    mock_get_secret.assert_called_once_with('git_token')


@patch('eventum.core.config_loader.get_secret')
def test_resolve_secrets_substitutes_a_dotted_name(mock_get_secret):
    mock_get_secret.return_value = 'ghp_token'

    assert resolve_secrets('${secrets.git.token}') == 'ghp_token'
    mock_get_secret.assert_called_once_with('git.token')


@patch('eventum.core.config_loader.get_secret')
def test_resolve_secrets_tolerates_spacing(mock_get_secret):
    mock_get_secret.return_value = 'ghp_token'

    assert resolve_secrets('${ secrets.git_token }') == 'ghp_token'


@patch('eventum.core.config_loader.get_secret')
def test_resolve_secrets_substitutes_within_a_value(mock_get_secret):
    mock_get_secret.side_effect = ['one', 'two']

    result = resolve_secrets('a-${secrets.first}-b-${secrets.second}')

    assert result == 'a-one-b-two'


@patch('eventum.core.config_loader.get_secret')
def test_resolve_secrets_keeps_a_token_of_another_kind(mock_get_secret):
    assert resolve_secrets('${params.token}') == '${params.token}'
    assert resolve_secrets('${token}') == '${token}'
    mock_get_secret.assert_not_called()


@patch('eventum.core.config_loader.get_secret')
def test_resolve_secrets_keeps_a_value_holding_no_token(mock_get_secret):
    # A password is resolved, not rendered: what a template engine
    # would read as syntax is part of the value here.
    assert resolve_secrets('{% raw %}p@ss') == '{% raw %}p@ss'
    mock_get_secret.assert_not_called()


@patch('eventum.core.config_loader.get_secret')
def test_resolve_secrets_missing_raises(mock_get_secret):
    mock_get_secret.side_effect = ValueError('not found')

    with pytest.raises(ValueError, match='Cannot obtain secret `git_token`'):
        resolve_secrets('${secrets.git_token}')


@patch('eventum.core.config_loader.get_secret')
def test_resolve_secrets_keyring_failure_raises(mock_get_secret):
    mock_get_secret.side_effect = OSError('keyring error')

    with pytest.raises(ValueError, match='Cannot obtain secret'):
        resolve_secrets('${secrets.git_token}')


# --- the grammar of a secret name, against what substitution reads ---

# Every character a name could be built from. The rule is checked over
# all of them rather than over a handful of examples, so widening it
# into something the substitution mangles fails here instead of in a
# configuration.
_ALPHABET = string.printable


def _accepted(name: str) -> bool:
    """Whether the keyring would accept the name."""
    try:
        validate_secret_name(name)
    except SecretNameError:
        return False

    return True


def _resolves(name: str) -> bool:
    """Whether a reference to the name reads the value back."""
    content = 'password: ${secrets.' + name + '}'

    with patch(
        'eventum.core.config_loader.get_secret',
        return_value='VALUE',
    ):
        try:
            secrets = _prepare_secrets(extract_secrets(content))
        except ValueError:
            return False

        try:
            rendered = _substitute_tokens({}, secrets, content)
        except ValueError:
            return False

    return rendered == 'password: VALUE'


@pytest.mark.parametrize('char', _ALPHABET)
def test_every_accepted_name_resolves(char):
    # The keyring accepts a name on this rule alone, so whatever it
    # lets in has to come back out of a configuration. The converse
    # does not hold: a name may resolve and still be refused, since
    # the keyring cannot store every name it could substitute.
    for name in (f'a{char}b', f'{char}ab', f'ab{char}'):
        if _accepted(name):
            assert _resolves(name), name


@pytest.mark.parametrize(
    'name',
    ['key', 'my_secret', '_leading', 'a.b', 'a.b.c', 'with2digits'],
)
def test_a_name_the_keyring_accepts_resolves(name):
    validate_secret_name(name)

    assert _resolves(name)


@pytest.mark.parametrize(
    'name',
    ['my-secret', 'my key', 'my@secret', '1secret', 'a/b', 'a.', 'a..b'],
)
def test_a_name_the_keyring_refuses_would_not_resolve(name):
    with pytest.raises(SecretNameError):
        validate_secret_name(name)

    assert not _resolves(name)


@pytest.mark.parametrize('name', ['keys', 'items', 'aws.get', 'a.values'])
def test_a_name_matching_a_mapping_method_reads_the_value(name):
    # Substitution reads a reference as attribute access, so these
    # would answer with a method of the mapping holding the secrets
    # unless names address entries and nothing else.
    validate_secret_name(name)

    assert _resolves(name)


@patch('eventum.core.config_loader.get_secret')
def test_a_name_holding_a_brace_reads_another_secret(mock_get_secret):
    # The one refused shape that does not fail: the token ends at the
    # first brace, so the reference reads the secret the shortened
    # name addresses and keeps the rest as text.
    mock_get_secret.return_value = 'VALUE-OF-A'
    content = 'password: ${secrets.a}b}'

    secrets = _prepare_secrets(extract_secrets(content))

    assert SECRET_NAME_PATTERN.fullmatch('a}b') is None
    assert _substitute_tokens({}, secrets, content) == 'password: VALUE-OF-Ab}'


# --- repoint_secret_token ---


def test_repoint_secret_token_rewrites_the_named_secret():
    content = 'password: ${secrets.git_token}\ntoken: ${secrets.other}\n'

    result = repoint_secret_token(content, 'git_token', 'forge_token')

    assert result == (
        'password: ${secrets.forge_token}\ntoken: ${secrets.other}\n'
    )


def test_repoint_secret_token_keeps_the_spacing_of_a_token():
    result = repoint_secret_token('${ secrets.a }', 'a', 'b')

    assert result == '${ secrets.b }'


def test_repoint_secret_token_keeps_the_text_around_a_token():
    result = repoint_secret_token('Bearer ${secrets.a}!', 'a', 'b')

    assert result == 'Bearer ${secrets.b}!'


def test_repoint_secret_token_leaves_another_kind_of_token():
    content = '${params.a} and ${secrets.ab}'

    assert repoint_secret_token(content, 'a', 'b') == content


def test_repoint_secret_token_leaves_content_holding_none():
    assert repoint_secret_token('plain value', 'a', 'b') == 'plain value'
