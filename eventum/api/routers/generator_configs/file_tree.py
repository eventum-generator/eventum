"""Builder of file tree."""

from pathlib import Path

from pydantic import BaseModel


class FileNode(BaseModel, frozen=True, extra='forbid'):
    """Representation of a file or directory in a file tree.

    Used as a recursive structure to describe the contents of a
    generator directory for API responses.

    Attributes
    ----------
    name : str
        The base name of the file or directory.

    is_dir : bool
        Whether this node represents a directory or a file.

    size_in_bytes : int | None
        Size of the file in bytes. `None` for directories and for files
        whose size cannot be read.

    children : list[FileNode] | None
        Nested file nodes if this node is a directory. `None` if this
        node is a file.

    """

    name: str
    is_dir: bool
    size_in_bytes: int | None = None  # only for files
    children: list[FileNode] | None = None  # only for directories


def build_file_tree(path: Path) -> FileNode:
    """Recursively build a file tree representation for a given path.

    Parameters
    ----------
    path : Path
        Path to a file or directory.

    Returns
    -------
    FileNode
        Root node of the tree.

    Raises
    ------
    OSError
        If an OS error occurs while accessing directories, such as
        insufficient permissions or inaccessible paths.

    """
    if path.is_dir():
        return FileNode(
            name=path.name,
            is_dir=True,
            children=[build_file_tree(child) for child in path.iterdir()],
        )

    return FileNode(
        name=path.name,
        is_dir=False,
        size_in_bytes=_get_file_size(path),
    )


def _get_file_size(path: Path) -> int | None:
    """Get file size in bytes, or `None` if it cannot be read.

    Size of a file that cannot be stat'ed - a broken symlink, for
    example - is reported as unknown, so that a single such entry does
    not fail the whole tree.
    """
    try:
        return path.stat().st_size
    except OSError:
        return None
