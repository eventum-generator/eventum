"""Operations over connected generator repositories."""

import shutil
import tempfile
import threading
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import structlog
from pydantic import ValidationError
from pydantic_core import ErrorDetails

from eventum.app.repositories.catalog import read_catalog
from eventum.app.repositories.discovery import (
    DISCOVERY_TOPIC,
    normalize_query,
    search_repositories,
)
from eventum.app.repositories.exceptions import (
    CatalogEntryNotFoundError,
    RepositoryConflictError,
    RepositoryError,
    RepositoryFetchError,
    RepositoryNotFoundError,
    RepositorySecretError,
)
from eventum.app.repositories.fetching import (
    DEFAULT_FETCH_TIMEOUT,
    fetch_repository,
    probe_repository,
)
from eventum.app.repositories.installing import install_entry
from eventum.app.repositories.models import (
    REDACTED_PASSWORD,
    Catalog,
    CatalogEntry,
    ConnectedRepository,
    DiscoveredRepository,
    Discovery,
    DiscoveryRate,
    InstalledProject,
    Repository,
    RepositoryList,
    RepositoryStatus,
    identify_repository,
    secret_reference,
)
from eventum.app.repositories.source import (
    build_source,
    collect_installed,
)
from eventum.app.repositories.storage import RepositoriesFile
from eventum.core.config_loader import resolve_secrets
from eventum.utils.validation_prettier import prettify_validation_errors

logger = structlog.stdlib.get_logger()

_CACHE_PREFIX = 'eventum-repositories-'
_REPO_DIRNAME = 'repo'

# How long a read list of published repositories stands before it is
# read again. Long enough that browsing the list never spends the
# small quota an anonymous search has, short enough that a repository
# published today is found today.
DEFAULT_DISCOVERY_TTL = 600.0

# How many searches are held at once. Every word typed into the search
# box is a search of its own, so what is held is capped and the oldest
# of it gives way rather than growing for as long as the instance runs.
DISCOVERY_CACHE_LIMIT = 32

_UNKNOWN = RepositoryStatus(state='unknown')


def _ordered(
    entries: tuple[DiscoveredRepository, ...],
) -> tuple[DiscoveredRepository, ...]:
    """Order published repositories, the official ones first.

    GitHub already returns them by stars, and the repositories Eventum
    publishes itself are lifted above the rest, so the list opens on
    what a first-time reader is looking for.
    """
    return tuple(sorted(entries, key=lambda entry: not entry.official))


def _without_passwords(
    errors: Iterable[ErrorDetails],
) -> list[ErrorDetails]:
    """Return validation errors with rejected passwords taken out.

    A rejected value is quoted back in the reason an error carries, and
    the reason travels to whoever asked. The password of a repository
    is the one field of the file that may hold a credential, so what
    was rejected is named rather than shown.

    Parameters
    ----------
    errors : Iterable[ErrorDetails]
        Errors as pydantic reports them.

    Returns
    -------
    list[ErrorDetails]
        The same errors, with the input of a password replaced.

    """
    scrubbed: list[ErrorDetails] = []

    for error in errors:
        value = error['input']

        if 'password' in error['loc']:
            scrubbed.append({**error, 'input': REDACTED_PASSWORD})
        elif isinstance(value, dict) and 'password' in value:
            # A field reported as missing quotes the whole entry it is
            # missing from, password included.
            scrubbed.append(
                {**error, 'input': {**value, 'password': REDACTED_PASSWORD}},
            )
        else:
            scrubbed.append(error)

    return scrubbed


def _available() -> RepositoryStatus:
    """Build the state of a repository that answered just now."""
    return RepositoryStatus(state='available', checked_at=datetime.now(tz=UTC))


def _unavailable(error: RepositoryFetchError) -> RepositoryStatus:
    """Build the state of a repository that did not answer."""
    return RepositoryStatus(
        state='unavailable',
        checked_at=datetime.now(tz=UTC),
        reason=str(error.context.get('reason') or error),
    )


@dataclass(frozen=True)
class _Discovered:
    """Published repositories as one search returned them.

    Held to answer the same search again without spending the quota,
    and to revalidate it with the entity tag it came with.
    """

    entries: tuple[DiscoveredRepository, ...]
    total_count: int
    etag: str | None
    refreshed_at: datetime
    rate: DiscoveryRate


@dataclass
class _Fetched:
    """Bare repository a catalog was read from.

    Handed out to callers that read or install from it while the lock
    of the service is released, so it counts its users: what is
    dropped while somebody still reads it is removed once the last of
    them is done rather than under their feet.
    """

    path: Path
    repo_path: Path
    catalog: Catalog
    repository: Repository
    users: int = 0
    dropped: bool = False


class Repositories:
    """Connected repositories and the generators they publish.

    Owns the repositories file and, for every repository fetched in
    this process, a bare clone of it and the catalog read from it. All
    public methods are serialized through a single `RLock` and perform
    blocking IO, so a caller on an event loop runs them in a worker
    thread.

    The clones live in a temporary directory of their own and are
    dropped when a repository is refreshed, disconnected, or the
    service is closed.
    """

    def __init__(
        self,
        *,
        file_path: Path,
        generators_dir: Path,
        config_filename: str,
        fetch_timeout: float = DEFAULT_FETCH_TIMEOUT,
        discovery_ttl: float = DEFAULT_DISCOVERY_TTL,
    ) -> None:
        """Initialize Repositories.

        Parameters
        ----------
        file_path : Path
            Location of the repositories file.

        generators_dir : Path
            Directory the projects of the workspace live in.

        config_filename : str
            Name of the generator configuration file.

        fetch_timeout : float, default=DEFAULT_FETCH_TIMEOUT
            Timeout of a single fetch operation, in seconds.

        discovery_ttl : float, default=DEFAULT_DISCOVERY_TTL
            How long a read list of published repositories stands
            before it is read again, in seconds.

        """
        self._file = RepositoriesFile(file_path=file_path)
        self._generators_dir = generators_dir
        self._config_filename = config_filename
        self._fetch_timeout = fetch_timeout

        self._fetched: dict[str, _Fetched] = {}
        self._statuses: dict[str, RepositoryStatus] = {}
        self._fetch_locks: dict[str, threading.Lock] = {}
        self._discovery_ttl = discovery_ttl
        self._discovered: dict[tuple[str, int], _Discovered] = {}
        self._discovery_lock = threading.Lock()
        self._cache_dir: Path | None = None
        self._closed = False
        self._lock = threading.RLock()

    def get_all(self) -> RepositoryList:
        """Read all connected repositories.

        Returns
        -------
        RepositoryList
            All connected repositories.

        Raises
        ------
        RepositoryError
            If the repositories file cannot be read or validated.

        """
        with self._lock:
            return self._read()

    def get_all_with_status(self) -> list[ConnectedRepository]:
        """Read all connected repositories with their last check.

        Returns
        -------
        list[ConnectedRepository]
            All connected repositories, each carrying the result of
            the last check made in this process. A password holding a
            credential is redacted, so what comes back is what may be
            shown rather than what authenticates.

        Raises
        ------
        RepositoryError
            If the repositories file cannot be read or validated.

        """
        with self._lock:
            return [
                ConnectedRepository.of(
                    repository,
                    self._statuses.get(repository.name, _UNKNOWN),
                )
                for repository in self._read().root
            ]

    def check(self, name: str) -> RepositoryStatus:
        """Check that a repository answers, and record the result.

        Parameters
        ----------
        name : str
            Name of the repository.

        Returns
        -------
        RepositoryStatus
            Result of the check. A repository that did not answer is
            reported rather than raised, since the state of a
            repository is what the caller asked for.

        Raises
        ------
        RepositoryError
            If the repositories file cannot be read or validated.

        RepositoryNotFoundError
            If no repository with the provided name is connected.

        """
        with self._lock:
            repository = self._find(self._read(), name)

        return self._probe(repository)

    def get(self, name: str) -> Repository:
        """Read a single connected repository by name.

        Parameters
        ----------
        name : str
            Name of the repository.

        Returns
        -------
        Repository
            Connected repository.

        Raises
        ------
        RepositoryError
            If the repositories file cannot be read or validated.

        RepositoryNotFoundError
            If no repository with the provided name is connected.

        """
        with self._lock:
            return self._find(self._read(), name)

    def add(self, repository: Repository, *, verify: bool = True) -> None:
        """Connect a new repository.

        Parameters
        ----------
        repository : Repository
            Repository to connect.

        verify : bool, default=True
            Whether to check that the repository answers before
            connecting it.

        Raises
        ------
        RepositoryError
            If the repositories file cannot be read, validated or
            written.

        RepositoryConflictError
            If a repository with the same name, or the same repository
            at the same branch or tag, is already connected.

        RepositoryFetchError
            If the repository does not answer and `verify` is set.

        """
        with self._lock:
            repositories = self._read()
            self._reject_duplicate(repositories, repository)

        if verify:
            self._raise_status(self._probe(repository))

        with self._lock:
            repositories = self._read()
            self._reject_duplicate(repositories, repository)
            self._write((*repositories.root, repository))

    def remove(self, name: str) -> None:
        """Disconnect a repository.

        Parameters
        ----------
        name : str
            Name of the repository.

        Raises
        ------
        RepositoryError
            If the repositories file cannot be read, validated or
            written.

        RepositoryNotFoundError
            If no repository with the provided name is connected.

        """
        with self._lock:
            repositories = self._read()
            self._find(repositories, name)

            self._write(
                tuple(item for item in repositories.root if item.name != name),
            )
            self._drop_fetched(name)
            self._statuses.pop(name, None)

    def find_secret_users(self, secret: str) -> list[str]:
        """Read the repositories authenticating with a secret.

        Parameters
        ----------
        secret : str
            Name of the keyring secret.

        Returns
        -------
        list[str]
            Sorted names of the repositories holding the secret.

        Raises
        ------
        RepositoryError
            If the repositories file cannot be read or validated.

        """
        with self._lock:
            repositories = self._read()

        return sorted(
            repository.name
            for repository in repositories.root
            if repository.secret == secret
        )

    def repoint_secret(self, secret: str, new_name: str) -> list[str]:
        """Point the repositories holding a secret at another name.

        The value behind the secret is not read, so a repository keeps
        authenticating with whatever it did before.

        Parameters
        ----------
        secret : str
            Name the repositories hold.

        new_name : str
            Name to hold in its place.

        Returns
        -------
        list[str]
            Sorted names of the repositories that were repointed.

        Raises
        ------
        RepositoryError
            If the new name is not a valid secret name, or the
            repositories file cannot be read, validated or written.

        """
        with self._lock:
            repositories = self._read()
            users = [
                repository
                for repository in repositories.root
                if repository.secret == secret
            ]

            if not users:
                return []

            self._write(
                tuple(
                    self._with_secret(repository, new_name)
                    if repository.secret == secret
                    else repository
                    for repository in repositories.root
                ),
            )

        return sorted(repository.name for repository in users)

    def get_catalog(self, name: str) -> Catalog:
        """Read the catalog of a repository, fetching it if needed.

        The catalog read in this process is returned as is; a
        repository that was never fetched here is fetched now.

        Parameters
        ----------
        name : str
            Name of the repository.

        Returns
        -------
        Catalog
            Catalog of the repository.

        Raises
        ------
        RepositoryError
            If the repositories file cannot be read or validated.

        RepositoryNotFoundError
            If no repository with the provided name is connected.

        RepositoryFetchError
            If the repository cannot be fetched.

        CatalogError
            If the fetched repository publishes no catalog.

        """
        with self._leased(name) as fetched:
            return self._with_installed(fetched.catalog, fetched.repository)

    def refresh(self, name: str) -> Catalog:
        """Fetch a repository and read its catalog anew.

        Parameters
        ----------
        name : str
            Name of the repository.

        Returns
        -------
        Catalog
            Catalog of the repository.

        Raises
        ------
        RepositoryError
            If the repositories file cannot be read or validated.

        RepositoryNotFoundError
            If no repository with the provided name is connected.

        RepositoryFetchError
            If the repository cannot be fetched.

        CatalogError
            If the fetched repository publishes no catalog.

        """
        with self._lock:
            repository = self._find(self._read(), name)

        fetched = self._fetch(repository)

        try:
            return self._with_installed(fetched.catalog, fetched.repository)
        finally:
            with self._lock:
                self._release(fetched)

    def discover(self, query: str | None = None, page: int = 1) -> Discovery:
        """Search the repositories that publish generators in the open.

        A repository appears in the list by carrying the topic that
        defines it, and the content of a listed repository is not
        reviewed. What was read is held for a while and answered from,
        since an anonymous search has a small quota.

        Parameters
        ----------
        query : str | None, default=None
            Words to narrow the list with.

        page : int, default=1
            Page of the results, counted from one.

        Returns
        -------
        Discovery
            Published repositories, the ones published by Eventum
            first and the rest by the stars they carry, each marked
            with whether this instance is already connected to it.

        Raises
        ------
        RepositoryDiscoveryLimitError
            If searching is refused until the quota resets.

        RepositoryDiscoveryError
            If the repositories cannot be searched.

        RepositoryError
            If the repositories file cannot be read or validated.

        """
        words = normalize_query(query)
        discovered = self._search(words, page)

        return Discovery(
            topic=DISCOVERY_TOPIC,
            query=words,
            entries=self._mark_connected(discovered.entries),
            total_count=discovered.total_count,
            refreshed_at=discovered.refreshed_at,
            rate=discovered.rate,
        )

    def _search(self, words: str, page: int) -> _Discovered:
        """Return the answer of a search, reading it again when stale.

        The lock is held across the request, so several callers asking
        at once spend one search between them rather than one each.
        """
        key = (words, page)

        with self._discovery_lock:
            held = self._discovered.get(key)

            if held is not None and not self._is_stale(held):
                return held

            search = search_repositories(
                query=words,
                page=page,
                etag=held.etag if held is not None else None,
            )
            now = datetime.now(tz=UTC)

            if search.modified:
                held = _Discovered(
                    entries=_ordered(search.entries),
                    total_count=search.total_count,
                    etag=search.etag,
                    refreshed_at=now,
                    rate=search.rate,
                )
            else:
                # Nothing changed since the answer was read, so it
                # stands as it is and only its age is reset.
                held = replace(
                    cast('_Discovered', held),
                    refreshed_at=now,
                    rate=search.rate,
                )

            self._discovered[key] = held
            self._forget_oldest_searches()

            return held

    def _forget_oldest_searches(self) -> None:
        """Drop the oldest searches once too many are held."""
        excess = len(self._discovered) - DISCOVERY_CACHE_LIMIT

        if excess <= 0:
            return

        oldest = sorted(
            self._discovered,
            key=lambda key: self._discovered[key].refreshed_at,
        )

        for key in oldest[:excess]:
            del self._discovered[key]

    def _is_stale(self, discovered: _Discovered) -> bool:
        """Whether a read list is old enough to be read again."""
        age = datetime.now(tz=UTC) - discovered.refreshed_at

        return age.total_seconds() >= self._discovery_ttl

    def _mark_connected(
        self,
        entries: tuple[DiscoveredRepository, ...],
    ) -> tuple[DiscoveredRepository, ...]:
        """Mark the repositories this instance is already connected to.

        The connected list is read here rather than when the search
        runs, so a repository connected since is marked without
        searching again.
        """
        with self._lock:
            connected = {
                identify_repository(repository.url)
                for repository in self._read().root
            }

        return tuple(
            entry.model_copy(
                update={
                    'connected': identify_repository(entry.url) in connected,
                },
            )
            for entry in entries
        )

    def install(self, name: str, entry: str, project_name: str) -> int:
        """Install a published generator as a project.

        Parameters
        ----------
        name : str
            Name of the repository.

        entry : str
            Name of the published generator.

        project_name : str
            Name of the project directory to install into.

        Returns
        -------
        int
            Number of installed files.

        Raises
        ------
        RepositoryError
            If the repositories file cannot be read or validated.

        RepositoryNotFoundError
            If no repository with the provided name is connected.

        RepositoryFetchError
            If the repository cannot be fetched.

        CatalogError
            If the fetched repository publishes no catalog.

        CatalogEntryNotFoundError
            If the repository publishes no such generator.

        InstallNameError
            If the project name cannot name a project directory.

        InstallConflictError
            If a project with the requested name already exists.

        InstallContentError
            If the published generator holds no installable project.

        InstallError
            If the workspace cannot be written.

        """
        with self._leased(name) as fetched:
            published = self._find_entry(fetched.catalog, entry)

            # Writing a project is file work rather than a change of
            # what the service holds, so it runs outside the lock; the
            # lease is what keeps the fetched repository in place.
            installed = install_entry(
                repo_path=fetched.repo_path,
                revision=fetched.catalog.revision,
                entry=entry,
                generators_dir=self._generators_dir,
                project_name=project_name,
                config_filename=self._config_filename,
                # The project keeps its own origin, so what it came
                # from survives a rename, an export and this process.
                source=build_source(
                    repository=fetched.repository.name,
                    url=fetched.repository.url,
                    ref=fetched.repository.ref,
                    entry=entry,
                    revision=fetched.catalog.revision,
                    tree=published.tree,
                ),
            )

            logger.info(
                'Generator is installed from repository',
                name=name,
                value=entry,
                count=installed,
            )

            return installed

    def close(self) -> None:
        """Drop everything fetched by the service.

        A closed service fetches nothing more, so a fetch still
        running when this is called keeps nothing of what it read.
        """
        with self._lock:
            self._closed = True
            self._fetched.clear()

            if self._cache_dir is not None:
                shutil.rmtree(self._cache_dir, ignore_errors=True)
                self._cache_dir = None

    def _read(self) -> RepositoryList:
        """Read and validate the repositories file.

        Raises
        ------
        RepositoryError
            If the file cannot be read or fails schema validation.

        """
        try:
            return RepositoryList.model_validate(self._file.read())
        except ValidationError as e:
            msg = 'Repositories file fails schema validation'
            raise RepositoryError(
                msg,
                context={
                    'file_path': str(self._file.path),
                    'reason': prettify_validation_errors(
                        _without_passwords(e.errors()),
                    ),
                },
            ) from None

    def _write(self, repositories: tuple[Repository, ...]) -> None:
        """Persist the connected repositories."""
        self._file.write(
            [
                repository.model_dump(mode='json', exclude_none=True)
                for repository in repositories
            ],
        )

    def _with_secret(self, repository: Repository, secret: str) -> Repository:
        """Rebuild a repository holding another secret name.

        Built through validation rather than copied: the new name comes
        from the keyring, which accepts names the repositories file
        cannot carry, and a file written past its own schema fails
        every later read of it.

        Raises
        ------
        RepositoryError
            If the name is not valid for a repository.

        """
        try:
            return Repository.model_validate(
                {**repository.model_dump(), 'secret': secret},
            )
        except ValidationError as e:
            msg = 'Secret name is not valid for a repository'
            raise RepositoryError(
                msg,
                context={
                    'name': repository.name,
                    'value': secret,
                    'reason': prettify_validation_errors(e.errors()),
                },
            ) from None

    def _find_entry(self, catalog: Catalog, entry: str) -> CatalogEntry:
        """Return the catalog entry with the provided name.

        Raises
        ------
        CatalogEntryNotFoundError
            If the catalog holds no such entry.

        """
        for published in catalog.entries:
            if published.name == entry:
                return published

        msg = 'Repository publishes no such generator'
        raise CatalogEntryNotFoundError(msg, context={'name': entry})

    def _with_installed(
        self,
        catalog: Catalog,
        repository: Repository,
    ) -> Catalog:
        """Return a catalog naming what of it is already installed.

        The workspace is read here rather than when the catalog is
        fetched, so an installation made since is reflected without
        reaching the remote again.
        """
        installed = collect_installed(
            self._generators_dir,
            repository.url,
            repository.ref,
        )

        return catalog.model_copy(
            update={
                'entries': [
                    entry.model_copy(
                        update={
                            'installed_as': tuple(
                                InstalledProject(
                                    project=project,
                                    revision=source.revision,
                                    installed_at=source.installed_at,
                                    outdated=source.tree != entry.tree,
                                )
                                for project, source in sorted(
                                    installed.get(entry.name, []),
                                )
                            ),
                        },
                    )
                    for entry in catalog.entries
                ],
            },
        )

    def _reject_duplicate(
        self,
        repositories: RepositoryList,
        repository: Repository,
    ) -> None:
        """Refuse a repository already connected.

        The same remote may be connected more than once to follow two
        of its branches, so what may not repeat is a name, and a
        remote at a branch or a tag already followed.

        Raises
        ------
        RepositoryConflictError
            If the name or the remote at that reference is taken.

        """
        for item in repositories.root:
            if item.name == repository.name:
                msg = 'Repository with this name is already connected'
                raise RepositoryConflictError(
                    msg,
                    context={'name': repository.name},
                )

            same_remote = identify_repository(item.url) == (
                identify_repository(repository.url)
            )

            if same_remote and item.ref == repository.ref:
                msg = (
                    'This repository is already connected at the same '
                    'branch or tag'
                )
                raise RepositoryConflictError(
                    msg,
                    context={
                        'name': item.name,
                        'url': repository.url,
                        'ref': repository.ref,
                    },
                )

    def _probe(self, repository: Repository) -> RepositoryStatus:
        """Check that a repository answers and record the result.

        Runs outside the lock, since it reaches a remote.

        Raises
        ------
        RepositorySecretError
            If the secret of the repository cannot be read. A local
            misconfiguration is not the remote being unavailable, so
            it is raised rather than recorded as its state.

        """
        password = self._resolve_password(repository)

        try:
            probe_repository(
                repository,
                password=password,
                timeout=self._fetch_timeout,
            )
        except RepositoryFetchError as e:
            status = _unavailable(e)
        else:
            status = _available()

        self._record_status(repository.name, status)

        return status

    def _record_status(self, name: str, status: RepositoryStatus) -> None:
        """Record the state of a repository that is still connected.

        A repository that failed to connect, or was disconnected while
        it was being checked, keeps no state behind: the next one to
        take that name would inherit it.
        """
        with self._lock:
            if any(item.name == name for item in self._read().root):
                self._statuses[name] = status

    def _raise_status(self, status: RepositoryStatus) -> None:
        """Turn an unavailable repository into a failure.

        Raises
        ------
        RepositoryFetchError
            If the repository did not answer the check.

        """
        if status.state != 'unavailable':
            return

        msg = 'Failed to reach repository'
        raise RepositoryFetchError(msg, context={'reason': status.reason})

    def _find(self, repositories: RepositoryList, name: str) -> Repository:
        """Return the repository with the provided name.

        Raises
        ------
        RepositoryNotFoundError
            If no repository with the provided name is connected.

        """
        for repository in repositories.root:
            if repository.name == name:
                return repository

        msg = 'Repository with this name is not connected'
        raise RepositoryNotFoundError(msg, context={'name': name})

    @contextmanager
    def _leased(self, name: str) -> Iterator[_Fetched]:
        """Hold what was fetched for a repository, fetching if none.

        The fetched repository is kept alive for the body: a refresh
        or a disconnect that lands meanwhile drops it from the service
        but leaves the directory until the body is done with it.

        Raises
        ------
        RepositoryError
            If the repositories file cannot be read or validated.

        RepositoryNotFoundError
            If no repository with the provided name is connected.

        RepositoryFetchError
            If the repository cannot be fetched.

        RepositorySecretError
            If the secret of the repository cannot be read.

        CatalogError
            If the fetched repository publishes no catalog.

        """
        fetched = self._ensure_fetched(name)

        try:
            yield fetched
        finally:
            with self._lock:
                self._release(fetched)

    def _ensure_fetched(self, name: str) -> _Fetched:
        """Return a held handle of what was fetched, fetching if none.

        A repository is fetched once however many callers ask for it
        at the same time: the rest wait for that fetch and take what
        it stored.
        """
        with self._lock:
            fetched = self._acquire(name)

            if fetched is not None:
                return fetched

            repository = self._find(self._read(), name)
            fetch_lock = self._fetch_locks.setdefault(name, threading.Lock())

        with fetch_lock:
            with self._lock:
                fetched = self._acquire(name)

                if fetched is not None:
                    return fetched

            return self._fetch(repository)

    def _acquire(self, name: str) -> _Fetched | None:
        """Take a hold of what was fetched for a repository."""
        fetched = self._fetched.get(name)

        if fetched is not None:
            fetched.users += 1

        return fetched

    def _release(self, fetched: _Fetched) -> None:
        """Give up a hold, removing what nothing holds any more."""
        fetched.users -= 1

        if fetched.dropped and fetched.users <= 0:
            shutil.rmtree(fetched.path, ignore_errors=True)

    def _fetch(self, repository: Repository) -> _Fetched:
        """Fetch a repository and read its catalog.

        Runs outside the lock, since a fetch reaches a remote and takes
        as long as that remote does: holding the lock would stall every
        other caller for the whole of it. What is returned is held for
        the caller, which gives it up through `_release`.

        Raises
        ------
        RepositoryFetchError
            If the repository cannot be fetched.

        RepositorySecretError
            If the secret of the repository cannot be read.

        CatalogError
            If the fetched repository publishes no catalog.

        RepositoryError
            If the service is closed.

        """
        logger.info(
            'Fetching repository',
            name=repository.name,
            url=repository.url,
            ref=repository.ref,
        )

        password = self._resolve_password(repository)

        with self._lock:
            cache_dir = self._ensure_cache_dir()

            # The bare repository is initialized one level below a
            # directory of its own, since a fetch initializes the
            # directory it is given and cannot take an existing one.
            try:
                holder = Path(tempfile.mkdtemp(dir=cache_dir))
            except OSError as e:
                msg = 'Failed to create the directory for the repository'
                raise RepositoryError(
                    msg,
                    context={'path': str(cache_dir), 'reason': str(e)},
                ) from None

        destination = holder / _REPO_DIRNAME

        try:
            revision = fetch_repository(
                repository,
                destination,
                password=password,
                timeout=self._fetch_timeout,
            )
            catalog = read_catalog(
                destination,
                revision,
                config_filename=self._config_filename,
            )
        except RepositoryFetchError as e:
            shutil.rmtree(holder, ignore_errors=True)
            self._record_status(repository.name, _unavailable(e))
            raise
        except Exception:
            shutil.rmtree(holder, ignore_errors=True)
            raise

        # A fetch that came back is the strongest statement there is
        # that the repository is there, so it stands as the check.
        self._record_status(repository.name, _available())

        logger.info(
            'Repository catalog is read',
            name=repository.name,
            value=revision,
            count=len(catalog.entries),
        )

        fetched = _Fetched(
            path=holder,
            repo_path=destination,
            catalog=catalog,
            repository=repository,
        )

        with self._lock:
            # A service closed while this fetch was running keeps
            # nothing: the directory is removed here rather than left
            # behind by a caller that is no longer there.
            if self._closed:
                shutil.rmtree(holder, ignore_errors=True)
                msg = 'Repositories are closed'
                raise RepositoryError(msg, context={'name': repository.name})

            self._drop_fetched(repository.name)
            self._fetched[repository.name] = fetched
            fetched.users += 1

        return fetched

    def _resolve_password(self, repository: Repository) -> str | None:
        """Read the password a repository authenticates with.

        A password is taken as it is kept, apart from the keyring
        secrets it refers to, which are read here rather than when the
        repository is connected - so a secret added afterwards is
        picked up by the next fetch.

        Raises
        ------
        RepositorySecretError
            If a secret the password refers to is missing in the
            keyring or cannot be read.

        """
        if repository.password is None:
            return None

        try:
            return resolve_secrets(repository.password)
        except ValueError as e:
            context: dict[str, Any] = {
                'name': repository.name,
                'reason': str(e),
                'hint': 'Add the secret using the eventum-keyring CLI',
            }

            reference = secret_reference(repository.password)
            if reference is not None:
                context['secret'] = reference

            msg = 'Failed to read the secret of the repository'
            raise RepositorySecretError(msg, context=context) from None

    def _ensure_cache_dir(self) -> Path:
        """Return the directory the fetched repositories live in.

        Raises
        ------
        RepositoryError
            If the service is closed, or the directory cannot be
            created.

        """
        if self._closed:
            msg = 'Repositories are closed'
            raise RepositoryError(msg, context={})

        if self._cache_dir is not None:
            return self._cache_dir

        try:
            self._cache_dir = Path(tempfile.mkdtemp(prefix=_CACHE_PREFIX))
        except OSError as e:
            msg = 'Failed to create the directory for fetched repositories'
            raise RepositoryError(msg, context={'reason': str(e)}) from None

        return self._cache_dir

    def _drop_fetched(self, name: str) -> None:
        """Drop what was fetched for a repository.

        What somebody still holds is marked instead of removed, and
        goes when the last of them gives it up.
        """
        fetched = self._fetched.pop(name, None)

        if fetched is None:
            return

        fetched.dropped = True

        if fetched.users <= 0:
            shutil.rmtree(fetched.path, ignore_errors=True)
