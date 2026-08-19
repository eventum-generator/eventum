"""Operations over connected generator repositories."""

import shutil
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path

import structlog
from pydantic import ValidationError

from eventum.app.repositories.catalog import read_catalog
from eventum.app.repositories.exceptions import (
    RepositoryConflictError,
    RepositoryError,
    RepositoryFetchError,
    RepositoryNotFoundError,
)
from eventum.app.repositories.fetching import (
    DEFAULT_FETCH_TIMEOUT,
    fetch_repository,
)
from eventum.app.repositories.installing import install_entry
from eventum.app.repositories.models import (
    Catalog,
    Repository,
    RepositoryList,
)
from eventum.app.repositories.storage import RepositoriesFile
from eventum.security.manage import get_secret
from eventum.utils.validation_prettier import prettify_validation_errors

logger = structlog.stdlib.get_logger()

_CACHE_PREFIX = 'eventum-repositories-'
_REPO_DIRNAME = 'repo'


@dataclass(frozen=True)
class _Fetched:
    """Bare repository a catalog was read from."""

    path: Path
    catalog: Catalog


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

        """
        self._file = RepositoriesFile(file_path=file_path)
        self._generators_dir = generators_dir
        self._config_filename = config_filename
        self._fetch_timeout = fetch_timeout

        self._fetched: dict[str, _Fetched] = {}
        self._cache_dir: Path | None = None
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

    def add(self, repository: Repository) -> None:
        """Connect a new repository.

        Parameters
        ----------
        repository : Repository
            Repository to connect.

        Raises
        ------
        RepositoryError
            If the repositories file cannot be read, validated or
            written.

        RepositoryConflictError
            If a repository with the same name is already connected.

        """
        with self._lock:
            repositories = self._read()

            if any(item.name == repository.name for item in repositories.root):
                msg = 'Repository with this name is already connected'
                raise RepositoryConflictError(
                    msg,
                    context={'name': repository.name},
                )

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
        return self._ensure_fetched(name).catalog

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

        return self._fetch(repository).catalog

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
        fetched = self._ensure_fetched(name)

        with self._lock:
            installed = install_entry(
                repo_path=fetched.path / _REPO_DIRNAME,
                revision=fetched.catalog.revision,
                entry=entry,
                generators_dir=self._generators_dir,
                project_name=project_name,
                config_filename=self._config_filename,
            )

            logger.info(
                'Generator is installed from repository',
                name=name,
                value=entry,
                count=installed,
            )

            return installed

    def close(self) -> None:
        """Drop everything fetched by the service."""
        with self._lock:
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
                    'reason': prettify_validation_errors(e.errors()),
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

    def _ensure_fetched(self, name: str) -> _Fetched:
        """Return what was fetched for a repository, fetching if none.

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
            fetched = self._fetched.get(name)

            if fetched is not None:
                return fetched

            repository = self._find(self._read(), name)

        return self._fetch(repository)

    def _fetch(self, repository: Repository) -> _Fetched:
        """Fetch a repository and read its catalog.

        Runs outside the lock, since a fetch reaches a remote and takes
        as long as that remote does: holding the lock would stall every
        other caller for the whole of it. Two fetches of one repository
        therefore may overlap, and the one that finishes last is the
        one that is kept.

        Raises
        ------
        RepositoryFetchError
            If the repository cannot be fetched.

        CatalogError
            If the fetched repository publishes no catalog.

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
        holder = Path(tempfile.mkdtemp(dir=cache_dir))
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
        except Exception:
            shutil.rmtree(holder, ignore_errors=True)
            raise

        logger.info(
            'Repository catalog is read',
            name=repository.name,
            value=revision,
            count=len(catalog.entries),
        )

        fetched = _Fetched(path=holder, catalog=catalog)

        with self._lock:
            self._drop_fetched(repository.name)
            self._fetched[repository.name] = fetched

        return fetched

    def _resolve_password(self, repository: Repository) -> str | None:
        """Read the secret a repository authenticates with.

        Raises
        ------
        RepositoryFetchError
            If the secret is missing in the keyring or cannot be read.

        """
        if repository.secret is None:
            return None

        try:
            return get_secret(repository.secret)
        except (ValueError, OSError) as e:
            msg = 'Failed to read the secret of the repository'
            raise RepositoryFetchError(
                msg,
                context={
                    'name': repository.name,
                    'value': repository.secret,
                    'reason': str(e),
                    'hint': 'Add the secret using the eventum-keyring CLI',
                },
            ) from None

    def _ensure_cache_dir(self) -> Path:
        """Return the directory the fetched repositories live in.

        Raises
        ------
        RepositoryError
            If the directory cannot be created.

        """
        if self._cache_dir is not None:
            return self._cache_dir

        try:
            self._cache_dir = Path(tempfile.mkdtemp(prefix=_CACHE_PREFIX))
        except OSError as e:
            msg = 'Failed to create the directory for fetched repositories'
            raise RepositoryError(msg, context={'reason': str(e)}) from None

        return self._cache_dir

    def _drop_fetched(self, name: str) -> None:
        """Drop what was fetched for a repository."""
        fetched = self._fetched.pop(name, None)

        if fetched is not None:
            shutil.rmtree(fetched.path, ignore_errors=True)
