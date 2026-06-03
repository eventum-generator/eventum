"""Transport-neutral generator-workspace operations.

Path-safety, text file IO, and config serialization shared by the
api, cli, and mcp driver adapters. No transport concerns here.
"""

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

from eventum.exceptions import ContextualError


class WorkspaceError(ContextualError):
    """Error while accessing the generator workspace."""


def resolve_generator_dir(generators_dir: Path, name: str) -> Path:
    """Resolve a generator directory, rejecting paths that escape the
    generators directory.

    Parameters
    ----------
    generators_dir : Path
        Root directory that contains generator subdirectories.
    name : str
        Name of the generator directory to resolve.

    Returns
    -------
    Path
        Resolved absolute path to the generator directory.

    Raises
    ------
    WorkspaceError
        If the resolved path is outside ``generators_dir``.

    """
    base = generators_dir.resolve()
    path = (base / name).resolve()

    if not path.is_relative_to(base):
        msg = 'Accessing directories outside generators dir is not allowed'
        raise WorkspaceError(msg, context={'name': name})

    return path


def resolve_generator_file(
    generators_dir: Path,
    name: str,
    relative: Path,
) -> Path:
    """Resolve a file inside a generator directory, rejecting absolute
    paths and parent traversal.

    Parameters
    ----------
    generators_dir : Path
        Root directory that contains generator subdirectories.
    name : str
        Name of the generator directory.
    relative : Path
        Relative path to the file within the generator directory.

    Returns
    -------
    Path
        Resolved absolute path to the file.

    Raises
    ------
    WorkspaceError
        If ``relative`` is absolute, uses ``..``, or the resolved path
        escapes the generator directory.

    """
    ensure_relative(relative)
    return (resolve_generator_dir(generators_dir, name) / relative).resolve()


def ensure_relative(relative: Path) -> Path:
    """Reject absolute paths and parent traversal; return the path.

    Parameters
    ----------
    relative : Path
        Path to validate.

    Returns
    -------
    Path
        The same path, if valid.

    Raises
    ------
    WorkspaceError
        If the path is absolute or contains ``..`` components.

    """
    if relative.is_absolute():
        msg = 'File path cannot be absolute'
        raise WorkspaceError(msg, context={'file_path': str(relative)})

    if any(part == '..' for part in relative.parts):
        msg = 'Parent directory traversal is not allowed'
        raise WorkspaceError(msg, context={'file_path': str(relative)})

    return relative


def read_text(path: Path) -> str:
    """Read a text file, translating OS errors to `WorkspaceError`.

    Parameters
    ----------
    path : Path
        Path to read.

    Returns
    -------
    str
        File contents.

    Raises
    ------
    WorkspaceError
        If the file cannot be read.

    """
    try:
        return path.read_text()
    except OSError as e:
        msg = 'Failed to read file'
        raise WorkspaceError(
            msg,
            context={'reason': str(e), 'file_path': str(path)},
        ) from None


def write_text(path: Path, content: str) -> None:
    """Write a text file, creating parent directories as needed.

    Parameters
    ----------
    path : Path
        Destination path.
    content : str
        Text to write.

    Raises
    ------
    WorkspaceError
        If the file cannot be written.

    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    except OSError as e:
        msg = 'Failed to write file'
        raise WorkspaceError(
            msg,
            context={'reason': str(e), 'file_path': str(path)},
        ) from None


def dump_config_yaml(data: Mapping[str, Any]) -> str:
    """Serialize a config mapping to YAML matching the Studio writer.

    Parameters
    ----------
    data : Mapping[str, Any]
        Config data to serialize.

    Returns
    -------
    str
        YAML string with insertion-order keys preserved.

    """
    return yaml.dump(data=dict(data), sort_keys=False)
