"""Dependencies."""

from typing import Annotated

from fastapi import Body, HTTPException, Path, status
from fastapi.params import Depends

from eventum.api.dependencies.app import GeneratorManagerDep, SettingsDep
from eventum.api.utils.response_description import set_responses
from eventum.app.manager import ManagingError
from eventum.core.generator import Generator
from eventum.core.parameters import GeneratorParameters


@set_responses(
    responses={
        404: {
            'description': 'Generator with provided id is not found',
        },
    },
)
async def get_generator(
    id: Annotated[str, Path(description='Generator id', min_length=1)],
    generator_manager: GeneratorManagerDep,
) -> Generator:
    """Get generator with provided id from manager.

    Parameters
    ----------
    id : str
        ID of the generator to get.

    generator_manager : GeneratorManagerDep
        Generator manager dependency.

    Returns
    -------
    Generator
        Generator gotten from manager.

    Raises
    ------
    HTTPException
        If generator with provided id is not found in manager.

    """
    try:
        return generator_manager.get_generator(id)
    except ManagingError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from None


GeneratorDep = Annotated[Generator, Depends(get_generator)]


async def get_prepared_generator_params_from_request(
    id: Annotated[str, Path(description='Generator id', min_length=1)],
    params: Annotated[
        GeneratorParameters,
        Body(description='Generator parameters'),
    ],
    settings: SettingsDep,
) -> GeneratorParameters:
    """Get generator parameters from request body with prepared
    parameters.

    Particularly id is substituted from query parameters, and path to
    configuration is resolved to absolute, which is preferred before
    adding it to a generator manager.

    This dependency should be used when a new generator is added to
    manager in methods like PUT and POST.

    Parameters
    ----------
    id : str
        ID of the generator to use this parameters for.

    params : GeneratorParameters
        Generator parameters.

    settings : SettingsDep
        Settings dependency.

    Returns
    -------
    GeneratorParameters
        Prepared generator parameters.

    """
    kwargs = params.model_dump(exclude_defaults=True)
    kwargs.update(id=id)

    return GeneratorParameters(**kwargs).as_absolute(
        base_dir=settings.path.generators_dir,
    )


PreparedGeneratorParamsDep = Annotated[
    GeneratorParameters,
    Depends(get_prepared_generator_params_from_request),
]


@set_responses(
    responses={
        404: {
            'description': 'No configuration exists in specified path',
        },
    },
)
async def check_path_exists(
    params: PreparedGeneratorParamsDep,
) -> GeneratorParameters:
    """Check if the path in generator parameters exists.

    Parameters
    ----------
    params : PreparedGeneratorParamsDep
        Prepared generator parameters dependency.

    Returns
    -------
    GeneratorParameters
        Original prepared generator parameters.

    Raises
    ------
    HTTPException
        If no configuration exists in specified path.

    """
    if not params.path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'No configuration exists in specified path: {params.path}',
        ) from None

    return params


CheckPathExistsDep = Depends(check_path_exists)
