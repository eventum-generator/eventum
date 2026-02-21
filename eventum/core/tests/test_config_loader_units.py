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


# --- _prepare_secrets ---


@patch('eventum.core.config_loader.get_secret')
def test_prepare_secrets_success(mock_get_secret):
    mock_get_secret.return_value = 'secret_value'
    result = _prepare_secrets(used_secrets=['api_key'])
    assert result == {'api_key': 'secret_value'}
    mock_get_secret.assert_called_once_with('api_key')


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
