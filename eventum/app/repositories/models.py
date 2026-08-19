"""Models of connected generator repositories."""

from datetime import datetime
from urllib.parse import urlsplit

from pydantic import BaseModel, Field, RootModel, field_validator

# A repository is fetched by the server on request, so the transports
# it may name are limited to the two that carry nothing but a fetch.
# Everything else - `ssh`, `file`, `git` - either reaches into the
# host the server runs on or opens a channel with no credentials of
# its own.
ALLOWED_URL_SCHEMES = frozenset({'http', 'https'})

_NAME_PATTERN = r'^[a-zA-Z0-9](?:[a-zA-Z0-9._-]*[a-zA-Z0-9])?$'
_REF_PATTERN = r'^[a-zA-Z0-9][a-zA-Z0-9._/-]*$'


class Repository(BaseModel, extra='forbid', frozen=True):
    """Connected generator repository.

    Attributes
    ----------
    name : str
        Name the repository is referred to by, unique across the
        connected ones.

    url : str
        URL the repository is fetched from.

    ref : str | None, default=None
        Branch or tag to fetch. The default branch of the repository
        is fetched when not provided.

    username : str | None, default=None
        User name to authenticate with.

    secret : str | None, default=None
        Name of the keyring secret holding the password or access
        token to authenticate with.

    """

    name: str = Field(min_length=1, max_length=64, pattern=_NAME_PATTERN)
    url: str = Field(min_length=1, max_length=2048)
    ref: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        pattern=_REF_PATTERN,
    )
    username: str | None = Field(default=None, min_length=1, max_length=255)
    secret: str | None = Field(default=None, min_length=1, max_length=255)

    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:  # noqa: D102
        parts = urlsplit(v)

        if parts.scheme not in ALLOWED_URL_SCHEMES:
            schemes = ', '.join(sorted(ALLOWED_URL_SCHEMES))
            msg = f'URL scheme must be one of: {schemes}'
            raise ValueError(msg)

        if not parts.hostname:
            msg = 'URL must include a host'
            raise ValueError(msg)

        if parts.username is not None or parts.password is not None:
            msg = (
                'URL must not carry credentials, provide them as '
                '"username" and "secret"'
            )
            raise ValueError(msg)

        return v

    @field_validator('ref')
    @classmethod
    def validate_ref(cls, v: str | None) -> str | None:  # noqa: D102
        if v is not None and ('..' in v or v.endswith(('/', '.lock'))):
            msg = 'Reference is not a valid branch or tag name'
            raise ValueError(msg)

        return v


class RepositoryList(RootModel, frozen=True):
    """List of connected repositories."""

    root: tuple[Repository, ...] = Field()


class CatalogEntry(BaseModel, extra='forbid', frozen=True):
    """Generator published by a connected repository.

    Attributes
    ----------
    name : str
        Name of the generator directory in the repository.

    title : str | None
        Title of the generator, taken from the heading of its readme.

    summary : str | None
        Summary of the generator, taken from the first paragraph of
        its readme.

    file_count : int
        Number of files the generator consists of.

    size : int
        Total size of the generator files in bytes.

    """

    name: str
    title: str | None
    summary: str | None
    file_count: int
    size: int


class Catalog(BaseModel, extra='forbid', frozen=True):
    """Generators published by a connected repository.

    Attributes
    ----------
    revision : str
        Commit hash the catalog was read from.

    refreshed_at : datetime
        Moment the catalog was read at.

    entries : list[CatalogEntry]
        Published generators, ordered by name.

    """

    revision: str
    refreshed_at: datetime
    entries: list[CatalogEntry]
