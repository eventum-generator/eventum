"""Models."""

from pydantic import BaseModel, Field


class ScenarioResponse(BaseModel, frozen=True):
    """A scenario with its generator IDs."""

    name: str = Field(min_length=1, description='Scenario name')
    generator_ids: list[str] = Field(
        description='IDs of generators in this scenario',
    )
