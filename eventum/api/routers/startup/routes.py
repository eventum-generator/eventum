"""Routes."""

import asyncio
from typing import Annotated

import aiofiles
import yaml
from fastapi import APIRouter, Body, HTTPException, status

from eventum.api.dependencies.app import SettingsDep
from eventum.api.routers.startup.dependencies import (
    CheckIdInBodyMatchPathDep,
    StartupGeneratorParametersListRaw,
    StartupGeneratorsParametersListDep,
    TargetStartupParamsIndexDep,
    TargetStartupParamsIndexesDep,
    check_id_in_body_match_path,
    get_startup_generator_parameters_list,
    get_target_startup_params_index,
    get_target_startup_params_indexes,
)
from eventum.api.routers.startup.utils import move_key_to_first_position
from eventum.api.utils.response_description import merge_responses
from eventum.app.models.generators import (
    StartupGeneratorParameters,
    StartupGeneratorParametersList,
)

router = APIRouter()


@router.get(
    '/',
    description='Get list of generator definitions in the startup file',
    response_description=(
        'List of parameters of generators in the startup file. '
        'Note that response also includes default parameters '
        'even if they are not set in the file.'
    ),
    responses=get_startup_generator_parameters_list.responses,
)
async def get_generators_in_startup(
    generators_parameters: StartupGeneratorsParametersListDep,
    settings: SettingsDep,
) -> StartupGeneratorParametersList:
    generators_parameters_model, _ = generators_parameters

    normalized_params_list: list[StartupGeneratorParameters] = []
    for params in generators_parameters_model.root:
        try:
            normalized_params = params.as_relative(
                base_dir=settings.path.generators_dir,
            )
        except ValueError:
            normalized_params = params

        normalized_params_list.append(normalized_params)

    return StartupGeneratorParametersList(root=tuple(normalized_params_list))


@router.get(
    '/{id}',
    description='Get generator definition from list in the startup file',
    response_description=(
        'Parameters of generator from the startup file. '
        'Note that response also includes default parameters '
        'even if they are not set in the file.'
    ),
    responses=merge_responses(
        get_startup_generator_parameters_list.responses,
        get_target_startup_params_index.responses,
    ),
)
async def get_generator_from_startup(
    generators_parameters: StartupGeneratorsParametersListDep,
    target_index: TargetStartupParamsIndexDep,
    settings: SettingsDep,
) -> StartupGeneratorParameters:
    generators_parameters_model, _ = generators_parameters

    target_params = generators_parameters_model.root[target_index]
    try:
        return target_params.as_relative(base_dir=settings.path.generators_dir)
    except ValueError:
        return target_params


@router.post(
    '/{id}',
    description='Add generator definition to list in the startup file',
    responses=merge_responses(
        get_startup_generator_parameters_list.responses,
        check_id_in_body_match_path.responses,
        {409: {'description': 'Generator with this ID is already defined'}},
        {
            500: {
                'description': (
                    'Cannot append updated content to startup file '
                    'due to OS error'
                ),
            },
        },
    ),
    status_code=status.HTTP_201_CREATED,
)
async def add_generator_to_startup(
    id: Annotated[str, CheckIdInBodyMatchPathDep],
    params: Annotated[
        StartupGeneratorParameters,
        Body(description='Generator parameters'),
    ],
    generators_parameters: StartupGeneratorsParametersListDep,
    settings: SettingsDep,
) -> None:
    generators_parameters_model, generators_parameters_raw_content = (
        generators_parameters
    )

    for startup_params in generators_parameters_model.root:
        if id == startup_params.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    'Generator with this ID is already defined '
                    f'({startup_params.path})'
                ),
            )

    new_content = await asyncio.to_thread(
        lambda: yaml.dump(
            [
                *generators_parameters_raw_content,
                move_key_to_first_position(
                    params.as_absolute(
                        base_dir=settings.path.generators_dir,
                    ).model_dump(mode='json', exclude_unset=True),
                    'id',
                ),
            ],
            sort_keys=False,
        ),
    )

    try:
        async with aiofiles.open(settings.path.startup, 'w') as f:
            await f.write(new_content)
    except OSError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                'Cannot append updated content to startup file '
                f'due to OS error: {e}'
            ),
        ) from None


@router.put(
    '/{id}',
    description='Update generator definition in list in the startup file',
    responses=merge_responses(
        get_startup_generator_parameters_list.responses,
        get_target_startup_params_index.responses,
        check_id_in_body_match_path.responses,
        {
            500: {
                'description': ('Cannot modify startup file due to OS error'),
            },
        },
    ),
)
async def update_generator_in_startup(
    id: Annotated[str, CheckIdInBodyMatchPathDep],  # noqa: ARG001
    params: Annotated[
        StartupGeneratorParameters,
        Body(description='Startup generator parameters'),
    ],
    target_index: TargetStartupParamsIndexDep,
    generators_parameters: StartupGeneratorsParametersListDep,
    settings: SettingsDep,
) -> None:
    _, generators_parameters_raw_content = generators_parameters

    generators_parameters_raw_content[target_index] = (
        move_key_to_first_position(
            params.as_absolute(
                base_dir=settings.path.generators_dir,
            ).model_dump(
                mode='json',
                exclude_unset=True,
            ),
            'id',
        )
    )
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
    '/{id}',
    description='Delete generator definition from list in the startup file',
    responses=merge_responses(
        get_startup_generator_parameters_list.responses,
        get_target_startup_params_index.responses,
        {
            500: {
                'description': 'Cannot modify startup file due to OS error',
            },
        },
    ),
)
async def delete_generator_from_startup(
    generators_parameters: StartupGeneratorsParametersListDep,
    target_index: TargetStartupParamsIndexDep,
    settings: SettingsDep,
) -> None:
    _, generators_parameters_raw_content = generators_parameters

    del generators_parameters_raw_content[target_index]
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
    '/group-actions/bulk-delete',
    description=(
        'Bulk delete several generator definitions from list in the '
        'startup file'
    ),
    response_description='IDs of deleted generator definitions',
    responses=merge_responses(
        get_startup_generator_parameters_list.responses,
        get_target_startup_params_indexes.responses,
        {
            500: {
                'description': 'Cannot modify startup file due to OS error',
            },
        },
    ),
)
async def bulk_delete_generators_from_startup(
    generators_parameters: StartupGeneratorsParametersListDep,
    target_indexes: TargetStartupParamsIndexesDep,
    settings: SettingsDep,
) -> list[str]:
    _, generators_parameters_raw_content = generators_parameters

    deleted_ids: list[str] = []
    new_raw_content: StartupGeneratorParametersListRaw = []

    for index, params in enumerate(generators_parameters_raw_content):
        if index in target_indexes:
            deleted_ids.append(params['id'])
        else:
            new_raw_content.append(params)

    new_content = await asyncio.to_thread(
        lambda: yaml.dump(new_raw_content, sort_keys=False),
    )

    try:
        async with aiofiles.open(settings.path.startup, 'w') as f:
            await f.write(new_content)
    except OSError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Cannot modify startup file due to OS error: {e}',
        ) from None

    return deleted_ids
