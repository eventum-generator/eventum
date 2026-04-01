"""Routes."""

import asyncio
from pathlib import Path
from typing import Annotated, Any

import aiofiles
import structlog
import yaml
from fastapi import APIRouter, Body, HTTPException, status
from fastapi import Path as FastApiPath
from jinja2 import TemplateSyntaxError

from eventum.api.dependencies.app import SettingsDep
from eventum.api.routers.generator_configs.globals_detector import (
    GlobalsUsage,
    detect_globals_usage,
)
from eventum.api.routers.scenarios.dependencies import (
    CheckScenarioExistsDep,
    check_scenario_exists,
)
from eventum.api.routers.scenarios.models import (
    GlobalsReferenceResponse,
    GlobalsUsageResponse,
    GlobalsWarningResponse,
    ScenarioResponse,
)
from eventum.api.routers.startup.dependencies import (
    StartupGeneratorsParametersListDep,
    get_startup_generator_parameters_list,
)
from eventum.api.utils.response_description import merge_responses
from eventum.plugins.event.plugins.template.plugin import TemplateEventPlugin
from eventum.utils.json_utils import normalize_types

logger = structlog.stdlib.get_logger()

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
            scenarios = [
                s for s in raw_entry.get('scenarios', []) if s != name
            ]
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
        str, FastApiPath(description='Scenario name', min_length=1)
    ],
    generator_id: Annotated[
        str, FastApiPath(description='Generator ID', min_length=1)
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
        {
            404: {
                'description': 'Generator with this ID is not in this scenario'
            }
        },
        {500: {'description': 'Cannot modify startup file due to OS error'}},
    ),
)
async def remove_generator_from_scenario(
    name: CheckScenarioExistsDep,
    generator_id: Annotated[
        str, FastApiPath(description='Generator ID', min_length=1)
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


@router.get(
    '/{name}/generators/{generator_name}/globals-usage',
    summary='Get globals usage for a generator in a scenario',
    description=(
        'Detect globals.set/get usage in Jinja2 templates via AST analysis.'
    ),
    responses=merge_responses(
        check_scenario_exists.responses,
        {
            403: {
                'description': (
                    'Accessing directories outside'
                    ' generators_dir is not allowed'
                )
            },
            404: {'description': 'Generator configuration not found'},
        },
    ),
)
async def get_generator_globals_usage(
    name: CheckScenarioExistsDep,  # noqa: ARG001
    generator_name: Annotated[
        str,
        FastApiPath(description='Generator config name', min_length=1),
    ],
    settings: SettingsDep,
) -> GlobalsUsageResponse:
    generator_dir = (settings.path.generators_dir / generator_name).resolve()

    if not generator_dir.is_relative_to(settings.path.generators_dir):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                'Accessing directories outside generators_dir is not allowed'
            ),
        )

    if not generator_dir.is_dir():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Generator configuration not found: {generator_name}',
        )
    usage = GlobalsUsage()

    template_files: list[tuple[Path, str]] = []
    for pattern in ('**/*.j2', '**/*.jinja'):
        for filepath in generator_dir.glob(pattern):
            if filepath.is_file():
                rel_path = str(filepath.relative_to(generator_dir))
                template_files.append((filepath, rel_path))

    for filepath, rel_path in template_files:
        try:
            async with aiofiles.open(filepath, encoding='utf-8') as f:
                source = await f.read()
            template_usage = await asyncio.to_thread(
                detect_globals_usage, source, rel_path
            )
            usage.merge(template_usage)
        except OSError:
            logger.warning('Failed to read template file', path=str(filepath))
        except TemplateSyntaxError:
            logger.warning('Failed to parse template file', path=str(filepath))

    return GlobalsUsageResponse(
        writes=[
            GlobalsReferenceResponse.model_validate(w, from_attributes=True)
            for w in usage.writes
        ],
        reads=[
            GlobalsReferenceResponse.model_validate(r, from_attributes=True)
            for r in usage.reads
        ],
        warnings=[
            GlobalsWarningResponse.model_validate(w, from_attributes=True)
            for w in usage.warnings
        ],
    )


@router.get(
    '/{name}/globals/{key}',
    description='Get a specific global state key value',
    responses=merge_responses(
        check_scenario_exists.responses,
        {404: {'description': 'Key not found in global state'}},
    ),
)
async def get_scenario_global_state_key(
    name: CheckScenarioExistsDep,  # noqa: ARG001
    key: Annotated[
        str,
        FastApiPath(
            description='Key to get from global state',
            min_length=1,
        ),
    ],
) -> Any:
    value = await asyncio.to_thread(TemplateEventPlugin.GLOBAL_STATE.get, key)
    if value is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Key not found in global state: {key}',
        )
    try:
        return await asyncio.to_thread(lambda: normalize_types(value))
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to serialize global state value: {e}',
        ) from None


@router.get(
    '/{name}/globals',
    description='Get global state shared across all template event plugins',
    responses=merge_responses(
        check_scenario_exists.responses,
        {500: {'description': 'Failed to serialize global state'}},
    ),
)
async def get_scenario_global_state(
    name: CheckScenarioExistsDep,  # noqa: ARG001
) -> dict[str, Any]:
    try:
        return await asyncio.to_thread(
            lambda: normalize_types(
                TemplateEventPlugin.GLOBAL_STATE.as_dict()
            ),
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Failed to serialize global state: {e}',
        ) from None


@router.patch(
    '/{name}/globals',
    description='Update global state shared across all template event plugins',
    responses=check_scenario_exists.responses,
)
async def update_scenario_global_state(
    name: CheckScenarioExistsDep,  # noqa: ARG001
    content: Annotated[
        dict[str, Any],
        Body(description='Content to patch in global state'),
    ],
) -> None:
    await asyncio.to_thread(TemplateEventPlugin.GLOBAL_STATE.update, content)


@router.delete(
    '/{name}/globals/{key}',
    description='Delete a key from global state',
    responses=check_scenario_exists.responses,
)
async def delete_scenario_global_state_key(
    name: CheckScenarioExistsDep,  # noqa: ARG001
    key: Annotated[
        str,
        FastApiPath(
            description='Key to delete from global state', min_length=1
        ),
    ],
) -> None:
    await asyncio.to_thread(TemplateEventPlugin.GLOBAL_STATE.pop, key)


@router.delete(
    '/{name}/globals',
    description='Clear global state shared across all template event plugins',
    responses=check_scenario_exists.responses,
)
async def clear_scenario_global_state(
    name: CheckScenarioExistsDep,  # noqa: ARG001
) -> None:
    await asyncio.to_thread(TemplateEventPlugin.GLOBAL_STATE.clear)
