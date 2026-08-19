"""Dependency context for MCP tools.

Tools depend on these Protocols, not on globals; composition roots
(stdio in cli, HTTP-mount in server) supply concrete implementations.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Protocol, runtime_checkable

from eventum.app.hooks import InstanceHooks
from eventum.app.manager import GeneratorManager
from eventum.app.models.parameters.path import (
    DEFAULT_REPOSITORIES_FILENAME,
)
from eventum.app.models.settings import Settings
from eventum.app.repositories import Repositories
from eventum.app.startup import Startup
from eventum.core.parameters import GenerationParameters


@runtime_checkable
class AuthoringContext(Protocol):
    """Capabilities available to authoring tools in any transport."""

    @property
    def generators_dir(self) -> Path:
        """Absolute path to the generators directory."""
        ...

    @property
    def config_filename(self) -> str:
        """Generator config filename inside a generator directory."""
        ...

    @property
    def read_only(self) -> bool:
        """Whether write tools are disabled."""
        ...

    @property
    def repositories(self) -> Repositories:
        """The connected generator repositories service."""
        ...

    def is_live_managed(self, generator_id: str) -> bool:
        """Whether a generator with this id is managed live.

        Always False for authoring-only (stdio) contexts, which have
        no live runtime; a live context checks its manager.
        """
        ...


@dataclass(frozen=True)
class FileAuthoringContext:
    """File-backed authoring context used by the stdio transport.

    Attributes
    ----------
    generators_dir : Path
        Directory the projects of the workspace live in.

    read_only : bool
        Whether write tools are disabled.

    config_filename : str, default='generator.yml'
        Name of the generator configuration file.

    repositories_file : Path | None, default=None
        Location of the list of connected repositories. When not
        provided, the file named "repositories.yml" next to the
        generators directory is used - where an instance keeps it,
        since that file lives beside the startup file.

    repositories : Repositories
        Connected repositories service, built from the paths above.

    """

    generators_dir: Path
    read_only: bool
    config_filename: str = 'generator.yml'
    repositories_file: Path | None = None

    # Built from the paths above rather than injected: stdio has no
    # running instance to share a service with.
    repositories: Repositories = field(init=False)

    def __post_init__(self) -> None:
        """Build the repositories service this context serves."""
        object.__setattr__(
            self,
            'repositories',
            Repositories(
                file_path=(
                    self.repositories_file
                    if self.repositories_file is not None
                    else self.generators_dir.parent
                    / DEFAULT_REPOSITORIES_FILENAME
                ),
                generators_dir=self.generators_dir,
                config_filename=self.config_filename,
            ),
        )

    def is_live_managed(self, generator_id: str) -> bool:  # noqa: ARG002
        """Stdio has no live runtime, so nothing is live-managed."""
        return False


@runtime_checkable
class LiveContext(AuthoringContext, Protocol):
    """Authoring context plus live generator management."""

    @property
    def manager(self) -> GeneratorManager:
        """The generator manager."""
        ...

    @property
    def startup(self) -> Startup:
        """The startup-config service."""
        ...

    @property
    def generation(self) -> GenerationParameters:
        """Generation parameters for newly registered generators."""
        ...

    @property
    def logs_dir(self) -> Path:
        """Absolute path to the log files directory."""
        ...

    @property
    def log_format(self) -> Literal['plain', 'json']:
        """Log file format - selects the log file extension."""
        ...

    @property
    def settings(self) -> Settings:
        """The running instance settings (a snapshot at injection)."""
        ...

    @property
    def hooks(self) -> InstanceHooks:
        """Hooks controlling the running instance (settings/lifecycle)."""
        ...


@dataclass(frozen=True)
class ServerLiveContext:
    """Live context backed by the server's manager and startup."""

    generators_dir: Path
    read_only: bool
    manager: GeneratorManager
    startup: Startup
    generation: GenerationParameters
    logs_dir: Path
    log_format: Literal['plain', 'json']
    settings: Settings
    hooks: InstanceHooks
    repositories: Repositories
    config_filename: str = 'generator.yml'

    def is_live_managed(self, generator_id: str) -> bool:
        """Whether the manager currently holds this generator id."""
        return generator_id in self.manager.generator_ids
