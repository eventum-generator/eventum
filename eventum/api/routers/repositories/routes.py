"""Routes."""

import asyncio
from typing import Annotated, Any

from fastapi import APIRouter, Body, HTTPException, Path, Query, status

from eventum.api.dependencies.app import RepositoriesDep
from eventum.api.routers.repositories.models import InstallGeneratorRequest
from eventum.api.utils.response_description import merge_responses
from eventum.app.repositories import (
    Catalog,
    CatalogEntryNotFoundError,
    CatalogError,
    ConnectedRepository,
    InstallConflictError,
    InstallContentError,
    InstallError,
    InstallNameError,
    Repository,
    RepositoryConflictError,
    RepositoryError,
    RepositoryFetchError,
    RepositoryNotFoundError,
    RepositoryStatus,
)

router = APIRouter()

NameParam = Annotated[
    str,
    Path(description='Name of the connected repository', min_length=1),
]
EntryParam = Annotated[
    str,
    Path(description='Name of the published generator', min_length=1),
]

_STORAGE_RESPONSES: dict[int | str, dict[str, Any]] = {
    500: {'description': 'Repositories cannot be read or written'},
}
_NOT_CONNECTED_RESPONSES: dict[int | str, dict[str, Any]] = {
    404: {'description': 'Repository is not connected'},
}
_FETCH_RESPONSES: dict[int | str, dict[str, Any]] = {
    502: {
        'description': (
            'Repository cannot be fetched or publishes no catalog'
        ),
    },
}


@router.get(
    '/',
    description=(
        'List connected generator repositories, each with the result '
        'of the last check made in this process.'
    ),
    response_description='Connected repositories',
    responses=_STORAGE_RESPONSES,
)
async def list_repositories(
    repositories: RepositoriesDep,
) -> list[ConnectedRepository]:
    try:
        return await asyncio.to_thread(repositories.get_all_with_status)
    except RepositoryError as e:
        raise _storage_error(e) from None


@router.post(
    '/',
    description=(
        'Connect a generator repository. The repository is checked '
        'before it is connected, and the catalog it publishes is read '
        'on the first request for it.'
    ),
    responses=merge_responses(
        _STORAGE_RESPONSES,
        _FETCH_RESPONSES,
        {
            409: {
                'description': (
                    'Repository with this name, or the same repository '
                    'at the same branch or tag, is already connected'
                ),
            },
        },
    ),
    status_code=status.HTTP_201_CREATED,
)
async def add_repository(
    repository: Annotated[
        Repository,
        Body(description='Repository to connect'),
    ],
    repositories: RepositoriesDep,
    *,
    verify: Annotated[
        bool,
        Query(
            description=(
                'Whether to check that the repository answers before '
                'connecting it'
            ),
        ),
    ] = True,
) -> None:
    try:
        await asyncio.to_thread(repositories.add, repository, verify=verify)
    except RepositoryConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        ) from None
    except RepositoryFetchError as e:
        raise _fetch_error(e) from None
    except RepositoryError as e:
        raise _storage_error(e) from None


@router.post(
    '/{name}/check',
    description=(
        'Check that the repository with specified name answers and '
        'publishes the branch or tag it names.'
    ),
    response_description='Result of the check',
    responses=merge_responses(
        _STORAGE_RESPONSES,
        _NOT_CONNECTED_RESPONSES,
    ),
)
async def check_repository(
    name: NameParam,
    repositories: RepositoriesDep,
) -> RepositoryStatus:
    try:
        return await asyncio.to_thread(repositories.check, name)
    except RepositoryNotFoundError as e:
        raise _not_found_error(e) from None
    except RepositoryError as e:
        raise _storage_error(e) from None


@router.delete(
    '/{name}',
    description=(
        'Disconnect the repository with specified name. Generators '
        'installed from it are left in place.'
    ),
    responses=merge_responses(
        _STORAGE_RESPONSES,
        _NOT_CONNECTED_RESPONSES,
    ),
)
async def remove_repository(
    name: NameParam,
    repositories: RepositoriesDep,
) -> None:
    try:
        await asyncio.to_thread(repositories.remove, name)
    except RepositoryNotFoundError as e:
        raise _not_found_error(e) from None
    except RepositoryError as e:
        raise _storage_error(e) from None


@router.get(
    '/{name}/catalog',
    description=(
        'Get the catalog of generators published by the repository '
        'with specified name. The repository is fetched when it has '
        'not been fetched yet.'
    ),
    response_description='Catalog of the repository',
    responses=merge_responses(
        _STORAGE_RESPONSES,
        _NOT_CONNECTED_RESPONSES,
        _FETCH_RESPONSES,
    ),
)
async def get_catalog(
    name: NameParam,
    repositories: RepositoriesDep,
) -> Catalog:
    try:
        return await asyncio.to_thread(repositories.get_catalog, name)
    except RepositoryNotFoundError as e:
        raise _not_found_error(e) from None
    except (RepositoryFetchError, CatalogError) as e:
        raise _fetch_error(e) from None
    except RepositoryError as e:
        raise _storage_error(e) from None


@router.post(
    '/{name}/refresh',
    description=(
        'Fetch the repository with specified name and read its catalog anew.'
    ),
    response_description='Catalog of the repository',
    responses=merge_responses(
        _STORAGE_RESPONSES,
        _NOT_CONNECTED_RESPONSES,
        _FETCH_RESPONSES,
    ),
)
async def refresh_catalog(
    name: NameParam,
    repositories: RepositoriesDep,
) -> Catalog:
    try:
        return await asyncio.to_thread(repositories.refresh, name)
    except RepositoryNotFoundError as e:
        raise _not_found_error(e) from None
    except (RepositoryFetchError, CatalogError) as e:
        raise _fetch_error(e) from None
    except RepositoryError as e:
        raise _storage_error(e) from None


@router.post(
    '/{name}/catalog/{entry}/install',
    description=(
        'Install the published generator with specified name as a '
        'generator directory of the workspace.'
    ),
    responses=merge_responses(
        _STORAGE_RESPONSES,
        _FETCH_RESPONSES,
        {
            400: {'description': 'Requested directory name is not allowed'},
            404: {
                'description': (
                    'Repository is not connected or publishes no such '
                    'generator'
                ),
            },
            409: {'description': 'Directory already exists'},
            422: {
                'description': (
                    'Published generator holds no generator '
                    'configuration or exceeds the size limits'
                ),
            },
        },
    ),
    status_code=status.HTTP_201_CREATED,
)
async def install_generator(
    name: NameParam,
    entry: EntryParam,
    request: Annotated[
        InstallGeneratorRequest,
        Body(description='Generator directory to install into'),
    ],
    repositories: RepositoriesDep,
) -> None:
    try:
        await asyncio.to_thread(
            repositories.install,
            name,
            entry,
            request.name,
        )
    except (RepositoryNotFoundError, CatalogEntryNotFoundError) as e:
        raise _not_found_error(e) from None
    except InstallNameError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from None
    except InstallConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        ) from None
    except InstallContentError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f'Generator cannot be installed: {e}',
        ) from None
    except (RepositoryFetchError, CatalogError) as e:
        raise _fetch_error(e) from None
    except InstallError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Generator cannot be installed: {e}',
        ) from None
    except RepositoryError as e:
        raise _storage_error(e) from None


def _not_found_error(error: RepositoryError) -> HTTPException:
    """Build the response of a missing repository or catalog entry."""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=str(error),
    )


def _fetch_error(error: RepositoryError) -> HTTPException:
    """Build the response of a repository that cannot be fetched.

    The reason the remote gave and the hint that reads it are what the
    user acts on, so they are carried over; nothing else of the
    context is, since a fetch runs with credentials.
    """
    parts = [
        str(error),
        error.context.get('reason'),
        error.context.get('hint'),
    ]

    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail='. '.join(str(part) for part in parts if part),
    )


def _storage_error(error: RepositoryError) -> HTTPException:
    """Build the response of an unreadable or unwritable list."""
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=str(error),
    )
