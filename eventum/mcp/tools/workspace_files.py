"""Workspace file tools.

Lists generators and their files, and reads/writes individual files
inside a generator directory. All path safety and IO go through
``eventum.app.workspace``; this module contains no path logic.

The generator config filename comes from the context
(``generator.yml`` by default), so generators detected here match
the ones the composition root's transport serves.
"""

from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from eventum.app import workspace
from eventum.app.workspace import WorkspaceError
from eventum.mcp.context import AuthoringContext
from eventum.mcp.errors import (
    ToolFailure,
    read_only_failure,
    to_tool_error,
)
from eventum.mcp.observability import observe_failure

_ALLOWED_EXTENSIONS = frozenset({'.yml', '.yaml', '.jinja', '.csv', '.json'})


def _check_extension(rel: Path, relative_path: str) -> ToolFailure | None:
    """Reject a path whose suffix is not in the allow-list.

    Returns a ToolFailure to forward, or None when the extension is
    allowed.
    """
    if rel.suffix not in _ALLOWED_EXTENSIONS:
        return ToolFailure(
            error='File extension not allowed',
            details={'file_path': relative_path},
        )
    return None


def list_generators(context: AuthoringContext) -> list[str]:
    """Return sorted names of generator directories.

    A directory qualifies when it contains the context's config
    filename directly inside it (one level deep).

    Parameters
    ----------
    context : AuthoringContext
        Authoring context supplying the generators directory and the
        config filename.

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
        p.parent.name
        for p in generators_dir.glob(f'*/{context.config_filename}')
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

    extension_failure = _check_extension(rel, relative_path)
    if extension_failure is not None:
        return extension_failure

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
        return read_only_failure({'file_path': relative_path})

    rel = Path(relative_path)

    try:
        path = workspace.resolve_generator_file(
            context.generators_dir, name, rel
        )
    except WorkspaceError as e:
        return to_tool_error(e, context.generators_dir)

    extension_failure = _check_extension(rel, relative_path)
    if extension_failure is not None:
        return extension_failure

    try:
        workspace.write_text(path, content)
    except WorkspaceError as e:
        return to_tool_error(e, context.generators_dir)

    return {'written': relative_path}


def delete_generator_file(
    context: AuthoringContext,
    name: str,
    relative_path: str,
) -> dict[str, Any] | ToolFailure:
    """Delete a file in a generator directory.

    Gated on ``context.read_only``: if the server is read-only the call
    fails immediately without touching the filesystem.

    Parameters
    ----------
    context : AuthoringContext
        Authoring context supplying the generators directory and the
        read-only flag.

    name : str
        Generator directory name.

    relative_path : str
        Path to the file relative to the generator directory.

    Returns
    -------
    dict[str, Any]
        ``{'deleted': relative_path}`` on success.

    ToolFailure
        If the server is read-only, the path escapes the generator
        directory, the extension is not in the allow-list, or the file
        does not exist. Never raises; does not leak absolute paths.

    """
    if context.read_only:
        return read_only_failure({'file_path': relative_path})

    rel = Path(relative_path)

    try:
        path = workspace.resolve_generator_file(
            context.generators_dir, name, rel
        )
    except WorkspaceError as e:
        return to_tool_error(e, context.generators_dir)

    extension_failure = _check_extension(rel, relative_path)
    if extension_failure is not None:
        return extension_failure

    if not path.is_file():
        return ToolFailure(
            error='File not found',
            details={'file_path': relative_path},
        )

    try:
        workspace.delete_file(path)
    except WorkspaceError as e:
        return to_tool_error(e, context.generators_dir)

    return {'deleted': relative_path}


def delete_generator(
    context: AuthoringContext,
    name: str,
) -> dict[str, Any] | ToolFailure:
    """Delete a whole generator directory and its files.

    Gated on ``context.read_only``. Only a direct child of the
    generators directory may be removed - nested paths and the
    generators directory itself are rejected.

    Parameters
    ----------
    context : AuthoringContext
        Authoring context supplying the generators directory and the
        read-only flag.

    name : str
        Generator directory name.

    Returns
    -------
    dict[str, Any]
        ``{'deleted': name}`` on success.

    ToolFailure
        If the server is read-only, the name escapes or is not a direct
        child of the generators directory, or the directory does not
        exist. Never raises; does not leak absolute paths.

    """
    if context.read_only:
        return read_only_failure({'name': name})

    try:
        path = workspace.resolve_generator_dir(context.generators_dir, name)
    except WorkspaceError as e:
        return to_tool_error(e, context.generators_dir)

    base = context.generators_dir.resolve()
    if path.parent != base:
        return ToolFailure(
            error='Only a direct child generator may be deleted',
            details={'name': name},
        )

    if not path.is_dir():
        return ToolFailure(
            error='Generator directory not found',
            details={'name': name},
        )

    try:
        workspace.delete_dir(path)
    except WorkspaceError as e:
        return to_tool_error(e, context.generators_dir)

    return {'deleted': name}


def register(
    mcp: FastMCP,
    context: AuthoringContext,
    *,
    transport: str,
) -> None:
    """Register workspace-file tools on the server."""

    @mcp.tool(name='list_generators')
    def _list_generators_tool() -> list[str]:
        """List generator directory names in the generators directory.

        Returns
        -------
        list[str]
            Sorted list of generator names (immediate subdirectories
            containing a generator config file, ``generator.yml`` by
            default). Empty if the generators directory does not
            exist.

        """
        return observe_failure(
            list_generators(context),
            mcp_tool='list_generators',
            mcp_transport=transport,
        )

    @mcp.tool(name='list_generator_files')
    def _list_generator_files_tool(
        name: str,
    ) -> list[str] | ToolFailure:
        """List files in a generator directory.

        Only files with allowed extensions (``.yml``, ``.yaml``,
        ``.jinja``, ``.csv``, ``.json``) are included.

        Parameters
        ----------
        name : str
            Generator directory name, as returned by
            ``list_generators``.

        Returns
        -------
        list[str] | ToolFailure
            Sorted POSIX-relative paths inside the generator directory,
            or a structured failure if the name is invalid or the
            directory does not exist. Does not raise.

        """
        return observe_failure(
            list_generator_files(context, name),
            mcp_tool='list_generator_files',
            mcp_transport=transport,
        )

    @mcp.tool(name='read_generator_file')
    def _read_generator_file_tool(
        name: str,
        relative_path: str,
    ) -> str | ToolFailure:
        """Return the text content of a file in a generator directory.

        Parameters
        ----------
        name : str
            Generator directory name.

        relative_path : str
            Path to the file relative to the generator directory
            (e.g. ``'templates/event.jinja'``).

        Returns
        -------
        str | ToolFailure
            File contents, or a structured failure if the path is
            invalid, the extension is not allowed, or the file does not
            exist. Does not raise.

        """
        return observe_failure(
            read_generator_file(context, name, relative_path),
            mcp_tool='read_generator_file',
            mcp_transport=transport,
        )

    @mcp.tool(name='write_generator_file')
    def _write_generator_file_tool(
        name: str,
        relative_path: str,
        content: str,
    ) -> dict[str, Any] | ToolFailure:
        """Write text content to a file in a generator directory.

        Creates parent directories as needed. Fails immediately when
        the server is read-only without touching the filesystem. Name
        the config file ``generator.yml`` unless this server is
        configured with another config filename - validate, preview,
        and run load that filename.

        Parameters
        ----------
        name : str
            Generator directory name.

        relative_path : str
            Path to the file relative to the generator directory
            (e.g. ``'templates/event.jinja'``).

        content : str
            Text to write.

        Returns
        -------
        dict[str, Any] | ToolFailure
            ``{'written': relative_path}`` on success, or a structured
            failure if the server is read-only, the path is invalid, the
            extension is not allowed, or the write fails. Does not raise.

        """
        return observe_failure(
            write_generator_file(context, name, relative_path, content),
            mcp_tool='write_generator_file',
            mcp_transport=transport,
        )

    @mcp.tool(name='delete_generator_file')
    def _delete_generator_file_tool(
        name: str,
        relative_path: str,
    ) -> dict[str, Any] | ToolFailure:
        """Delete a file in a generator directory.

        Fails immediately when the server is read-only without touching
        the filesystem.

        Parameters
        ----------
        name : str
            Generator directory name.

        relative_path : str
            Path to the file relative to the generator directory
            (e.g. ``'templates/event.jinja'``).

        Returns
        -------
        dict[str, Any] | ToolFailure
            ``{'deleted': relative_path}`` on success, or a structured
            failure if the server is read-only, the path is invalid, the
            extension is not allowed, or the file does not exist. Does
            not raise.

        """
        return observe_failure(
            delete_generator_file(context, name, relative_path),
            mcp_tool='delete_generator_file',
            mcp_transport=transport,
        )

    @mcp.tool(name='delete_generator')
    def _delete_generator_tool(
        name: str,
    ) -> dict[str, Any] | ToolFailure:
        """Delete a whole generator directory and its files.

        Fails immediately when the server is read-only. Over HTTP,
        unregister the generator first - it remains in startup
        otherwise.

        Parameters
        ----------
        name : str
            Generator directory name, as returned by
            ``list_generators``.

        Returns
        -------
        dict[str, Any] | ToolFailure
            ``{'deleted': name}`` on success, or a structured failure if
            the server is read-only, the name is invalid, or the
            directory does not exist. Does not raise.

        """
        return observe_failure(
            delete_generator(context, name),
            mcp_tool='delete_generator',
            mcp_transport=transport,
        )
