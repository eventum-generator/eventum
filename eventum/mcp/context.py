"""Dependency context for MCP tools.

Tools depend on these Protocols, not on globals; composition roots
(stdio in cli, HTTP-mount in server) supply concrete implementations.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol, runtime_checkable

from eventum.app.manager import GeneratorManager
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
    def read_only(self) -> bool:
        """Whether write tools are disabled."""
        ...


@dataclass(frozen=True)
class FileAuthoringContext:
    """File-backed authoring context used by the stdio transport."""

    generators_dir: Path
    read_only: bool


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
