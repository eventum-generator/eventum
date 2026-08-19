"""Models."""

from pathlib import Path

from pydantic import BaseModel, Field, field_validator


class InstallGeneratorRequest(BaseModel, extra='forbid', frozen=True):
    """Request of installing a published generator.

    Attributes
    ----------
    name : str
        Name of the generator directory to install into.

    """

    name: str = Field(
        description='Name of the generator directory to install into',
        min_length=1,
        max_length=255,
    )

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:  # noqa: D102
        if v != Path(v).name or v in {'.', '..'}:
            msg = 'Name must be a single directory name'
            raise ValueError(msg)

        return v
