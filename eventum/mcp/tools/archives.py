"""Project archive tools.

Packs a generator directory into a ZIP archive and unpacks one back
into the generators directory. Packing and path safety go through
``eventum.app.archiving`` and ``eventum.app.workspace``; this module
contains no archive logic.

Archive bytes travel inline in the tool payload and land in the
agent's context. A client able to make HTTP requests and write files
is better served by the REST API, which moves the same archive as a
file; an archive above the inline limit has no other route and is
refused - the fallback the server instructions describe.
"""

import base64
import binascii
import io
import shutil
import tempfile
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from eventum.app import workspace
from eventum.app.archiving import (
    ArchiveError,
    pack_project,
    unpack_project,
)
from eventum.app.workspace import WorkspaceError
from eventum.mcp.context import AuthoringContext
from eventum.mcp.errors import (
    ToolFailure,
    read_only_failure,
    scrub_message,
    to_tool_error,
)
from eventum.mcp.observability import observe_failure

# Every generator published in the Eventum Hub packs well below this
# size - the largest of them into 91 KiB - so the limit only turns
# away projects carrying generated output or oversized samples.
MAX_INLINE_ARCHIVE_SIZE = 128 * 1024

_TRANSFER_HINT = (
    'Archive exceeds the inline transfer limit; transfer it through '
    'the REST API instead'
)


def _check_excluded(
    excluded: set[str],
    config_filename: str,
) -> ToolFailure | None:
    """Reject an exclusion list holding anything but top level names.

    Returns a ToolFailure to forward, or None when the list is valid.
    """
    for entry in excluded:
        if not entry or entry != Path(entry).name or entry in {'.', '..'}:
            return ToolFailure(
                error='Excluded entry must be a top level entry name',
                details={'value': entry},
            )

    if config_filename in excluded:
        return ToolFailure(
            error=(
                'Generator configuration cannot be excluded, since the '
                'archive would not be importable without it'
            ),
            details={'name': config_filename},
        )

    return None


def _resolve_existing_generator(
    context: AuthoringContext,
    name: str,
) -> Path | ToolFailure:
    """Resolve a generator directory that must already exist.

    Returns the resolved directory, or a ToolFailure to forward.
    """
    try:
        project_dir = workspace.resolve_generator_dir(
            context.generators_dir,
            name,
        )
    except WorkspaceError as e:
        return to_tool_error(e, context.generators_dir)

    if not (project_dir / context.config_filename).is_file():
        return ToolFailure(
            error='Generator directory not found',
            details={'name': name},
        )

    return project_dir


def _pack_inline(
    context: AuthoringContext,
    name: str,
    project_dir: Path,
    excluded: set[str],
) -> dict[str, Any] | ToolFailure:
    """Pack a project and return it base64 encoded.

    Returns the archive payload, or a ToolFailure to forward.
    """
    with tempfile.TemporaryDirectory() as staging:
        archive_path = Path(staging) / f'{name}.zip'

        try:
            pack_project(project_dir, archive_path, exclude=excluded)
            size = archive_path.stat().st_size

            if size > MAX_INLINE_ARCHIVE_SIZE:
                return _oversized_failure(name, size)

            content = archive_path.read_bytes()
        except ArchiveError as e:
            return to_tool_error(e, context.generators_dir)
        except OSError as e:
            return _os_error_failure(
                'Failed to pack generator', context, name, e
            )

    return {
        'filename': f'{name}.zip',
        'size_in_bytes': size,
        'content_base64': base64.b64encode(content).decode('ascii'),
    }


def _oversized_failure(name: str, size: int) -> ToolFailure:
    """Failure for an archive over the inline transfer limit."""
    return ToolFailure(
        error=_TRANSFER_HINT,
        details={
            'name': name,
            'size': size,
            'limit': MAX_INLINE_ARCHIVE_SIZE,
        },
    )


def _os_error_failure(
    message: str,
    context: AuthoringContext,
    name: str,
    error: OSError,
) -> ToolFailure:
    """Failure for an OS error, with the reason stripped of paths."""
    return ToolFailure(
        error=message,
        details={
            'name': name,
            'reason': scrub_message(str(error), context.generators_dir),
        },
    )


def export_generator(
    context: AuthoringContext,
    name: str,
    exclude: list[str] | None = None,
) -> dict[str, Any] | ToolFailure:
    """Pack a generator directory into a base64 encoded ZIP archive.

    Parameters
    ----------
    context : AuthoringContext
        Authoring context supplying the generators directory and the
        config filename.

    name : str
        Generator directory name.

    exclude : list[str] | None, default None
        Names of top level entries to leave out of the archive, with
        everything under them.

    Returns
    -------
    dict[str, Any]
        ``{'filename': ..., 'size_in_bytes': ..., 'content_base64':
        ...}`` on success.

    ToolFailure
        If the name escapes the generators root, the generator does
        not exist, an excluded entry is not a top level name, the
        archive exceeds the inline transfer limit, or the directory
        cannot be read. Never raises; does not leak absolute paths.

    """
    project_dir = _resolve_existing_generator(context, name)

    if isinstance(project_dir, ToolFailure):
        return project_dir

    excluded = set(exclude or [])
    excluded_failure = _check_excluded(excluded, context.config_filename)

    if excluded_failure is not None:
        return excluded_failure

    return _pack_inline(context, name, project_dir, excluded)


def _resolve_new_generator(
    context: AuthoringContext,
    name: str,
) -> Path | ToolFailure:
    """Resolve a generator directory that must not exist yet.

    Returns the resolved directory, or a ToolFailure to forward.
    """
    if name != Path(name).name or name in {'', '.', '..'}:
        return ToolFailure(
            error='Generator name must be a single directory name',
            details={'name': name},
        )

    try:
        destination = workspace.resolve_generator_dir(
            context.generators_dir,
            name,
        )
    except WorkspaceError as e:
        return to_tool_error(e, context.generators_dir)

    if destination.exists():
        return ToolFailure(
            error='Generator directory already exists',
            details={'name': name},
        )

    return destination


def _decode_inline(name: str, content_base64: str) -> bytes | ToolFailure:
    """Decode base64 archive content within the inline limit.

    Returns the decoded bytes, or a ToolFailure to forward.
    """
    try:
        content = base64.b64decode(content_base64, validate=True)
    except binascii.Error, ValueError:
        return ToolFailure(
            error='Content is not valid base64',
            details={'name': name},
        )

    if len(content) > MAX_INLINE_ARCHIVE_SIZE:
        return _oversized_failure(name, len(content))

    return content


def import_generator(
    context: AuthoringContext,
    name: str,
    content_base64: str,
) -> dict[str, Any] | ToolFailure:
    """Unpack a base64 encoded ZIP archive into a new generator.

    Gated on ``context.read_only``: if the server is read-only the
    call fails immediately without touching the filesystem.

    Parameters
    ----------
    context : AuthoringContext
        Authoring context supplying the generators directory, the
        config filename and the read-only flag.

    name : str
        Name of the generator directory to create.

    content_base64 : str
        Base64 encoded ZIP archive holding a generator configuration.

    Returns
    -------
    dict[str, Any]
        ``{'imported': name, 'files': <number of files>}`` on success.

    ToolFailure
        If the server is read-only, the name is not a single directory
        name or escapes the generators root, the generator already
        exists, the content is not valid base64, the archive exceeds
        the inline transfer limit, or the archive holds no generator
        configuration. Never raises; does not leak absolute paths.

    """
    if context.read_only:
        return read_only_failure({'name': name})

    destination = _resolve_new_generator(context, name)

    if isinstance(destination, ToolFailure):
        return destination

    content = _decode_inline(name, content_base64)

    if isinstance(content, ToolFailure):
        return content

    return _unpack_into_generators_dir(context, name, content, destination)


def _unpack_into_generators_dir(
    context: AuthoringContext,
    name: str,
    content: bytes,
    destination: Path,
) -> dict[str, Any] | ToolFailure:
    """Unpack archive content into a new generator directory.

    The project is unpacked one level below a staging directory, so
    that a directory holding a generator configuration appears
    directly inside the generators directory - and thus in the list of
    generators - only once the import is complete.
    """
    try:
        context.generators_dir.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(dir=context.generators_dir))
    except OSError as e:
        return _os_error_failure(
            'Failed to import generator',
            context,
            name,
            e,
        )

    unpacked = staging / 'project'

    try:
        written = unpack_project(
            io.BytesIO(content),
            unpacked,
            context.config_filename,
        )
        unpacked.rename(destination)
    except ArchiveError as e:
        return to_tool_error(e, context.generators_dir)
    except OSError as e:
        return _os_error_failure(
            'Failed to import generator',
            context,
            name,
            e,
        )
    finally:
        shutil.rmtree(staging, ignore_errors=True)

    return {'imported': name, 'files': written}


def register(
    mcp: FastMCP,
    context: AuthoringContext,
    *,
    transport: str,
) -> None:
    """Register project archive tools on the server."""

    @mcp.tool(name='export_generator')
    def _export_generator_tool(
        name: str,
        exclude: list[str] | None = None,
    ) -> dict[str, Any] | ToolFailure:
        """Export a generator directory as a ZIP archive.

        The archive holds the whole generator directory - the
        configuration, templates, samples and any generated output -
        without a wrapping directory, and is returned base64 encoded
        in ``content_base64``.

        Archive content is carried in the result and lands in the
        conversation. If this client can make HTTP requests and write
        files, take the archive from the REST API instead - ``GET
        /api/generator-configs/{name}/export`` returns the same file
        and leaves the conversation free of it. For the same reason an
        archive over 128 KiB is refused and the REST API is the only
        route left. Passing the directories that hold generated output
        in ``exclude`` usually brings a project back under the limit.

        Parameters
        ----------
        name : str
            Generator directory name, as returned by
            ``list_generators``.

        exclude : list[str] | None, default None
            Names of top level entries to leave out of the archive,
            with everything under them (e.g. ``['output']``). The
            generator configuration cannot be excluded.

        Returns
        -------
        dict[str, Any] | ToolFailure
            ``filename``, ``size_in_bytes`` and ``content_base64`` of
            the archive, or a structured failure. Does not raise.

        """
        return observe_failure(
            export_generator(context, name, exclude),
            mcp_tool='export_generator',
            mcp_transport=transport,
        )

    @mcp.tool(name='import_generator')
    def _import_generator_tool(
        name: str,
        content_base64: str,
    ) -> dict[str, Any] | ToolFailure:
        """Import a generator directory from a ZIP archive.

        The archive must hold a generator configuration file; the
        directory holding it becomes the root of the imported
        generator, so an archive that wraps the project in one or more
        directories imports the same way as one holding it at the top
        level. An existing generator is never overwritten.

        Archive content is carried in the call and lands in the
        conversation. If this client can make HTTP requests, upload the
        archive to the REST API instead - ``POST
        /api/generator-configs/{name}/import`` takes the same file. For
        the same reason an archive over 128 KiB is refused and the REST
        API is the only route left.

        Parameters
        ----------
        name : str
            Name of the generator directory to create.

        content_base64 : str
            Base64 encoded ZIP archive.

        Returns
        -------
        dict[str, Any] | ToolFailure
            ``imported`` name and the number of extracted ``files``,
            or a structured failure. Does not raise.

        """
        return observe_failure(
            import_generator(context, name, content_base64),
            mcp_tool='import_generator',
            mcp_transport=transport,
        )
