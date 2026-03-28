"""Models."""

from pydantic import BaseModel, Field


class GlobalsReferenceResponse(BaseModel, frozen=True):
    """A single reference to globals in a template."""

    key: str
    template: str


class GlobalsWarningResponse(BaseModel, frozen=True):
    """A warning about globals usage that cannot be fully detected."""

    type: str
    template: str


class GlobalsUsageResponse(BaseModel, frozen=True):
    """Detected globals usage across all templates in a generator."""

    writes: list[GlobalsReferenceResponse]
    reads: list[GlobalsReferenceResponse]
    warnings: list[GlobalsWarningResponse]


class ScenarioResponse(BaseModel, frozen=True):
    """A scenario with its generator IDs."""

    name: str = Field(min_length=1, description='Scenario name')
    generator_ids: list[str] = Field(
        description='IDs of generators in this scenario',
    )
