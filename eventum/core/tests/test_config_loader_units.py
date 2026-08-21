"""Unit tests for config_loader helper functions."""

from unittest.mock import patch

import pytest

from eventum.core.config_loader import (
    _extract_tokens,
    _prepare_params,
    _prepare_secrets,
    _strip_yaml_comments,
    _substitute_tokens,
    extract_params,
    extract_secrets,
)
from eventum.security.manage import SECRET_NAME_PATTERN

# --- _extract_tokens ---


def test_extract_tokens_no_tokens():
    assert _extract_tokens('plain yaml content') == []


def test_extract_tokens_finds_all():
    content = '${foo} and ${bar}'
    result = _extract_tokens(content)
    assert result == ['foo', 'bar']


def test_extract_tokens_with_prefix_filter():
    content = '${params.x} ${secrets.y} ${params.z}'
    result = _extract_tokens(content, prefix='params')
    assert result == ['params.x', 'params.z']


def test_extract_tokens_with_prefix_filter_no_match():
    content = '${secrets.y}'
    result = _extract_tokens(content, prefix='params')
    assert result == []


def test_extract_tokens_whitespace_in_token():
    content = '${ params.x }'
    result = _extract_tokens(content, prefix='params')
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


# --- the grammar of a secret name, against what substitution reads ---


@pytest.mark.parametrize(
    'name',
    ['key', 'MY_SECRET', '_leading', 'a.b', 'a.b.c', 'with2digits'],
)
@patch('eventum.core.config_loader.get_secret')
def test_a_name_the_keyring_accepts_resolves(mock_get_secret, name):
    # The keyring guards the name against this: whatever it lets in
    # has to come back out of a configuration.
    mock_get_secret.return_value = 'VALUE'
    content = 'password: ${secrets.' + name + '}'

    secrets = _prepare_secrets(extract_secrets(content))

    assert SECRET_NAME_PATTERN.fullmatch(name) is not None
    assert _substitute_tokens({}, secrets, content) == 'password: VALUE'


@pytest.mark.parametrize(
    'name',
    ['my-secret', 'my key', 'my@secret', '1secret', 'a/b', 'a.', 'a..b'],
)
@patch('eventum.core.config_loader.get_secret')
def test_a_name_the_keyring_refuses_would_not_resolve(mock_get_secret, name):
    mock_get_secret.return_value = 'VALUE'
    content = 'password: ${secrets.' + name + '}'
    secrets = _prepare_secrets(extract_secrets(content))

    assert SECRET_NAME_PATTERN.fullmatch(name) is None

    with pytest.raises(ValueError):
        _substitute_tokens({}, secrets, content)


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
