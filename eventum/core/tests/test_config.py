from pathlib import Path
from unittest.mock import patch

import pytest

from eventum.core.config import GeneratorConfig
from eventum.core.config_loader import ConfigurationLoadError, load
from eventum.plugins.event.plugins.template.config import (
    TemplateEventPluginConfig,
    TemplatePickingMode,
)

BASE_PATH = Path(__file__).parent

CONFIG_PATH = BASE_PATH / 'static' / 'config.yml'
BAD_TOKENS_CONFIG_PATH = BASE_PATH / 'static' / 'bad_tokens_config.yml'
INVALID_YAML_CONFIG_PATH = BASE_PATH / 'static' / 'invalid_yaml_config.yml'
INVALID_STRUCTURE_CONFIG_PATH = (
    BASE_PATH / 'static' / 'invalid_structure_config.yml'
)
FSM_CONDITIONS_CONFIG_PATH = BASE_PATH / 'static' / 'fsm_conditions_config.yml'
NESTED_PARAMS_CONFIG_PATH = BASE_PATH / 'static' / 'nested_params_config.yml'


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


def test_load_keeps_dotted_keys_literal() -> None:
    """Keys are taken as written, without splitting them on dots."""
    config = load(path=FSM_CONDITIONS_CONFIG_PATH, params={})
    template_config = config.event['template']

    assert template_config['params'] == {'host.name': 'srv-01'}

    transitions = template_config['templates'][0]['login']['transitions']
    assert transitions[0]['when'] == {'eq': {'shared.status': 'ready'}}


def test_load_validates_documented_fsm_conditions() -> None:
    """Every documented fsm condition passes plugin validation."""
    config = load(path=FSM_CONDITIONS_CONFIG_PATH, params={})

    plugin_config = TemplateEventPluginConfig.model_validate(
        config.event['template'],
    )

    assert plugin_config.root.mode == TemplatePickingMode.FSM
