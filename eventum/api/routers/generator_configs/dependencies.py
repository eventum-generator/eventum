"""Dependencies."""

import asyncio
import pathlib
from typing import Annotated

from fastapi import Depends, HTTPException, Path, status

from eventum.api.dependencies.app import SettingsDep
from eventum.api.utils.response_description import set_responses
from eventum.app.workspace import (
    WorkspaceError,
    ensure_relative,
    resolve_generator_dir,
)


async def list_generator_dirs(settings: SettingsDep) -> list[str]:
    """List all generator directory names inside `path.generators_dir` '
    with generator configs.

    Parameters
    ----------
    settings : SettingsDep
        Application settings dependency.

    Returns
    -------
    list[str]
        List of directory names.

    """
    if not settings.path.generators_dir.exists():
        return []

    return await asyncio.to_thread(
        lambda: [
            path.parent.name
            for path in settings.path.generators_dir.glob(
                f'*/{settings.path.generator_config_filename}',
            )
        ],
    )


GeneratorDirsDep = Annotated[list[str], Depends(list_generator_dirs)]


@set_responses(
    responses={
        403: {
            'description': (
                'Accessing directories outside `path.generators_dir` '
                'is not allowed'
            ),
        },
    },
)
async def check_directory_is_allowed(
    name: Annotated[str, Path(description='Name of the generator directory')],
    settings: SettingsDep,
) -> str:
    """Check that a generator directory is located within the
    allowed generators directory.

    Parameters
    ----------
    name : str
        Name of the generator directory to check.

    settings : SettingsDep
        Application settings dependency.

    Returns
    -------
    str
        Original directory name.

    Raises
    ------
    HTTPException
        If the resolved path is outside `settings.path.generators_dir`.

    """
    try:
        resolve_generator_dir(settings.path.generators_dir, name)
    except WorkspaceError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                'Accessing directories outside `path.generators_dir` '
                'is not allowed'
            ),
        ) from None

    return name


CheckDirectoryIsAllowedDep = Depends(check_directory_is_allowed)


@set_responses(
    responses={
        404: {
            'description': 'Generator configuration does not exist',
        },
    },
)
async def check_configuration_exists(
    name: Annotated[str, Path(description='Name of the generator directory')],
    settings: SettingsDep,
) -> str:
    """Check that generator configuration exist.

    Parameters
    ----------
    name : str
        Name of the generator directory to check.

    settings : SettingsDep
        Application settings dependency.

    Returns
    -------
    str
        Original directory name.

    Raises
    ------
    HTTPException
        Generator configuration do not exist.

    """
    path = (
        settings.path.generators_dir
        / name
        / settings.path.generator_config_filename
    ).resolve()

    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Generator configuration does not exist',
        )

    return name


CheckConfigurationExistsDep = Depends(check_configuration_exists)


@set_responses(
    responses={
        409: {
            'description': 'Configuration already exists',
        },
    },
)
async def check_configuration_not_exists(
    name: Annotated[str, Path(description='Name of the generator directory')],
    settings: SettingsDep,
) -> str:
    """Check that generator configuration does not exist.

    Parameters
    ----------
    name : str
        Name of the generator directory to check.

    settings : SettingsDep
        Application settings dependency.

    Returns
    -------
    str
        Original directory name.

    Raises
    ------
    HTTPException
        Configuration already exists.

    """
    path = (
        settings.path.generators_dir
        / name
        / settings.path.generator_config_filename
    ).resolve()

    if path.exists():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Configuration already exists',
        )

    return name


CheckConfigurationNotExistsDep = Depends(check_configuration_not_exists)


@set_responses(
    responses={
        400: {
            'description': (
                "Parent directories traversal (i.e. using '..') "
                'is not allowed and path cannot be absolute'
            ),
        },
    },
)
async def check_filepath_is_directly_relative(
    filepath: Annotated[
        pathlib.Path,
        Path(description='Relative path to the file'),
    ],
) -> pathlib.Path:
    """Check that filepath directly relative (i.e. not using '..').

    Parameters
    ----------
    filepath : Path
        Path to check.

    Returns
    -------
    Path
        Original path.

    Raises
    ------
    HTTPException
        - Parent directories traversal (i.e. using '..') is not allowed
        - Path cannot be absolute

    """
    try:
        ensure_relative(filepath)
    except WorkspaceError:
        detail = (
            'Path cannot be absolute'
            if filepath.is_absolute()
            else (
                "Parent directories traversal (i.e. using '..') "
                'is not allowed.'
            )
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        ) from None

    return filepath


CheckFilepathIsDirectlyRelativeDep = Depends(
    check_filepath_is_directly_relative,
)
