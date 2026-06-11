from pathlib import Path

import pytest

from eventum.core.config import GeneratorConfig
from eventum.core.config_loader import ConfigurationLoadError, load

BASE_PATH = Path(__file__).parent

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
