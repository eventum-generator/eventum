"""Routes."""

import asyncio
from pathlib import Path
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Body, HTTPException, status
from fastapi import Path as FastApiPath

from eventum.api.dependencies.app import SettingsDep, StartupDep
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
    RenameScenarioRequest,
    ScenarioResponse,
)
from eventum.api.utils.response_description import merge_responses
from eventum.app.startup import (
    ScenarioConflictError,
    ScenarioNotFoundError,
    StartupError,
    StartupNotFoundError,
)
from eventum.app.workspace import WorkspaceError, resolve_generator_dir
from eventum.plugins.event.plugins.template.plugin import TemplateEventPlugin
from eventum.utils.json_utils import normalize_types

logger = structlog.stdlib.get_logger()

router = APIRouter()

_TEMPLATE_SUFFIXES = ('.j2', '.jinja')

_STARTUP_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    500: {
        'description': (
            'Startup file cannot be read, parsed, validated, or written'
        ),
    },
}


def _collect_globals_usage(generator_dir: Path) -> GlobalsUsage:
    """Scan a generator directory for Jinja2 templates and detect
    globals usage across all of them.

    Walks the directory tree once, reads each template, and runs AST
    detection. Performs blocking filesystem IO and CPU-bound parsing,
    so it must run in a worker thread to avoid blocking the event
    loop.

    Parameters
    ----------
    generator_dir : Path
        Resolved generator directory to scan.

    Returns
    -------
    GlobalsUsage
        Merged writes, reads, and warnings from all templates.

    """
    usage = GlobalsUsage()

    for filepath in generator_dir.rglob('*'):
        if filepath.suffix not in _TEMPLATE_SUFFIXES or not filepath.is_file():
            continue

        rel_path = str(filepath.relative_to(generator_dir))
        try:
            source = filepath.read_text(encoding='utf-8')
        except OSError:
            logger.warning('Failed to read template file', path=str(filepath))
            continue

        usage.merge(detect_globals_usage(source, rel_path))

    return usage


@router.get(
    '/',
    description='List all scenarios',
    responses=_STARTUP_ERROR_RESPONSES,
)
async def list_scenarios(startup: StartupDep) -> list[str]:
    try:
        return await asyncio.to_thread(startup.list_scenarios)
    except StartupError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from None


@router.get(
    '/{name}',
    description='Get scenario details',
    responses=merge_responses(
        _STARTUP_ERROR_RESPONSES,
        {404: {'description': 'Scenario not found'}},
    ),
)
async def get_scenario(
    name: Annotated[
        str, FastApiPath(description='Scenario name', min_length=1)
    ],
    startup: StartupDep,
) -> ScenarioResponse:
    try:
        generator_ids = await asyncio.to_thread(
            startup.get_scenario_generators, name
        )
    except StartupError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from None
    if not generator_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Scenario not found: {name}',
        )
    return ScenarioResponse(name=name, generator_ids=generator_ids)


@router.post(
    '/{name}/rename',
    description=(
        'Rename scenario (rewrite tag in all generators that carry it)'
    ),
    responses=merge_responses(
        _STARTUP_ERROR_RESPONSES,
        {404: {'description': 'Scenario not found'}},
        {409: {'description': 'Scenario with the new name already exists'}},
    ),
)
async def rename_scenario(
    name: Annotated[
        str, FastApiPath(description='Scenario name', min_length=1)
    ],
    request: Annotated[
        RenameScenarioRequest,
        Body(description='New scenario name'),
    ],
    startup: StartupDep,
) -> None:
    try:
        await asyncio.to_thread(
            startup.rename_scenario, name, request.new_name
        )
    except ScenarioNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Scenario not found: {name}',
        ) from None
    except ScenarioConflictError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f'Scenario already exists: {request.new_name}',
        ) from None
    except StartupError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from None


@router.delete(
    '/{name}',
    description='Delete scenario (remove tag from all generators)',
    responses=merge_responses(
        _STARTUP_ERROR_RESPONSES,
        {404: {'description': 'Scenario not found'}},
    ),
)
async def delete_scenario(
    name: Annotated[
        str, FastApiPath(description='Scenario name', min_length=1)
    ],
    startup: StartupDep,
) -> None:
    try:
        await asyncio.to_thread(startup.delete_scenario, name)
    except ScenarioNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Scenario not found: {name}',
        ) from None
    except StartupError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from None


@router.post(
    '/{name}/generators/{generator_id}',
    description='Add generator to scenario',
    responses=merge_responses(
        _STARTUP_ERROR_RESPONSES,
        {404: {'description': 'Generator with this ID is not defined'}},
        {409: {'description': 'Generator is already in this scenario'}},
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
    startup: StartupDep,
) -> None:
    try:
        await asyncio.to_thread(startup.tag_scenario, generator_id, name)
    except StartupNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Generator with this ID is not defined',
        ) from None
    except ScenarioConflictError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Generator is already in this scenario',
        ) from None
    except StartupError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from None


@router.delete(
    '/{name}/generators/{generator_id}',
    description='Remove generator from scenario',
    responses=merge_responses(
        _STARTUP_ERROR_RESPONSES,
        {
            404: {
                'description': 'Generator with this ID is not in this scenario'
            }
        },
    ),
)
async def remove_generator_from_scenario(
    name: Annotated[
        str, FastApiPath(description='Scenario name', min_length=1)
    ],
    generator_id: Annotated[
        str, FastApiPath(description='Generator ID', min_length=1)
    ],
    startup: StartupDep,
) -> None:
    try:
        await asyncio.to_thread(startup.untag_scenario, generator_id, name)
    except ScenarioNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Generator with this ID is not in this scenario',
        ) from None
    except StartupError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
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
    try:
        generator_dir = resolve_generator_dir(
            settings.path.generators_dir, generator_name
        )
    except WorkspaceError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                'Accessing directories outside generators_dir is not allowed'
            ),
        ) from None

    if not generator_dir.is_dir():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Generator configuration not found: {generator_name}',
        )

    usage = await asyncio.to_thread(_collect_globals_usage, generator_dir)

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
