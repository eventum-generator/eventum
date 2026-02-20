"""Tests for API application building."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI

from eventum.api.exceptions import APISchemaGenerationError
from eventum.api.main import build_api_app
from eventum.app.manager import GeneratorManager
from eventum.app.models.parameters.log import LogParameters
from eventum.app.models.parameters.path import PathParameters
from eventum.app.models.parameters.server import (
    AuthParameters,
    ServerParameters,
)
from eventum.app.models.settings import Settings
from eventum.core.parameters import GenerationParameters


@pytest.fixture()
def settings(tmp_path):
    return Settings(
        server=ServerParameters(
            auth=AuthParameters(user='admin', password='secret'),
        ),
        generation=GenerationParameters(),
        log=LogParameters(),
        path=PathParameters(
            logs=tmp_path / 'logs',
            startup=tmp_path / 'startup.yml',
            generators_dir=tmp_path / 'generators',
            keyring_cryptfile=tmp_path / 'keyring.dat',
        ),
    )


@pytest.fixture()
def hooks(tmp_path):
    return {
        'get_settings_file_path': lambda: tmp_path / 'settings.yml',
        'terminate': MagicMock(),
        'restart': MagicMock(),
    }


def test_build_api_app_returns_fastapi(settings, hooks):
    app = build_api_app(
        generator_manager=GeneratorManager(),
        settings=settings,
        instance_hooks=hooks,
    )
    assert isinstance(app, FastAPI)


def test_build_api_app_has_routers(settings, hooks):
    app = build_api_app(
        generator_manager=GeneratorManager(),
        settings=settings,
        instance_hooks=hooks,
    )
    paths = [route.path for route in app.routes]
    assert any('/auth' in p for p in paths)
    assert any('/generators' in p for p in paths)
    assert any('/instance' in p for p in paths)
    assert any('/startup' in p for p in paths)
    assert any('/secrets' in p for p in paths)


def test_build_api_app_schema_error(settings, hooks):
    with (
        patch(
            'eventum.api.main.register_asyncapi_schema',
            side_effect=RuntimeError('schema fail'),
        ),
        pytest.raises(APISchemaGenerationError),
    ):
        build_api_app(
            generator_manager=GeneratorManager(),
            settings=settings,
            instance_hooks=hooks,
        )
