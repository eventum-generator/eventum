"""Dependency context for MCP tools.

Tools depend on these Protocols, not on globals; composition roots
(stdio in cli, HTTP-mount in server) supply concrete implementations.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable


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
