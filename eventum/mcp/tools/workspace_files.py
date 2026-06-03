"""Workspace file tools.

Lists generators and their files, and reads/writes individual files
inside a generator directory. All path safety and IO go through
``eventum.app.workspace``; this module contains no path logic.

Assumption: the generator config filename is ``generator.yml``. This
matches the default setting value. The stdio composition root uses the
default, so the constant is correct for the MCP transport.
"""

from pathlib import Path
from typing import Any

from eventum.app import workspace
from eventum.app.workspace import WorkspaceError
from eventum.mcp.context import AuthoringContext
from eventum.mcp.errors import ToolFailure, to_tool_error

_CONFIG_FILENAME = 'generator.yml'
_ALLOWED_EXTENSIONS = frozenset({'.yml', '.yaml', '.jinja', '.csv', '.json'})


def list_generators(context: AuthoringContext) -> list[str]:
    """Return sorted names of generator directories.

    A directory qualifies when it contains ``generator.yml`` directly
    inside it (one level deep).

    Parameters
    ----------
    context : AuthoringContext
        Authoring context supplying the generators directory.

    Returns
    -------
    list[str]
        Sorted list of generator directory names. Empty if the
        generators directory does not exist.

    """
    generators_dir = context.generators_dir

    if not generators_dir.exists():
        return []

    names = [
        p.parent.name for p in generators_dir.glob(f'*/{_CONFIG_FILENAME}')
    ]

    return sorted(names)


def list_generator_files(
    context: AuthoringContext,
    name: str,
) -> list[str] | ToolFailure:
    """Return allowed-extension files inside a generator directory.

    Parameters
    ----------
    context : AuthoringContext
        Authoring context supplying the generators directory.

    name : str
        Generator directory name.

    Returns
    -------
    list[str]
        Sorted POSIX-relative paths of files whose suffix is in the
        allow-list.

    ToolFailure
        If the generator directory name escapes the generators root.
        Never raises; does not leak absolute paths.

    """
    try:
        base = workspace.resolve_generator_dir(context.generators_dir, name)
    except WorkspaceError as e:
        return to_tool_error(e, context.generators_dir)

    if not base.is_dir():
        return ToolFailure(
            error='Generator directory not found',
            details={'name': name},
        )

    paths = [
        str(p.relative_to(base).as_posix())
        for p in base.rglob('*')
        if p.is_file() and p.suffix in _ALLOWED_EXTENSIONS
    ]

    return sorted(paths)


def read_generator_file(
    context: AuthoringContext,
    name: str,
    relative_path: str,
) -> str | ToolFailure:
    """Return the text content of a file in a generator directory.

    Parameters
    ----------
    context : AuthoringContext
        Authoring context supplying the generators directory.

    name : str
        Generator directory name.

    relative_path : str
        Path to the file relative to the generator directory.

    Returns
    -------
    str
        File contents.

    ToolFailure
        If the path escapes the generator directory, the file does not
        exist, the extension is not in the allow-list, or the file
        cannot be read. Never raises; does not leak absolute paths.

    """
    rel = Path(relative_path)

    try:
        path = workspace.resolve_generator_file(
            context.generators_dir, name, rel
        )
    except WorkspaceError as e:
        return to_tool_error(e, context.generators_dir)

    if rel.suffix not in _ALLOWED_EXTENSIONS:
        return ToolFailure(
            error='File extension not allowed',
            details={'file_path': relative_path},
        )

    if not path.is_file():
        return ToolFailure(
            error='File not found',
            details={'file_path': relative_path},
        )

    try:
        return workspace.read_text(path)
    except WorkspaceError as e:
        return to_tool_error(e, context.generators_dir)


def write_generator_file(
    context: AuthoringContext,
    name: str,
    relative_path: str,
    content: str,
) -> dict[str, Any] | ToolFailure:
    """Write text content to a file in a generator directory.

    Creates parent directories as needed. Gated on ``context.read_only``:
    if the server is read-only the call fails immediately without
    touching the filesystem.

    Parameters
    ----------
    context : AuthoringContext
        Authoring context supplying the generators directory and the
        read-only flag.

    name : str
        Generator directory name.

    relative_path : str
        Path to the file relative to the generator directory.

    content : str
        Text to write.

    Returns
    -------
    dict[str, Any]
        ``{'written': relative_path}`` on success.

    ToolFailure
        If the server is read-only, the path escapes the generator
        directory, the extension is not in the allow-list, or the file
        cannot be written. Never raises; does not leak absolute paths.

    """
    if context.read_only:
        return ToolFailure(
            error='Server is read-only; writes are disabled',
            details={'relative_path': relative_path},
        )

    rel = Path(relative_path)

    try:
        path = workspace.resolve_generator_file(
            context.generators_dir, name, rel
        )
    except WorkspaceError as e:
        return to_tool_error(e, context.generators_dir)

    if rel.suffix not in _ALLOWED_EXTENSIONS:
        return ToolFailure(
            error='File extension not allowed',
            details={'file_path': relative_path},
        )

    try:
        workspace.write_text(path, content)
    except WorkspaceError as e:
        return to_tool_error(e, context.generators_dir)

    return {'written': relative_path}
