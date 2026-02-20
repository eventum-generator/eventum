"""Tests for startup generator parameters models."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from eventum.app.models.generators import (
    StartupGeneratorParameters,
    StartupGeneratorParametersList,
)
from eventum.core.parameters import GenerationParameters


# --- StartupGeneratorParameters ---


def test_startup_generator_parameters_autostart_default():
    params = StartupGeneratorParameters(
        id='gen1',
        path=Path('config.yml'),
    )
    assert params.autostart is True


def test_startup_generator_parameters_autostart_false():
    params = StartupGeneratorParameters(
        id='gen1',
        path=Path('config.yml'),
        autostart=False,
    )
    assert params.autostart is False


# --- StartupGeneratorParametersList.build_over_generation_parameters ---


def test_build_over_generation_parameters_basic():
    base = GenerationParameters(timezone='UTC')
    result = StartupGeneratorParametersList.build_over_generation_parameters(
        object=[{'id': 'gen1', 'path': 'config.yml'}],
        generation_parameters=base,
    )
    assert len(result.root) == 1
    assert result.root[0].id == 'gen1'
    assert result.root[0].timezone == 'UTC'


def test_build_over_generation_parameters_override():
    base = GenerationParameters(timezone='UTC')
    result = StartupGeneratorParametersList.build_over_generation_parameters(
        object=[
            {'id': 'gen1', 'path': 'config.yml', 'timezone': 'US/Eastern'}
        ],
        generation_parameters=base,
    )
    assert result.root[0].timezone == 'US/Eastern'


def test_build_over_generation_parameters_empty_list():
    base = GenerationParameters()
    result = StartupGeneratorParametersList.build_over_generation_parameters(
        object=[],
        generation_parameters=base,
    )
    assert len(result.root) == 0


def test_build_over_generation_parameters_nested_override():
    base = GenerationParameters(timezone='UTC')
    result = StartupGeneratorParametersList.build_over_generation_parameters(
        object=[
            {
                'id': 'gen1',
                'path': 'config.yml',
                'batch': {'size': 500},
            }
        ],
        generation_parameters=base,
    )
    assert result.root[0].batch.size == 500


def test_build_over_generation_parameters_missing_id_raises():
    base = GenerationParameters()
    with pytest.raises(ValidationError):
        StartupGeneratorParametersList.build_over_generation_parameters(
            object=[{'path': 'config.yml'}],
            generation_parameters=base,
        )


def test_build_over_generation_parameters_multiple_generators():
    base = GenerationParameters(timezone='UTC')
    result = StartupGeneratorParametersList.build_over_generation_parameters(
        object=[
            {'id': 'gen1', 'path': 'config1.yml'},
            {'id': 'gen2', 'path': 'config2.yml', 'live_mode': False},
        ],
        generation_parameters=base,
    )
    assert len(result.root) == 2
    assert result.root[0].id == 'gen1'
    assert result.root[0].live_mode is True
    assert result.root[1].id == 'gen2'
    assert result.root[1].live_mode is False
