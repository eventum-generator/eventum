"""Tests for core generator parameters."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from eventum.core.parameters import (
    BatchParameters,
    GenerationParameters,
    GeneratorParameters,
    QueueParameters,
)


# --- BatchParameters ---


def test_batch_parameters_defaults_when_nothing_provided():
    params = BatchParameters()
    assert params.size == 10_000
    assert params.delay == 1.0


def test_batch_parameters_size_only():
    params = BatchParameters(size=500)
    assert params.size == 500
    assert params.delay is None


def test_batch_parameters_delay_only():
    params = BatchParameters(delay=2.0)
    assert params.size is None
    assert params.delay == 2.0


def test_batch_parameters_both_none_explicitly_raises():
    with pytest.raises(ValidationError, match='Batch size or timeout'):
        BatchParameters(size=None, delay=None)


def test_batch_parameters_size_zero_raises():
    with pytest.raises(ValidationError):
        BatchParameters(size=0)


def test_batch_parameters_size_one_passes():
    params = BatchParameters(size=1)
    assert params.size == 1


def test_batch_parameters_delay_below_minimum_raises():
    with pytest.raises(ValidationError):
        BatchParameters(delay=0.05)


def test_batch_parameters_delay_minimum_passes():
    params = BatchParameters(delay=0.1)
    assert params.delay == 0.1


def test_batch_parameters_frozen():
    params = BatchParameters()
    with pytest.raises(ValidationError):
        params.size = 999


# --- QueueParameters ---


def test_queue_parameters_defaults():
    params = QueueParameters()
    assert params.max_timestamp_batches == 10
    assert params.max_event_batches == 10


def test_queue_parameters_zero_raises():
    with pytest.raises(ValidationError):
        QueueParameters(max_timestamp_batches=0)


def test_queue_parameters_one_passes():
    params = QueueParameters(max_timestamp_batches=1, max_event_batches=1)
    assert params.max_timestamp_batches == 1
    assert params.max_event_batches == 1


def test_queue_parameters_extra_fields_forbidden():
    with pytest.raises(ValidationError):
        QueueParameters(unknown_field=5)


# --- GenerationParameters ---


def test_generation_parameters_utc_default():
    params = GenerationParameters()
    assert params.timezone == 'UTC'


def test_generation_parameters_valid_timezone():
    params = GenerationParameters(timezone='US/Eastern')
    assert params.timezone == 'US/Eastern'


def test_generation_parameters_invalid_timezone_raises():
    with pytest.raises(ValidationError, match='Unknown time zone'):
        GenerationParameters(timezone='Fake/Zone')


def test_generation_parameters_timezone_too_short_raises():
    with pytest.raises(ValidationError):
        GenerationParameters(timezone='AB')


def test_generation_parameters_max_concurrency_zero_raises():
    with pytest.raises(ValidationError):
        GenerationParameters(max_concurrency=0)


def test_generation_parameters_max_concurrency_one_passes():
    params = GenerationParameters(max_concurrency=1)
    assert params.max_concurrency == 1


def test_generation_parameters_write_timeout_zero_raises():
    with pytest.raises(ValidationError):
        GenerationParameters(write_timeout=0)


def test_generation_parameters_write_timeout_one_passes():
    params = GenerationParameters(write_timeout=1)
    assert params.write_timeout == 1


def test_generation_parameters_defaults():
    params = GenerationParameters()
    assert params.keep_order is False
    assert params.max_concurrency == 100
    assert params.write_timeout == 10
    assert isinstance(params.batch, BatchParameters)
    assert isinstance(params.queue, QueueParameters)


# --- GeneratorParameters ---


def test_generator_parameters_required_fields():
    with pytest.raises(ValidationError):
        GeneratorParameters()


def test_generator_parameters_empty_id_raises():
    with pytest.raises(ValidationError):
        GeneratorParameters(id='', path=Path('config.yml'))


def test_generator_parameters_defaults():
    params = GeneratorParameters(id='gen1', path=Path('config.yml'))
    assert params.live_mode is True
    assert params.skip_past is True
    assert params.params == {}


def test_generator_parameters_as_absolute():
    params = GeneratorParameters(id='gen1', path=Path('config.yml'))
    abs_params = params.as_absolute(Path('/base/dir'))
    assert abs_params.path == Path('/base/dir/config.yml')
    assert abs_params.id == 'gen1'


def test_generator_parameters_as_absolute_already_absolute():
    params = GeneratorParameters(id='gen1', path=Path('/abs/config.yml'))
    result = params.as_absolute(Path('/base/dir'))
    assert result is params


def test_generator_parameters_as_relative():
    params = GeneratorParameters(
        id='gen1',
        path=Path('/base/dir/config.yml'),
    )
    rel_params = params.as_relative(Path('/base/dir'))
    assert rel_params.path == Path('config.yml')


def test_generator_parameters_as_relative_already_relative():
    params = GeneratorParameters(id='gen1', path=Path('config.yml'))
    result = params.as_relative(Path('/base/dir'))
    assert result is params


def test_generator_parameters_as_relative_non_parent_raises():
    params = GeneratorParameters(
        id='gen1',
        path=Path('/other/dir/config.yml'),
    )
    with pytest.raises(ValueError):
        params.as_relative(Path('/base/dir'))


def test_generator_parameters_frozen():
    params = GeneratorParameters(id='gen1', path=Path('config.yml'))
    with pytest.raises(ValidationError):
        params.id = 'gen2'
