"""Models."""

from pydantic import BaseModel, Field


class GeneratorDirExtendedInfo(BaseModel, frozen=True, extra='forbid'):
    """Response model that contains extended info about generator directory."""

    name: str = Field(min_length=1, description='Directory name')
    size_in_bytes: int | None = Field(
        ge=0,
        description='Size of directory content in bytes',
    )
    last_modified: float | None = Field(
        ge=0,
        description=(
            'Last directory content modification time as unix timestamp'
        ),
    )
    generator_ids: list[str] = Field(
        description=(
            'IDs of generators that use configuration from this directory'
        ),
    )
