"""Routes."""

import asyncio
from typing import Annotated

from fastapi import APIRouter, Body, HTTPException, Path

from eventum.api.dependencies.app import SettingsDep
from eventum.api.routers.secrets.models import RenameSecretRequest
from eventum.app.workspace import find_secret_references
from eventum.security.manage import (
    SecretConflictError,
    SecretNotFoundError,
    get_secret,
    list_secrets,
    remove_secret,
    rename_secret,
    set_secret,
)

router = APIRouter()


@router.get(
    '/{name}',
    description='Get secret with specified name from keyring',
    response_description='Secret value',
    responses={
        404: {'description': 'Secret is missing in keyring'},
        500: {'description': 'Failed to obtain secret'},
    },
)
async def get_secret_value(
    name: Annotated[str, Path(description='Secret name', min_length=1)],
) -> str:
    try:
        return await asyncio.to_thread(lambda: get_secret(name=name))
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e),
        ) from None
    except OSError as e:
        raise HTTPException(
            status_code=500,
            detail=f'Failed to obtain secret: {e}',
        ) from None


@router.get(
    '/',
    description='List all secrets names',
    response_description='List with names of secrets',
    responses={
        500: {'description': 'Failed to list secret names'},
    },
)
async def list_secret_names() -> list[str]:
    try:
        return await asyncio.to_thread(lambda: list_secrets())
    except OSError as e:
        raise HTTPException(
            status_code=500,
            detail=f'Failed to list secret names: {e}',
        ) from None


@router.put(
    '/{name}',
    description='Put secret with specified name to keyring',
    responses={500: {'description': 'Failed to set secret'}},
)
async def set_secret_value(
    name: Annotated[str, Path(description='Secret name', min_length=1)],
    value: Annotated[str, Body(description='Secret value', min_length=1)],
) -> None:
    try:
        await asyncio.to_thread(lambda: set_secret(name=name, value=value))
    except OSError as e:
        raise HTTPException(
            status_code=500,
            detail=f'Failed to set secret: {e}',
        ) from None


@router.delete(
    '/{name}',
    description='Delete secret with specified name to keyring',
    responses={500: {'description': 'Failed to remove secret'}},
)
async def delete_secret_value(
    name: Annotated[str, Path(description='Secret name', min_length=1)],
) -> None:
    try:
        await asyncio.to_thread(lambda: remove_secret(name=name))
    except OSError as e:
        raise HTTPException(
            status_code=500,
            detail=f'Failed to remove secret: {e}',
        ) from None


@router.get(
    '/{name}/references',
    description=(
        'List projects whose configuration references the secret as '
        '`${secrets.<name>}`'
    ),
    response_description='Names of referencing generator directories',
)
async def list_secret_references(
    name: Annotated[str, Path(description='Secret name', min_length=1)],
    settings: SettingsDep,
) -> list[str]:
    return await asyncio.to_thread(
        find_secret_references,
        settings.path.generators_dir,
        settings.path.generator_config_filename,
        name,
    )


@router.post(
    '/{name}/rename',
    description=(
        'Rename secret in keyring. References to the secret in generator '
        'configurations are not rewritten.'
    ),
    responses={
        404: {'description': 'Secret is missing in keyring'},
        409: {'description': 'Secret with the new name already exists'},
        500: {'description': 'Failed to rename secret'},
    },
)
async def rename_secret_value(
    name: Annotated[str, Path(description='Secret name', min_length=1)],
    request: Annotated[
        RenameSecretRequest,
        Body(description='New secret name'),
    ],
) -> None:
    try:
        await asyncio.to_thread(rename_secret, name, request.new_name)
    except SecretNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None
    except SecretConflictError as e:
        raise HTTPException(status_code=409, detail=str(e)) from None
    except OSError as e:
        raise HTTPException(
            status_code=500,
            detail=f'Failed to rename secret: {e}',
        ) from None
