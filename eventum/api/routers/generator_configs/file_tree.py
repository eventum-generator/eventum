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

    children : list[FileNode] | None
        Nested file nodes if this node is a directory. `None` if this
        node is a file.

    """

    name: str
    is_dir: bool
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
    return FileNode(name=path.name, is_dir=False)
