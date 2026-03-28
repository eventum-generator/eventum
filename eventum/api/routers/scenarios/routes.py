"""Routes."""

import asyncio
from typing import Annotated

import aiofiles
import yaml
from fastapi import APIRouter, HTTPException, Path, status

from eventum.api.dependencies.app import SettingsDep
from eventum.api.routers.scenarios.dependencies import (
    CheckScenarioExistsDep,
    check_scenario_exists,
)
from eventum.api.routers.scenarios.models import ScenarioResponse
from eventum.api.routers.startup.dependencies import (
    StartupGeneratorsParametersListDep,
    get_startup_generator_parameters_list,
)
from eventum.api.utils.response_description import merge_responses

router = APIRouter()


@router.get(
    '/',
    description='List all scenarios',
)
async def list_scenarios(
    generators_parameters: StartupGeneratorsParametersListDep,
) -> list[str]:
    generators_parameters_model, _ = generators_parameters
    scenario_names: set[str] = set()

    for params in generators_parameters_model.root:
        for scenario in params.scenarios or []:
            scenario_names.add(scenario)

    return sorted(scenario_names)


@router.get(
    '/{name}',
    description='Get scenario details',
    responses=check_scenario_exists.responses,
)
async def get_scenario(
    name: CheckScenarioExistsDep,
    generators_parameters: StartupGeneratorsParametersListDep,
) -> ScenarioResponse:
    generators_parameters_model, _ = generators_parameters
    generator_ids = [
        params.id
        for params in generators_parameters_model.root
        if name in (params.scenarios or [])
    ]
    return ScenarioResponse(name=name, generator_ids=generator_ids)


@router.delete(
    '/{name}',
    description='Delete scenario (remove tag from all generators)',
    responses=merge_responses(
        check_scenario_exists.responses,
        get_startup_generator_parameters_list.responses,
        {500: {'description': 'Cannot modify startup file due to OS error'}},
    ),
)
async def delete_scenario(
    name: CheckScenarioExistsDep,
    generators_parameters: StartupGeneratorsParametersListDep,
    settings: SettingsDep,
) -> None:
    generators_parameters_model, generators_parameters_raw_content = (
        generators_parameters
    )

    for i, params in enumerate(generators_parameters_model.root):
        if name in (params.scenarios or []):
            raw_entry = generators_parameters_raw_content[i]
            scenarios = [s for s in raw_entry.get('scenarios', []) if s != name]
            if scenarios:
                raw_entry['scenarios'] = scenarios
            else:
                raw_entry.pop('scenarios', None)

    new_content = await asyncio.to_thread(
        lambda: yaml.dump(generators_parameters_raw_content, sort_keys=False),
    )

    try:
        async with aiofiles.open(settings.path.startup, 'w') as f:
            await f.write(new_content)
    except OSError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Cannot modify startup file due to OS error: {e}',
        ) from None


@router.post(
    '/{name}/generators/{generator_id}',
    description='Add generator to scenario',
    responses=merge_responses(
        get_startup_generator_parameters_list.responses,
        {404: {'description': 'Generator with this ID is not defined'}},
        {409: {'description': 'Generator is already in this scenario'}},
        {500: {'description': 'Cannot modify startup file due to OS error'}},
    ),
    status_code=status.HTTP_201_CREATED,
)
async def add_generator_to_scenario(
    name: Annotated[
        str, Path(description='Scenario name', min_length=1)
    ],
    generator_id: Annotated[
        str, Path(description='Generator ID', min_length=1)
    ],
    generators_parameters: StartupGeneratorsParametersListDep,
    settings: SettingsDep,
) -> None:
    generators_parameters_model, generators_parameters_raw_content = (
        generators_parameters
    )

    target_index: int | None = None
    for i, params in enumerate(generators_parameters_model.root):
        if params.id == generator_id:
            target_index = i
            break

    if target_index is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Generator with this ID is not defined',
        )

    target_params = generators_parameters_model.root[target_index]
    if name in (target_params.scenarios or []):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Generator is already in this scenario',
        )

    raw_entry = generators_parameters_raw_content[target_index]
    scenarios = raw_entry.get('scenarios', [])
    scenarios.append(name)
    raw_entry['scenarios'] = scenarios

    new_content = await asyncio.to_thread(
        lambda: yaml.dump(generators_parameters_raw_content, sort_keys=False),
    )

    try:
        async with aiofiles.open(settings.path.startup, 'w') as f:
            await f.write(new_content)
    except OSError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Cannot modify startup file due to OS error: {e}',
        ) from None


@router.delete(
    '/{name}/generators/{generator_id}',
    description='Remove generator from scenario',
    responses=merge_responses(
        check_scenario_exists.responses,
        get_startup_generator_parameters_list.responses,
        {404: {'description': 'Generator with this ID is not in this scenario'}},
        {500: {'description': 'Cannot modify startup file due to OS error'}},
    ),
)
async def remove_generator_from_scenario(
    name: CheckScenarioExistsDep,
    generator_id: Annotated[
        str, Path(description='Generator ID', min_length=1)
    ],
    generators_parameters: StartupGeneratorsParametersListDep,
    settings: SettingsDep,
) -> None:
    generators_parameters_model, generators_parameters_raw_content = (
        generators_parameters
    )

    target_index: int | None = None
    for i, params in enumerate(generators_parameters_model.root):
        if params.id == generator_id and name in (params.scenarios or []):
            target_index = i
            break

    if target_index is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Generator with this ID is not in this scenario',
        )

    raw_entry = generators_parameters_raw_content[target_index]
    scenarios = [s for s in raw_entry.get('scenarios', []) if s != name]
    if scenarios:
        raw_entry['scenarios'] = scenarios
    else:
        raw_entry.pop('scenarios', None)

    new_content = await asyncio.to_thread(
        lambda: yaml.dump(generators_parameters_raw_content, sort_keys=False),
    )

    try:
        async with aiofiles.open(settings.path.startup, 'w') as f:
            await f.write(new_content)
    except OSError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Cannot modify startup file due to OS error: {e}',
        ) from None
