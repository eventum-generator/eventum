"""Transport-neutral generator-workspace operations.

Path-safety and text file IO shared by the api and mcp driver
adapters. No transport concerns here.
"""

import shutil
from pathlib import Path

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

    gen_dir = resolve_generator_dir(generators_dir, name)
    resolved = (gen_dir / relative).resolve()

    if not resolved.is_relative_to(gen_dir):
        msg = 'File path escapes the generator directory'
        raise WorkspaceError(msg, context={'file_path': str(relative)})

    return resolved


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
    """Read a text file, translating failures to `WorkspaceError`.

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
        If the file cannot be read or decoded as text.

    """
    try:
        return path.read_text()
    except (OSError, UnicodeDecodeError) as e:
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
        If the file cannot be written or the content cannot be
        encoded.

    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    except (OSError, UnicodeEncodeError) as e:
        msg = 'Failed to write file'
        raise WorkspaceError(
            msg,
            context={'reason': str(e), 'file_path': str(path)},
        ) from None


def delete_file(path: Path) -> None:
    """Delete a file, translating OS errors to `WorkspaceError`.

    Parameters
    ----------
    path : Path
        Path to delete.

    Raises
    ------
    WorkspaceError
        If the file cannot be deleted.

    """
    try:
        path.unlink()
    except OSError as e:
        msg = 'Failed to delete file'
        raise WorkspaceError(
            msg,
            context={'reason': str(e), 'file_path': str(path)},
        ) from None


def delete_dir(path: Path) -> None:
    """Recursively delete a directory, translating OS errors.

    Parameters
    ----------
    path : Path
        Directory to delete.

    Raises
    ------
    WorkspaceError
        If the directory cannot be deleted.

    """
    try:
        shutil.rmtree(path)
    except OSError as e:
        msg = 'Failed to delete directory'
        raise WorkspaceError(
            msg,
            context={'reason': str(e), 'file_path': str(path)},
        ) from None
