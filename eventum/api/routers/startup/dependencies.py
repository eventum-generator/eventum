"""Dependencies."""

import asyncio
from typing import Annotated

import aiofiles
import yaml
from fastapi import Body, Depends, HTTPException, Path, status
from pydantic import ValidationError

from eventum.api.dependencies.app import SettingsDep
from eventum.api.utils.response_description import (
    merge_responses,
    set_responses,
)
from eventum.app.models.generators import (
    StartupGeneratorParameters,
    StartupGeneratorParametersList,
)
from eventum.utils.validation_prettier import prettify_validation_errors

type StartupGeneratorParametersListRaw = list[dict]


@set_responses(
    merge_responses(
        {500: {'description': 'Cannot read startup file due to OS error'}},
        {500: {'description': 'Startup file structure is invalid'}},
    ),
)
async def get_startup_generator_parameters_list(
    settings: SettingsDep,
) -> tuple[StartupGeneratorParametersList, StartupGeneratorParametersListRaw]:
    """Get startup generator parameters (for scenarios router).

    Kept as a transitional helper for the scenarios router until that
    router is migrated to its own entry point. New code should use
    `StartupDep` from `eventum.api.dependencies.app`.

    Parameters
    ----------
    settings : SettingsDep
        Application settings dependency.

    Returns
    -------
    tuple[StartupGeneratorParametersList, StartupGeneratorParametersListRaw]
        Generators parameters from the startup file as model and as
        raw object.

    Raises
    ------
    HTTPException
        If startup file cannot be read due to OS error.

    HTTPException
        If startup file structure is invalid.

    """
    try:
        async with aiofiles.open(settings.path.startup) as f:
            content = await f.read()
    except OSError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Cannot read startup file due to OS error: {e}',
        ) from None

    parsed_object = await asyncio.to_thread(
        lambda: yaml.load(content, Loader=yaml.SafeLoader),
    )

    if not isinstance(parsed_object, list):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Startup file structure is invalid: object is not a list',
        ) from None

    try:
        params_list = await asyncio.to_thread(
            lambda: (
                StartupGeneratorParametersList.build_over_generation_parameters(
                    object=parsed_object,
                    generation_parameters=settings.generation,
                )
            ),
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                'Startup file structure is invalid: '
                f'{prettify_validation_errors(e.errors())}'
            ),
        ) from None
    return params_list, parsed_object


StartupGeneratorsParametersListDep = Annotated[
    tuple[StartupGeneratorParametersList, StartupGeneratorParametersListRaw],
    Depends(get_startup_generator_parameters_list),
]


@set_responses(
    {
        400: {
            'description': (
                'ID field in the body does not match ID path parameter'
            ),
        },
    },
)
async def check_id_in_body_match_path(
    id: Annotated[str, Path(description='ID of the generator', min_length=1)],
    params: Annotated[
        StartupGeneratorParameters,
        Body(description='Generator parameters'),
    ],
) -> str:
    """Check if ID parameter in body matches ID path parameter.

    Parameters
    ----------
    id : Annotated[str, Path]
        ID path parameter.

    params : Annotated[StartupGeneratorParameters, Body]
        Request body.

    Returns
    -------
    str
        Original id path parameter

    Raises
    ------
    HTTPException
        If ID field in the body does not match ID path parameter.

    """
    if id != params.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='ID field in the body does not match ID path parameter',
        )

    return id


CheckIdInBodyMatchPathDep = Depends(check_id_in_body_match_path)
