"""Dependencies."""

from typing import Annotated

from fastapi import Depends, HTTPException, Path, status

from eventum.api.routers.startup.dependencies import (
    StartupGeneratorsParametersListDep,
)
from eventum.api.utils.response_description import set_responses


@set_responses({404: {'description': 'Scenario not found'}})
async def check_scenario_exists(
    name: Annotated[
        str, Path(description='Scenario name', min_length=1)
    ],
    generators_parameters: StartupGeneratorsParametersListDep,
) -> str:
    """Validate that at least one generator has this scenario tag.

    Returns
    -------
    str
        The validated scenario name.

    """
    generators_parameters_model, _ = generators_parameters
    for params in generators_parameters_model.root:
        if name in (params.scenarios or []):
            return name

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f'Scenario not found: {name}',
    )


CheckScenarioExistsDep = Annotated[
    str,
    Depends(check_scenario_exists),
]
