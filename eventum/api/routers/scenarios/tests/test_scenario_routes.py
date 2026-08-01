"""Tests for the scenario-tag endpoints of the scenarios router."""

from collections.abc import Iterator
from http import HTTPStatus
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from eventum.api.routers.scenarios import router
from eventum.app.models.parameters.log import LogParameters
from eventum.app.models.parameters.path import PathParameters
from eventum.app.models.parameters.server import ServerParameters
from eventum.app.models.settings import Settings
from eventum.app.startup import Startup
from eventum.core.parameters import GenerationParameters

_STARTUP = (
    '- id: gen-1\n  path: gen-1/generator.yml\n  scenarios:\n'
    '    - myscenario\n'
    '- id: gen-2\n  path: gen-2/generator.yml\n'
)


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    """Build a TestClient over the scenarios router with a Startup."""
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
    settings.path.generators_dir.mkdir()
    settings.path.startup.write_text(_STARTUP)

    app = FastAPI()
    app.state.settings = settings
    app.state.startup = Startup(
        file_path=settings.path.startup,
        generators_dir=settings.path.generators_dir,
        generation_parameters=settings.generation,
    )
    app.include_router(router, prefix='/scenarios')
    with TestClient(app) as test_client:
        yield test_client


def test_list_scenarios(client: TestClient) -> None:
    """Listing returns the scenario names."""
    response = client.get('/scenarios/')

    assert response.status_code == HTTPStatus.OK
    assert response.json() == ['myscenario']


def test_get_scenario(client: TestClient) -> None:
    """Getting a scenario returns its generator ids."""
    response = client.get('/scenarios/myscenario')

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {
        'name': 'myscenario',
        'generator_ids': ['gen-1'],
    }


def test_get_scenario_unknown_is_404(client: TestClient) -> None:
    """An unknown scenario is a 404."""
    response = client.get('/scenarios/absent')

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_add_generator_to_scenario(client: TestClient) -> None:
    """Adding a generator returns 201 and tags it."""
    response = client.post('/scenarios/myscenario/generators/gen-2')

    assert response.status_code == HTTPStatus.CREATED
    assert client.get('/scenarios/myscenario').json()['generator_ids'] == [
        'gen-1',
        'gen-2',
    ]


def test_add_generator_unknown_is_404(client: TestClient) -> None:
    """Adding an undefined generator is a 404."""
    response = client.post('/scenarios/myscenario/generators/absent')

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_add_generator_already_in_scenario_is_409(client: TestClient) -> None:
    """Adding a generator already in the scenario is a 409."""
    response = client.post('/scenarios/myscenario/generators/gen-1')

    assert response.status_code == HTTPStatus.CONFLICT


def test_remove_generator_from_scenario(client: TestClient) -> None:
    """Removing a generator untags it."""
    response = client.delete('/scenarios/myscenario/generators/gen-1')

    assert response.status_code == HTTPStatus.OK
    assert client.get('/scenarios/').json() == []


def test_remove_generator_not_in_scenario_is_404(client: TestClient) -> None:
    """Removing a generator not in the scenario is a 404."""
    response = client.delete('/scenarios/myscenario/generators/gen-2')

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_delete_scenario(client: TestClient) -> None:
    """Deleting a scenario untags every member."""
    response = client.delete('/scenarios/myscenario')

    assert response.status_code == HTTPStatus.OK
    assert client.get('/scenarios/').json() == []


def test_delete_scenario_unknown_is_404(client: TestClient) -> None:
    """Deleting an unknown scenario is a 404."""
    response = client.delete('/scenarios/absent')

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_rename_scenario(client: TestClient) -> None:
    """Renaming a scenario rewrites the tag of every member."""
    response = client.post(
        '/scenarios/myscenario/rename',
        json={'new_name': 'renamed'},
    )

    assert response.status_code == HTTPStatus.OK
    assert client.get('/scenarios/').json() == ['renamed']
    assert client.get('/scenarios/renamed').json()['generator_ids'] == [
        'gen-1'
    ]


def test_rename_scenario_unknown_is_404(client: TestClient) -> None:
    """Renaming an unknown scenario is a 404."""
    response = client.post(
        '/scenarios/absent/rename',
        json={'new_name': 'renamed'},
    )

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_rename_scenario_taken_name_is_409(client: TestClient) -> None:
    """Renaming onto an existing scenario is a 409."""
    client.post('/scenarios/other/generators/gen-2')

    response = client.post(
        '/scenarios/myscenario/rename',
        json={'new_name': 'other'},
    )

    assert response.status_code == HTTPStatus.CONFLICT
    assert client.get('/scenarios/').json() == ['myscenario', 'other']


def test_rename_scenario_blank_name_is_422(client: TestClient) -> None:
    """A blank new name fails request validation."""
    response = client.post(
        '/scenarios/myscenario/rename',
        json={'new_name': ''},
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT
