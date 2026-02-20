"""Tests for pydantic to click converter."""

from typing import Literal

import click
import click.types as click_types
import pytest
from click.testing import CliRunner
from pydantic import BaseModel, Field

from eventum.cli.pydantic_converter import (
    _get_type_for_annotation,
    _patch_error_locations,
    _strip_none_values,
    build_arg_name,
    build_object_from_args,
    build_option_name,
    from_model,
)


class Config(BaseModel):
    """Config.

    Attributes
    ----------
    name : str
        User name.
    """

    name: str


@click.command()
@from_model(Config)
def cli(config: Config):
    click.echo(f'Hello {config.name}')


def test_cli_valid():
    runner = CliRunner()
    result = runner.invoke(cli, ['--name', 'Alice'])
    assert result.exit_code == 0
    assert 'Hello Alice' in result.output


def test_cli_invalid():
    runner = CliRunner()
    result = runner.invoke(cli, [])
    assert result.exit_code != 0
    assert "Missing option '--name'" in result.output


def test_parse_docstring_extracts_field_doc():
    runner = CliRunner()
    result = runner.invoke(cli, ['--help'])
    assert result.exit_code == 0
    assert 'User name' in result.output


# --- build_arg_name ---


def test_build_arg_name():
    assert build_arg_name(['server', 'port']) == 'server__port'


def test_build_arg_name_single():
    assert build_arg_name(['name']) == 'name'


def test_build_arg_name_empty_raises():
    with pytest.raises(ValueError, match='At least one field'):
        build_arg_name([])


# --- build_option_name ---


def test_build_option_name():
    assert build_option_name(['server', 'port']) == '--server.port'


def test_build_option_name_with_underscores():
    assert build_option_name(['live_mode']) == '--live-mode'


def test_build_option_name_empty_raises():
    with pytest.raises(ValueError, match='At least one field'):
        build_option_name([])


# --- build_object_from_args ---


def test_build_object_from_args_flat():
    result = build_object_from_args(name='Alice')
    assert result == {'name': 'Alice'}


def test_build_object_from_args_nested():
    result = build_object_from_args(
        server__port=8080, server__host='localhost'
    )
    assert result == {'server': {'port': 8080, 'host': 'localhost'}}


# --- _get_type_for_annotation ---


def test_get_type_for_annotation_optional_int():
    result = _get_type_for_annotation(int | None)
    assert result is int


def test_get_type_for_annotation_literal():
    result = _get_type_for_annotation(Literal['a', 'b'])
    assert isinstance(result, click_types.Choice)


def test_get_type_for_annotation_plain():
    result = _get_type_for_annotation(str)
    assert result is str


# --- _strip_none_values ---


def test_strip_none_values_removes_nones():
    result = _strip_none_values({'a': 1, 'b': None, 'c': 'x'})
    assert result == {'a': 1, 'c': 'x'}


def test_strip_none_values_recursive():
    result = _strip_none_values({'a': {'b': None, 'c': 1}, 'd': None})
    assert result == {'a': {'c': 1}}


def test_strip_none_values_removes_empty_sub_dict():
    result = _strip_none_values({'a': {'b': None}})
    assert result == {}


# --- _patch_error_locations ---


def test_patch_error_locations():
    errors = [
        {'loc': ('live_mode',), 'msg': 'err', 'type': 'value_error'},
    ]
    _patch_error_locations(errors)
    assert errors[0]['loc'] == ('--live-mode',)


def test_patch_error_locations_nested():
    errors = [
        {'loc': ('server', 'port'), 'msg': 'err', 'type': 'value_error'},
    ]
    _patch_error_locations(errors)
    assert errors[0]['loc'] == ('--server', 'port')


# --- Nested model ---


class Inner(BaseModel):
    """Inner.

    Attributes
    ----------
    port : int
        Port number.
    """

    port: int = Field(default=8080)


class Outer(BaseModel):
    """Outer.

    Attributes
    ----------
    host : str
        Host name.

    inner : Inner
        Inner settings.
    """

    host: str
    inner: Inner = Field(default_factory=Inner)


@click.command()
@from_model(Outer)
def nested_cli(outer: Outer):
    click.echo(f'{outer.host}:{outer.inner.port}')


def test_nested_model_flattened_options():
    runner = CliRunner()
    result = runner.invoke(
        nested_cli,
        ['--host', 'localhost', '--inner.port', '9090'],
    )
    assert result.exit_code == 0
    assert 'localhost:9090' in result.output


def test_nested_model_uses_defaults():
    runner = CliRunner()
    result = runner.invoke(nested_cli, ['--host', 'localhost'])
    assert result.exit_code == 0
    assert 'localhost:8080' in result.output
