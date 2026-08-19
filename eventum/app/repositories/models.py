"""Models of connected generator repositories."""

from datetime import datetime
from typing import Literal
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


class RepositoryStatus(BaseModel, extra='forbid', frozen=True):
    """Result of the last check of a repository.

    Attributes
    ----------
    state : Literal['unknown', 'available', 'unavailable']
        Whether the repository answered the last check. A repository
        that has not been checked in this process is unknown.

    checked_at : datetime | None, default=None
        Moment of the last check.

    reason : str | None, default=None
        Why the repository did not answer.

    """

    state: Literal['unknown', 'available', 'unavailable']
    checked_at: datetime | None = None
    reason: str | None = None


class ConnectedRepository(Repository):
    """Connected repository with the result of its last check.

    Attributes
    ----------
    status : RepositoryStatus
        Result of the last check of the repository.

    """

    status: RepositoryStatus


class GeneratorSource(BaseModel, extra='ignore', frozen=True):
    """Origin an installed project carries with it.

    Written into the project when a published generator is installed
    and read back to tell what a project came from. Unknown fields are
    kept out rather than rejected, so a project written by a later
    version still reads here.

    Attributes
    ----------
    repository : str
        Name the repository was connected under.

    url : str
        URL the repository was fetched from.

    ref : str | None, default=None
        Branch or tag the generator was installed from.

    entry : str
        Name of the published generator.

    revision : str
        Commit the catalog was read from.

    tree : str
        Content hash of the generator directory at that commit.

    installed_at : datetime
        Moment of the installation.

    """

    repository: str
    url: str
    ref: str | None = None
    entry: str
    revision: str
    tree: str
    installed_at: datetime


class InstalledProject(BaseModel, extra='forbid', frozen=True):
    """Project a published generator is installed as.

    Attributes
    ----------
    project : str
        Name of the project directory.

    revision : str
        Commit the project was installed from.

    installed_at : datetime
        Moment of the installation.

    outdated : bool
        Whether the repository publishes the generator with content
        different from what was installed. It says nothing about
        changes made to the project since.

    """

    project: str
    revision: str
    installed_at: datetime
    outdated: bool


class CatalogEntry(BaseModel, extra='forbid', frozen=True):
    """Generator published by a connected repository.

    Attributes
    ----------
    name : str
        Name of the generator directory in the repository.

    path : str
        Path of the generator directory inside the repository.

    title : str | None
        Title of the generator, taken from the heading of its readme.

    summary : str | None
        Summary of the generator, taken from the first paragraph of
        its readme.

    file_count : int
        Number of files the generator consists of.

    size : int
        Total size of the generator files in bytes.

    tree : str
        Content hash of the generator directory, which changes exactly
        when what the generator consists of changes.

    installed_as : tuple[InstalledProject, ...], default=()
        Projects of the workspace this generator is installed as.

    """

    name: str = Field(max_length=255)
    path: str = Field(max_length=4096)
    title: str | None = Field(max_length=250)
    summary: str | None = Field(max_length=500)
    file_count: int
    size: int
    tree: str
    installed_as: tuple[InstalledProject, ...] = ()


class Catalog(BaseModel, extra='forbid', frozen=True):
    """Generators published by a connected repository.

    Attributes
    ----------
    revision : str
        Commit hash the catalog was read from.

    refreshed_at : datetime
        Moment the catalog was read at.

    committed_at : datetime
        Moment the commit the catalog was read from was authored at.

    author : str | None
        Author of that commit.

    entries : list[CatalogEntry]
        Published generators, ordered by name.

    """

    revision: str
    refreshed_at: datetime
    committed_at: datetime
    author: str | None
    entries: list[CatalogEntry]


class DiscoveryRate(BaseModel, extra='forbid', frozen=True):
    """Quota left for searching the published repositories.

    Attributes
    ----------
    remaining : int | None, default=None
        Number of searches left before the quota is spent.

    reset_at : datetime | None, default=None
        Moment the quota is restored at.

    """

    remaining: int | None = None
    reset_at: datetime | None = None


class DiscoveredRepository(BaseModel, extra='forbid', frozen=True):
    """Repository publishing generators in the open.

    Everything but `connected` is what the repository states about
    itself, republished as it was read - nothing here is reviewed.

    Attributes
    ----------
    name : str
        Name of the repository.

    full_name : str
        Name of the repository with the owner it belongs to.

    url : str
        URL the repository is fetched from.

    page_url : str
        URL of the page the repository is presented on.

    owner : str
        Owner the repository belongs to.

    description : str | None, default=None
        What the repository says it holds.

    topics : tuple[str, ...], default=()
        Topics the repository carries.

    stars : int, default=0
        Number of stars the repository has.

    updated_at : datetime | None, default=None
        Moment the repository was last pushed to.

    license : str | None, default=None
        License the repository is published under.

    archived : bool, default=False
        Whether the repository is archived by its owner.

    official : bool, default=False
        Whether the repository is published by Eventum itself.

    connected : bool, default=False
        Whether this instance is already connected to the repository.

    """

    name: str = Field(max_length=255)
    full_name: str = Field(max_length=512)
    url: str = Field(max_length=2048)
    page_url: str = Field(max_length=2048)
    owner: str = Field(max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    topics: tuple[str, ...] = Field(default=(), max_length=32)
    stars: int = 0
    updated_at: datetime | None = None
    license: str | None = Field(default=None, max_length=64)
    archived: bool = False
    official: bool = False
    connected: bool = False


class Discovery(BaseModel, extra='forbid', frozen=True):
    """Repositories published in the open, as read at a moment.

    Attributes
    ----------
    topic : str
        Topic a repository carries to appear in the list.

    query : str
        Words the list was narrowed with, empty when it was not.

    entries : tuple[DiscoveredRepository, ...]
        Repositories that were found, the ones published by Eventum
        first and the rest by the stars they carry.

    total_count : int
        Number of repositories matching in total, of which this is one
        page.

    refreshed_at : datetime
        Moment the list was read at.

    rate : DiscoveryRate
        Quota left for searching again.

    """

    topic: str
    query: str
    entries: tuple[DiscoveredRepository, ...]
    total_count: int
    refreshed_at: datetime
    rate: DiscoveryRate


def identify_repository(url: str) -> str:
    """Return the identity of the repository an URL points at.

    Two URLs naming the same repository - differing only in scheme, in
    a trailing slash, in the ".git" suffix or in the case of the host -
    share one identity, so that connecting the same repository twice
    is recognized while connecting two of its branches is not.

    Parameters
    ----------
    url : str
        URL of the repository.

    Returns
    -------
    str
        Identity of the repository.

    """
    parts = urlsplit(url)

    # A host names the same machine whatever its case; a path does
    # not name the same repository on a host that tells "Team" and
    # "team" apart, which is every host but a few.
    host = (parts.hostname or '').lower()
    port = f':{parts.port}' if parts.port is not None else ''
    path = parts.path.rstrip('/').removesuffix('.git').rstrip('/')

    return f'{host}{port}{path}'
