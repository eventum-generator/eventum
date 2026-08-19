"""Exceptions of connected generator repositories."""

from eventum.exceptions import ContextualError


class RepositoryError(ContextualError):
    """Error while working with a connected repository."""


class RepositoryNotFoundError(RepositoryError):
    """Repository with the requested name is not connected."""


class RepositoryConflictError(RepositoryError):
    """Repository with the requested name is already connected."""


class RepositoryFetchError(RepositoryError):
    """Repository cannot be fetched from its remote."""


class RepositorySecretError(RepositoryError):
    """Secret a repository authenticates with cannot be read."""


class RepositoryDiscoveryError(RepositoryError):
    """Repositories published in the open cannot be searched."""


class RepositoryDiscoveryLimitError(RepositoryDiscoveryError):
    """Searching is refused until the quota of this address resets."""


class CatalogError(RepositoryError):
    """Fetched repository does not hold a readable catalog."""


class CatalogEntryNotFoundError(RepositoryError):
    """Catalog holds no entry with the requested name."""


class InstallError(RepositoryError):
    """Catalog entry cannot be installed into the workspace."""


class InstallNameError(InstallError):
    """Requested project name cannot name a project directory."""


class InstallConflictError(InstallError):
    """Project with the requested name already exists."""


class InstallContentError(InstallError):
    """Published generator does not hold an installable project."""
