"""Models."""

from pathlib import Path

from pydantic import BaseModel, Field, field_validator


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


class RenameGeneratorDirRequest(BaseModel, frozen=True, extra='forbid'):
    """New name for an existing generator directory."""

    new_name: str = Field(
        min_length=1,
        description=(
            'New directory name. Must be a single directory name, since '
            'only directories directly inside `path.generators_dir` are '
            'recognized as generator directories.'
        ),
    )

    @field_validator('new_name')
    @classmethod
    def validate_single_dir_name(cls, v: str) -> str:  # noqa: D102
        if v != Path(v).name:
            msg = 'Name must be a single directory name'
            raise ValueError(msg)

        return v
