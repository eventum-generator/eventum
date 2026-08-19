"""Tests for preview router endpoints."""

from datetime import datetime
from typing import override

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from eventum.api.routers.preview import router
from eventum.api.routers.preview.plugins_storage import EVENT_PLUGINS
from eventum.app.models.parameters.log import LogParameters
from eventum.app.models.parameters.path import PathParameters
from eventum.app.models.parameters.server import ServerParameters
from eventum.app.models.settings import Settings
from eventum.core.parameters import GenerationParameters
from eventum.plugins.event.base.config import EventPluginConfig
from eventum.plugins.event.base.plugin import (
    EventPlugin,
    EventPluginParams,
    ProduceParams,
)


class EchoEventPluginConfig(EventPluginConfig, frozen=True):
    """Config of echoing event plugin."""


class EchoEventPlugin(
    EventPlugin[EchoEventPluginConfig, EventPluginParams],
    register=False,
):
    """Event plugin that echoes the params it was called with."""

    @override
    def __init__(
        self,
        config: EchoEventPluginConfig,
        params: EventPluginParams,
    ) -> None:
        super().__init__(config, params)

        self.calls: list[ProduceParams] = []

    @override
    def _produce(self, params: ProduceParams) -> list[str]:
        self.calls.append(params)

        return [f'{params["timestamp"].isoformat()} {list(params["tags"])}']


@pytest.fixture
def plugin(tmp_path):
    settings = Settings(
        server=ServerParameters(),
        generation=GenerationParameters(),
        log=LogParameters(),
        path=PathParameters(
            logs=tmp_path / 'logs',
            startup=tmp_path / 'startup.yml',
            generators_dir=tmp_path / 'generators',
            keyring_cryptfile=tmp_path / 'keyring.cfg',
        ),
    )
    gen_dir = settings.path.generators_dir / 'gen-1'
    gen_dir.mkdir(parents=True)
    (gen_dir / settings.path.generator_config_filename).write_text('{}')

    plugin = EchoEventPlugin(
        config=EchoEventPluginConfig(),
        params={'id': 1, 'base_path': gen_dir},
    )
    EVENT_PLUGINS.set(path=gen_dir.resolve(), plugin=plugin)

    app = FastAPI()
    app.state.settings = settings
    app.include_router(router, prefix='/preview')

    with TestClient(app) as client:
        yield plugin, client

    EVENT_PLUGINS.remove(path=gen_dir.resolve())


def test_produce_passes_body_to_plugin(plugin):
    echo, client = plugin

    response = client.post(
        '/preview/gen-1/event-plugin/produce',
        json=[
            {'timestamp': '2026-02-20T10:00:00+00:00', 'tags': ['a', 'b']},
            {'timestamp': '2026-02-20T10:00:01+00:00', 'tags': []},
        ],
    )

    assert response.status_code == 200
    assert response.json()['events'] == [
        "2026-02-20T10:00:00+00:00 ['a', 'b']",
        '2026-02-20T10:00:01+00:00 []',
    ]

    assert [call['tags'] for call in echo.calls] == [('a', 'b'), ()]
    assert echo.calls[0]['timestamp'] == datetime.fromisoformat(
        '2026-02-20T10:00:00+00:00'
    )


def test_produce_rejects_body_without_timestamp(plugin):
    _, client = plugin

    response = client.post(
        '/preview/gen-1/event-plugin/produce',
        json=[{'tags': ['a']}],
    )

    assert response.status_code == 422
