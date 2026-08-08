"""Transport-neutral generator-workspace operations.

Path-safety and text file IO shared by the api and mcp driver
adapters. No transport concerns here.
"""

import shutil
from pathlib import Path
from typing import NamedTuple

from eventum.core.config_loader import extract_secrets
from eventum.exceptions import ContextualError

_LINE_BREAK = b'\n'


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
        return path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError) as e:
        msg = 'Failed to read file'
        raise WorkspaceError(
            msg,
            context={'reason': str(e), 'file_path': str(path)},
        ) from None


class TextWindow(NamedTuple):
    """Bounded window of a text file.

    Attributes
    ----------
    content : str
        Content of the window.

    offset : int
        Byte offset the window starts at.

    next_offset : int | None
        Byte offset to continue reading from, or `None` when the window
        reaches the end of the file.

    size_in_bytes : int
        Size of the whole file.

    """

    content: str
    offset: int
    next_offset: int | None
    size_in_bytes: int


def read_text_window(path: Path, offset: int, limit: int) -> TextWindow:
    """Read at most `limit` bytes of a text file, starting at `offset`.

    A window that stops short of the end of the file is cut back to its
    last complete line, so consecutive windows never split a line. A
    window holding no line break at all is returned as it is, which
    keeps a single oversized line readable and every window advancing.

    Undecodable bytes are replaced instead of failing the read - a
    window may begin or end inside a multi-byte character.

    Parameters
    ----------
    path : Path
        Path to read.

    offset : int
        Byte offset to start at. Clamped to the file bounds.

    limit : int
        Maximum number of bytes to read. Values below one are read as
        one, so a window always advances.

    Returns
    -------
    TextWindow
        Window content with the offsets needed to continue.

    Raises
    ------
    WorkspaceError
        If the file cannot be read.

    """
    try:
        size = path.stat().st_size

        with path.open('rb') as f:
            f.seek(min(max(offset, 0), size))
            start = f.tell()
            data = f.read(max(limit, 1))
    except OSError as e:
        msg = 'Failed to read file'
        raise WorkspaceError(
            msg,
            context={'reason': str(e), 'file_path': str(path)},
        ) from None

    end = start + len(data)

    if end < size:
        last_line_end = data.rfind(_LINE_BREAK) + 1

        if last_line_end > 0:
            data = data[:last_line_end]
            end = start + last_line_end

    return TextWindow(
        content=data.decode('utf-8', errors='replace'),
        offset=start,
        next_offset=end if end < size else None,
        size_in_bytes=size,
    )


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
        path.write_text(content, encoding='utf-8')
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


def rename_generator_dir(
    generators_dir: Path,
    name: str,
    new_name: str,
) -> Path:
    """Rename a generator directory inside the generators directory.

    Parameters
    ----------
    generators_dir : Path
        Root directory that contains generator subdirectories.
    name : str
        Current name of the generator directory.
    new_name : str
        Name to rename the directory to. Must be a single directory
        name, since only directories directly inside
        ``generators_dir`` are recognized as generators.

    Returns
    -------
    Path
        Resolved absolute path of the renamed directory.

    Raises
    ------
    WorkspaceError
        If either name resolves outside ``generators_dir``, the new
        name is not a single directory name, the source directory does
        not exist, the target name is already taken, or the rename
        fails.

    """
    source = resolve_generator_dir(generators_dir, name)

    if new_name != Path(new_name).name:
        msg = 'Generator name must be a single directory name'
        raise WorkspaceError(msg, context={'name': new_name})

    destination = resolve_generator_dir(generators_dir, new_name)

    if not source.is_dir():
        msg = 'Generator directory does not exist'
        raise WorkspaceError(msg, context={'name': name})

    if destination.exists():
        msg = 'Generator directory already exists'
        raise WorkspaceError(msg, context={'name': new_name})

    try:
        source.rename(destination)
    except OSError as e:
        msg = 'Failed to rename directory'
        raise WorkspaceError(
            msg,
            context={'reason': str(e), 'path': str(source)},
        ) from None

    return destination


def find_secret_references(
    generators_dir: Path,
    config_filename: Path,
    secret: str,
) -> list[str]:
    """List generator directories whose config references a secret.

    Only generator configurations are scanned, since `${secrets.*}`
    tokens are substituted in them alone. Configurations that cannot
    be read are skipped - such a generator cannot run either.

    Parameters
    ----------
    generators_dir : Path
        Root directory that contains generator subdirectories.
    config_filename : Path
        Name of the configuration file inside a generator directory.
    secret : str
        Name of the secret to look for.

    Returns
    -------
    list[str]
        Sorted names of generator directories referencing the secret.

    """
    if not generators_dir.exists():
        return []

    names: list[str] = []

    for config_path in generators_dir.glob(f'*/{config_filename}'):
        try:
            content = config_path.read_text(encoding='utf-8')
        except OSError, UnicodeDecodeError:
            continue

        if secret in extract_secrets(content):
            names.append(config_path.parent.name)

    return sorted(names)
