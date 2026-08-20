"""Routes."""

import asyncio
from typing import Annotated

from fastapi import APIRouter, Body, HTTPException, Path

from eventum.api.dependencies.app import RepositoriesDep, SettingsDep
from eventum.api.routers.secrets.models import (
    RenameSecretRequest,
    SecretReferencesResponse,
)
from eventum.app.renaming import (
    RenameConflictError,
    RenameError,
    RenameNotFoundError,
)
from eventum.app.repositories import RepositoryError
from eventum.app.secrets import find_secret_references, rename_secret
from eventum.exceptions import ContextualError
from eventum.security.manage import (
    get_secret,
    list_secrets,
    remove_secret,
    set_secret,
)

router = APIRouter()


def _detail(error: ContextualError) -> str:
    """Build the detail of a failure, naming the reason behind it.

    The reason names what the file system, the parser or the keyring
    objected to, which is what a caller looking at a failing
    instance acts on.
    """
    reason = error.context.get('reason')

    return str(error) if reason is None else f'{error}: {reason}'


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
        'List what refers to the secret - the projects whose '
        'configuration reads it as `${secrets.<name>}`, and the '
        'connected repositories authenticating with it'
    ),
    response_description='Referrers of the secret, by kind',
    responses={
        500: {'description': 'Connected repositories cannot be read'},
    },
)
async def list_secret_references(
    name: Annotated[str, Path(description='Secret name', min_length=1)],
    settings: SettingsDep,
    repositories: RepositoriesDep,
) -> SecretReferencesResponse:
    try:
        references = await asyncio.to_thread(
            find_secret_references,
            generators_dir=settings.path.generators_dir,
            config_filename=settings.path.generator_config_filename,
            repositories=repositories,
            secret=name,
        )
    except RepositoryError as e:
        raise HTTPException(status_code=500, detail=_detail(e)) from None

    return SecretReferencesResponse(
        projects=references.projects,
        repositories=references.repositories,
    )


@router.post(
    '/{name}/rename',
    description=(
        'Rename secret in keyring. Connected repositories '
        'authenticating with the secret are repointed at the new name; '
        'references in generator configurations are not rewritten.'
    ),
    response_description='Names of the repositories that were repointed',
    responses={
        404: {'description': 'Secret is missing in keyring'},
        409: {
            'description': (
                'The new name is taken - by another secret, or by a '
                'connected repository authenticating with it'
            ),
        },
        500: {
            'description': (
                'Failed to rename secret, or the repositories using it '
                'cannot be repointed. The detail names which of the two '
                'happened, and whether the secret was left renamed'
            ),
        },
    },
)
async def rename_secret_value(
    name: Annotated[str, Path(description='Secret name', min_length=1)],
    request: Annotated[
        RenameSecretRequest,
        Body(description='New secret name'),
    ],
    repositories: RepositoriesDep,
) -> list[str]:
    try:
        return await asyncio.to_thread(
            rename_secret,
            repositories=repositories,
            name=name,
            new_name=request.new_name,
        )
    except RenameNotFoundError as e:
        raise HTTPException(status_code=404, detail=_detail(e)) from None
    except RenameConflictError as e:
        raise HTTPException(status_code=409, detail=_detail(e)) from None
    except RenameError as e:
        raise HTTPException(status_code=500, detail=_detail(e)) from None
