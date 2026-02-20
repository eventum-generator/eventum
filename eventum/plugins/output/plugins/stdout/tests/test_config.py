"""Tests for stdout output plugin config."""

import pytest
from pydantic import ValidationError

from eventum.plugins.output.plugins.stdout.config import (
    StdoutOutputPluginConfig,
)


def test_defaults():
    config = StdoutOutputPluginConfig()
    assert config.stream == 'stdout'
    assert config.encoding == 'utf_8'
    assert config.flush_interval == 1


def test_stream_stdout():
    config = StdoutOutputPluginConfig(stream='stdout')
    assert config.stream == 'stdout'


def test_stream_stderr():
    config = StdoutOutputPluginConfig(stream='stderr')
    assert config.stream == 'stderr'


def test_invalid_stream():
    with pytest.raises(ValidationError):
        StdoutOutputPluginConfig(stream='invalid')


def test_flush_interval_zero():
    config = StdoutOutputPluginConfig(flush_interval=0)
    assert config.flush_interval == 0


def test_flush_interval_negative():
    with pytest.raises(ValidationError):
        StdoutOutputPluginConfig(flush_interval=-1)
