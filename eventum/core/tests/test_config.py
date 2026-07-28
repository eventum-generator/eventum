from pathlib import Path
from unittest.mock import patch

import pytest

from eventum.core.config import GeneratorConfig
from eventum.core.config_loader import ConfigurationLoadError, load

BASE_PATH = Path(__file__).parent

NESTED_PARAMS_CONFIG_PATH = BASE_PATH / 'static' / 'nested_params_config.yml'

CONFIG_PATH = BASE_PATH / 'static' / 'config.yml'
BAD_TOKENS_CONFIG_PATH = BASE_PATH / 'static' / 'bad_tokens_config.yml'
INVALID_YAML_CONFIG_PATH = BASE_PATH / 'static' / 'invalid_yaml_config.yml'
INVALID_STRUCTURE_CONFIG_PATH = (
    BASE_PATH / 'static' / 'invalid_structure_config.yml'
)
DOTTED_KEYS_CONFIG_PATH = BASE_PATH / 'static' / 'dotted_keys_config.yml'
CONFLICTING_DOTTED_KEYS_CONFIG_PATH = (
    BASE_PATH / 'static' / 'conflicting_dotted_keys_config.yml'
)


def test_load():
    config = load(path=CONFIG_PATH, params={'stream': 'stdout'})

    assert isinstance(config, GeneratorConfig)
    assert config.output[0]['stdout']['stream'] == 'stdout'


def test_invalid_path():
    with pytest.raises(ConfigurationLoadError):
        load(path=BASE_PATH / 'cha cha cha', params={})


def test_bad_tokens_structure():
    with pytest.raises(ConfigurationLoadError):
        load(path=BAD_TOKENS_CONFIG_PATH, params={'stream': 'stdout'})


def test_invalid_config_yaml():
    with pytest.raises(ConfigurationLoadError):
        load(path=INVALID_YAML_CONFIG_PATH, params={'stream': 'stdout'})


def test_invalid_config_structure():
    with pytest.raises(ConfigurationLoadError):
        load(path=INVALID_STRUCTURE_CONFIG_PATH, params={'stream': 'stdout'})


def test_missing_parameters():
    with pytest.raises(ConfigurationLoadError):
        load(path=CONFIG_PATH, params={})


def test_load_resolves_nested_param_names() -> None:
    """Dotted token name addresses a path of nested params."""
    with patch(
        'eventum.core.config_loader.get_secret',
        return_value='pass',
    ) as get_secret:
        config = load(
            path=NESTED_PARAMS_CONFIG_PATH,
            params={'opensearch': {'host': 'localhost', 'user': 'admin'}},
        )

    output = config.output[0]['opensearch']
    assert output['hosts'] == ['localhost']
    assert output['username'] == 'admin'
    assert output['password'] == 'pass'
    get_secret.assert_called_once_with('opensearch.password')


def test_load_resolves_dotted_param_names() -> None:
    """Dotted token name addresses a param spelled the same way."""
    with patch('eventum.core.config_loader.get_secret', return_value='pass'):
        config = load(
            path=NESTED_PARAMS_CONFIG_PATH,
            params={
                'opensearch.host': 'localhost',
                'opensearch.user': 'admin',
            },
        )

    output = config.output[0]['opensearch']
    assert output['hosts'] == ['localhost']
    assert output['username'] == 'admin'


def test_load_missing_nested_param_name() -> None:
    """Unresolvable token name is reported as a missing param."""
    with (
        patch('eventum.core.config_loader.get_secret', return_value='pass'),
        pytest.raises(ConfigurationLoadError) as exc,
    ):
        load(
            path=NESTED_PARAMS_CONFIG_PATH,
            params={'opensearch': {'host': 'localhost'}},
        )

    assert 'opensearch.user' in exc.value.context['reason']


def test_load_expands_dotted_keys() -> None:
    """Dotted spellings load identically to the nested form."""
    config = load(path=DOTTED_KEYS_CONFIG_PATH, params={})

    canonical = GeneratorConfig.model_validate(
        {
            'input': [{'cron': {'expression': '*/5 * * * *', 'count': 1}}],
            'event': {
                'template': {
                    'mode': 'all',
                    'params': {},
                    'samples': {},
                    'templates': [{'test': {'template': 'test.jinja'}}],
                },
            },
            'output': [{'stdout': {'formatter': {'format': 'plain'}}}],
        },
    )
    assert config == canonical


def test_load_conflicting_dotted_keys() -> None:
    """Conflicting spellings raise with the key path in reason."""
    with pytest.raises(ConfigurationLoadError) as exc:
        load(path=CONFLICTING_DOTTED_KEYS_CONFIG_PATH, params={})

    assert 'output[0].stdout.formatter.format' in exc.value.context['reason']
