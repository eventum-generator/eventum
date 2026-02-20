"""Tests for plugins initializer."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from eventum.core.parameters import GeneratorParameters
from eventum.core.plugins_initializer import (
    InitializationError,
    init_plugin,
    init_plugins,
)
from eventum.plugins.event.plugins.template.plugin import TemplateEventPlugin
from eventum.plugins.exceptions import (
    PluginConfigurationError,
    PluginLoadError,
    PluginNotFoundError,
)
from eventum.plugins.input.plugins.cron.plugin import CronInputPlugin
from eventum.plugins.input.plugins.static.plugin import StaticInputPlugin
from eventum.plugins.output.plugins.file.plugin import FileOutputPlugin
from eventum.plugins.output.plugins.stdout.plugin import StdoutOutputPlugin

BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_PATH = BASE_DIR / 'static' / 'template.jinja'
TEMPLATE_REL_PATH = TEMPLATE_PATH.relative_to(BASE_DIR)


def test_initializer():
    input_config = [
        {'cron': {'expression': '* * * * *', 'count': 1}},
        {'static': {'count': 100}},
    ]
    event_config = {
        'template': {
            'params': {},
            'samples': {},
            'mode': 'all',
            'templates': [{'test': {'template': TEMPLATE_REL_PATH}}],
        }
    }
    output_config = [
        {'stdout': {'stream': 'stderr'}},
        {'file': {'path': '/tmp/out.log'}},
    ]

    plugins = init_plugins(
        input=input_config,
        event=event_config,
        output=output_config,
        params=GeneratorParameters(
            id='test',
            live_mode=False,
            path=BASE_DIR / 'ephemeral.yml',
        ),
    )

    assert isinstance(plugins.input[0], CronInputPlugin)
    assert isinstance(plugins.input[1], StaticInputPlugin)

    assert isinstance(plugins.event, TemplateEventPlugin)

    assert isinstance(plugins.output[0], StdoutOutputPlugin)
    assert isinstance(plugins.output[1], FileOutputPlugin)


# --- init_plugin error cases ---


@patch('eventum.core.plugins_initializer.load_input_plugin')
def test_init_plugin_not_found(mock_load):
    mock_load.side_effect = PluginNotFoundError(
        'not found',
        context={'plugin_name': 'fake'},
    )
    with pytest.raises(InitializationError, match='not found'):
        init_plugin(
            name='fake',
            type='input',
            config={},
            params={'id': 1, 'timezone': None, 'base_path': Path('.')},
        )


@patch('eventum.core.plugins_initializer.load_input_plugin')
def test_init_plugin_load_error(mock_load):
    mock_load.side_effect = PluginLoadError(
        'load failed',
        context={'plugin_name': 'bad'},
    )
    with pytest.raises(InitializationError, match='Failed to load'):
        init_plugin(
            name='bad',
            type='input',
            config={},
            params={'id': 1, 'timezone': None, 'base_path': Path('.')},
        )


@patch('eventum.core.plugins_initializer.load_input_plugin')
def test_init_plugin_config_validation_error(mock_load):
    mock_config_cls = MagicMock()
    mock_config_cls.model_validate.side_effect = (
        ValidationError.from_exception_data(
            title='test',
            line_errors=[
                {
                    'type': 'missing',
                    'loc': ('field',),
                    'input': {},
                },
            ],
        )
    )
    mock_plugin_info = MagicMock()
    mock_plugin_info.cls = MagicMock()
    mock_plugin_info.config_cls = mock_config_cls
    mock_load.return_value = mock_plugin_info

    with pytest.raises(InitializationError, match='Invalid configuration'):
        init_plugin(
            name='test_plugin',
            type='input',
            config={'bad': 'data'},
            params={'id': 1, 'timezone': None, 'base_path': Path('.')},
        )


@patch('eventum.core.plugins_initializer.load_input_plugin')
def test_init_plugin_configuration_error(mock_load):
    mock_config_cls = MagicMock()
    mock_config_cls.model_validate.return_value = MagicMock()
    mock_plugin_cls = MagicMock()
    mock_plugin_cls.side_effect = PluginConfigurationError(
        'bad config',
        context={'detail': 'reason'},
    )
    mock_plugin_info = MagicMock()
    mock_plugin_info.cls = mock_plugin_cls
    mock_plugin_info.config_cls = mock_config_cls
    mock_load.return_value = mock_plugin_info

    with pytest.raises(InitializationError, match='bad config'):
        init_plugin(
            name='test_plugin',
            type='input',
            config={},
            params={'id': 1, 'timezone': None, 'base_path': Path('.')},
        )


@patch('eventum.core.plugins_initializer.load_input_plugin')
def test_init_plugin_unexpected_error(mock_load):
    mock_config_cls = MagicMock()
    mock_config_cls.model_validate.return_value = MagicMock()
    mock_plugin_cls = MagicMock()
    mock_plugin_cls.side_effect = RuntimeError('kaboom')
    mock_plugin_info = MagicMock()
    mock_plugin_info.cls = mock_plugin_cls
    mock_plugin_info.config_cls = mock_config_cls
    mock_load.return_value = mock_plugin_info

    with pytest.raises(InitializationError, match='Unexpected error'):
        init_plugin(
            name='test_plugin',
            type='input',
            config={},
            params={'id': 1, 'timezone': None, 'base_path': Path('.')},
        )


@patch('eventum.core.plugins_initializer.load_event_plugin')
def test_init_plugin_event_type_calls_event_loader(mock_load):
    mock_load.side_effect = PluginNotFoundError(
        'not found',
        context={'plugin_name': 'fake'},
    )
    with pytest.raises(InitializationError):
        init_plugin(
            name='fake',
            type='event',
            config={},
            params={'id': 1, 'base_path': Path('.')},
        )
    mock_load.assert_called_once_with(name='fake')


@patch('eventum.core.plugins_initializer.load_output_plugin')
def test_init_plugin_output_type_calls_output_loader(mock_load):
    mock_load.side_effect = PluginNotFoundError(
        'not found',
        context={'plugin_name': 'fake'},
    )
    with pytest.raises(InitializationError):
        init_plugin(
            name='fake',
            type='output',
            config={},
            params={'id': 1, 'base_path': Path('.')},
        )
    mock_load.assert_called_once_with(name='fake')
