"""Models."""

from datetime import datetime
from pathlib import Path
from typing import Self

from pydantic import BaseModel, Field, field_validator

from eventum.app.repositories import Catalog, CatalogEntry, InstalledProject


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


class InstalledGeneratorResponse(BaseModel, extra='forbid', frozen=True):
    """Project a published generator was installed as.

    Attributes
    ----------
    name : str
        Name of the generator directory that was written.

    file_count : int
        Number of files it holds.

    """

    name: str = Field(
        description='Name of the generator directory that was written',
    )
    file_count: int = Field(description='Number of files it holds')


class CatalogEntryResponse(BaseModel, extra='forbid', frozen=True):
    """Generator published by a connected repository."""

    name: str = Field(
        description='Name of the generator directory in the repository',
    )
    path: str = Field(
        description='Path of the generator directory inside the repository',
    )
    title: str | None = Field(
        description='Title taken from the readme of the generator',
    )
    summary: str | None = Field(
        description='Summary taken from the readme of the generator',
    )
    file_count: int = Field(
        description='Number of files the generator consists of',
    )
    size: int = Field(
        description='Total size of the generator files in bytes',
    )
    installed_as: list[InstalledProject] = Field(
        description='Projects of the workspace this generator is installed as',
    )

    @classmethod
    def of(cls, entry: CatalogEntry) -> Self:
        """Build the response of a published generator."""
        return cls(**entry.model_dump(exclude={'tree'}))


class CatalogResponse(BaseModel, extra='forbid', frozen=True):
    """Generators published by a connected repository."""

    revision: str = Field(
        description='Commit hash the catalog was read from',
    )
    refreshed_at: datetime = Field(
        description='Moment the catalog was read at',
    )
    committed_at: datetime = Field(
        description='Moment that commit was authored at',
    )
    author: str | None = Field(description='Author of that commit')
    entries: list[CatalogEntryResponse] = Field(
        description='Published generators, ordered by name',
    )

    @classmethod
    def of(cls, catalog: Catalog) -> Self:
        """Build the response of a catalog."""
        return cls(
            revision=catalog.revision,
            refreshed_at=catalog.refreshed_at,
            committed_at=catalog.committed_at,
            author=catalog.author,
            entries=[
                CatalogEntryResponse.of(entry) for entry in catalog.entries
            ],
        )
