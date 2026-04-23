"""Routes."""

import asyncio
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Body, HTTPException, status
from fastapi import Path as PathParam

from eventum.api.dependencies.app import SettingsDep, StartupDep
from eventum.api.routers.startup.dependencies import (
    CheckIdInBodyMatchPathDep,
)
from eventum.api.utils.response_description import merge_responses
from eventum.app.models.startup import (
    StartupGeneratorParameters,
    StartupGeneratorParametersList,
)
from eventum.app.startup import (
    StartupConflictError,
    StartupFileError,
    StartupFormatError,
    StartupNotFoundError,
)

router = APIRouter()


_READ_RESPONSES: dict[int | str, dict[str, Any]] = {
    500: {'description': 'Cannot read startup file due to OS error'},
    422: {'description': 'Startup file content is malformed or invalid'},
}

_WRITE_RESPONSES: dict[int | str, dict[str, Any]] = {
    500: {'description': 'Cannot write startup file due to OS error'},
}

_NOT_FOUND_RESPONSES: dict[int | str, dict[str, Any]] = {
    404: {'description': 'Generator with this ID is not defined'},
}


def _relative_where_possible(
    params_list: StartupGeneratorParametersList,
    base_dir: Path,
) -> StartupGeneratorParametersList:
    """Convert entries to relative paths where possible."""
    normalized: list[StartupGeneratorParameters] = []
    for params in params_list.root:
        try:
            normalized.append(params.as_relative(base_dir=base_dir))
        except ValueError:
            normalized.append(params)
    return StartupGeneratorParametersList(root=tuple(normalized))


@router.get(
    '/',
    description='Get list of generator definitions in the startup file',
    response_description=(
        'List of parameters of generators in the startup file. '
        'Note that response also includes default parameters '
        'even if they are not set in the file.'
    ),
    responses=_READ_RESPONSES,
)
async def get_generators_in_startup(
    startup: StartupDep,
    settings: SettingsDep,
) -> StartupGeneratorParametersList:
    try:
        params_list = await asyncio.to_thread(startup.get_all)
    except StartupFileError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from None
    except StartupFormatError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        ) from None

    return _relative_where_possible(
        params_list,
        base_dir=settings.path.generators_dir,
    )


@router.get(
    '/{id}',
    description='Get generator definition from list in the startup file',
    response_description=(
        'Parameters of generator from the startup file. '
        'Note that response also includes default parameters '
        'even if they are not set in the file.'
    ),
    responses=merge_responses(_READ_RESPONSES, _NOT_FOUND_RESPONSES),
)
async def get_generator_from_startup(
    id: Annotated[str, PathParam(description='Generator id', min_length=1)],
    startup: StartupDep,
    settings: SettingsDep,
) -> StartupGeneratorParameters:
    try:
        params = await asyncio.to_thread(startup.get, id)
    except StartupNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from None
    except StartupFileError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from None
    except StartupFormatError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        ) from None

    try:
        return params.as_relative(base_dir=settings.path.generators_dir)
    except ValueError:
        return params


@router.post(
    '/{id}',
    description='Add generator definition to list in the startup file',
    responses=merge_responses(
        _READ_RESPONSES,
        _WRITE_RESPONSES,
        {409: {'description': 'Generator with this ID is already defined'}},
    ),
    status_code=status.HTTP_201_CREATED,
)
async def add_generator_to_startup(
    id: Annotated[str, CheckIdInBodyMatchPathDep],  # noqa: ARG001
    params: Annotated[
        StartupGeneratorParameters,
        Body(description='Generator parameters'),
    ],
    startup: StartupDep,
) -> None:
    try:
        await asyncio.to_thread(startup.add, params)
    except StartupConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        ) from None
    except StartupFileError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from None
    except StartupFormatError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        ) from None


@router.put(
    '/{id}',
    description='Update generator definition in list in the startup file',
    responses=merge_responses(
        _READ_RESPONSES,
        _WRITE_RESPONSES,
        _NOT_FOUND_RESPONSES,
    ),
)
async def update_generator_in_startup(
    id: Annotated[str, CheckIdInBodyMatchPathDep],  # noqa: ARG001
    params: Annotated[
        StartupGeneratorParameters,
        Body(description='Startup generator parameters'),
    ],
    startup: StartupDep,
) -> None:
    try:
        await asyncio.to_thread(startup.update, params)
    except StartupNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from None
    except StartupFileError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from None
    except StartupFormatError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        ) from None


@router.delete(
    '/{id}',
    description='Delete generator definition from list in the startup file',
    responses=merge_responses(
        _READ_RESPONSES,
        _WRITE_RESPONSES,
        _NOT_FOUND_RESPONSES,
    ),
)
async def delete_generator_from_startup(
    id: Annotated[str, PathParam(description='Generator id', min_length=1)],
    startup: StartupDep,
) -> None:
    try:
        await asyncio.to_thread(startup.delete, id)
    except StartupNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from None
    except StartupFileError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from None
    except StartupFormatError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        ) from None


@router.post(
    '/group-actions/bulk-delete',
    description=(
        'Bulk delete several generator definitions from list in the '
        'startup file'
    ),
    response_description='IDs of deleted generator definitions',
    responses=merge_responses(_READ_RESPONSES, _WRITE_RESPONSES),
)
async def bulk_delete_generators_from_startup(
    ids: Annotated[
        list[str],
        Body(description='IDs of the generators', min_length=1),
    ],
    startup: StartupDep,
) -> list[str]:
    try:
        return await asyncio.to_thread(startup.bulk_delete, ids)
    except StartupFileError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from None
    except StartupFormatError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        ) from None
