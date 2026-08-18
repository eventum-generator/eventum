"""Transport-neutral packing and unpacking of generator projects.

A project travels between instances as a single ZIP archive: Studio
exports one for download and imports one back, and the MCP tools carry
the same archives. The archive layout, the guards that make an
uploaded archive safe to extract, and the limits live here, so every
driver adapter behaves the same.
"""

import stat
import zipfile
from collections.abc import Collection, Iterable
from pathlib import Path
from typing import IO

from eventum.exceptions import ContextualError

# An archive is inspected before anything about its origin is known,
# so both the number of entries and the unpacked size are capped: a
# small archive of highly compressible data expands into an
# arbitrarily large directory.
MAX_ARCHIVE_ENTRIES = 10_000
MAX_UNPACKED_SIZE = 512 * 1024 * 1024

_EXTRACT_CHUNK_SIZE = 64 * 1024


class ArchiveError(ContextualError):
    """Project archive cannot be packed or unpacked."""


class ArchiveContentError(ArchiveError):
    """Archive does not hold a project that can be extracted."""


def pack_project(
    project_dir: Path,
    destination: Path,
    *,
    exclude: Collection[str] = (),
) -> None:
    """Pack a project directory into a ZIP archive.

    Entries are stored relative to `project_dir`, so the archive holds
    the project without a wrapping directory.

    Symbolic links are left out. A link is stored as the content of
    the file it points at, so one pointing outside the project would
    put a copy of that file into the archive.

    Parameters
    ----------
    project_dir : Path
        Directory to pack.

    destination : Path
        Path of the archive to write. An existing file is replaced.

    exclude : Collection[str], default ()
        Names of top level entries to leave out, with everything under
        them.

    Raises
    ------
    ArchiveError
        If the project directory does not exist, cannot be read, or
        the archive cannot be written.

    """
    if not project_dir.is_dir():
        msg = 'Project directory does not exist'
        raise ArchiveError(msg, context={'path': str(project_dir)})

    excluded = frozenset(exclude)

    try:
        with zipfile.ZipFile(
            destination,
            mode='w',
            compression=zipfile.ZIP_DEFLATED,
        ) as archive:
            for path in sorted(project_dir.rglob('*')):
                relative = path.relative_to(project_dir)

                if relative.parts[0] in excluded or path.is_symlink():
                    continue

                if path.is_dir() or path.is_file():
                    archive.write(path, arcname=relative)
    except OSError as e:
        msg = 'Failed to pack project'
        raise ArchiveError(
            msg,
            context={'reason': str(e), 'path': str(project_dir)},
        ) from None


def unpack_project(
    archive: IO[bytes],
    destination: Path,
    config_filename: str,
) -> int:
    """Unpack a project from a ZIP archive into a directory.

    The project root inside the archive is found by the generator
    configuration file: the shallowest entry named `config_filename`
    marks it, and only entries under it are extracted. An archive
    holding the project in a nested directory - as produced by
    downloading a directory from a repository - therefore unpacks the
    same way as one holding it at the top level.

    Everything that is not a regular file or a directory is rejected,
    as are entries pointing outside the destination, so an archive
    from an untrusted source cannot write anywhere else.

    Parameters
    ----------
    archive : IO[bytes]
        Opened archive to read. Must be seekable.

    destination : Path
        Directory to extract the project into. Created if missing;
        left in a partial state if extraction fails.

    config_filename : str
        Name of the generator configuration file that marks the
        project root.

    Returns
    -------
    int
        Number of extracted files.

    Raises
    ------
    ArchiveContentError
        If the archive is not a readable ZIP file, holds no or more
        than one generator configuration, carries an unsafe entry, or
        exceeds the entry count or unpacked size limits.

    ArchiveError
        If the destination cannot be written.

    """
    try:
        with zipfile.ZipFile(archive) as zip_file:
            entries = zip_file.infolist()
            _validate_entries(entries)

            root = _find_project_root(entries, config_filename)

            return _extract_entries(zip_file, entries, root, destination)
    except zipfile.BadZipFile:
        msg = 'File is not a readable ZIP archive'
        raise ArchiveContentError(msg, context={}) from None
    except OSError as e:
        msg = 'Failed to unpack project'
        raise ArchiveError(
            msg,
            context={'reason': str(e), 'path': str(destination)},
        ) from None


def _validate_entries(entries: list[zipfile.ZipInfo]) -> None:
    """Reject an entry list that is unsafe or over the limits.

    Raises
    ------
    ArchiveContentError
        If the archive holds too many entries, unpacks to more than
        the size limit, or carries an entry that is not a regular file
        or a directory.

    """
    if len(entries) > MAX_ARCHIVE_ENTRIES:
        msg = 'Archive holds too many entries'
        raise ArchiveContentError(
            msg,
            context={'count': len(entries), 'limit': MAX_ARCHIVE_ENTRIES},
        )

    unpacked_size = sum(entry.file_size for entry in entries)

    if unpacked_size > MAX_UNPACKED_SIZE:
        msg = 'Archive unpacks to more than the size limit'
        raise ArchiveContentError(
            msg,
            context={'size': unpacked_size, 'limit': MAX_UNPACKED_SIZE},
        )

    for entry in entries:
        # The type bits are absent in an archive written without unix
        # metadata, and every such entry is a plain file or directory.
        mode = entry.external_attr >> 16

        if stat.S_IFMT(mode) and not (
            stat.S_ISREG(mode) or stat.S_ISDIR(mode)
        ):
            msg = 'Archive holds an entry that is not a file or directory'
            raise ArchiveContentError(
                msg,
                context={'file_path': entry.filename},
            )


def _entry_path(filename: str) -> Path:
    """Return an archive entry name as a safe relative path.

    Raises
    ------
    ArchiveContentError
        If the name is absolute or traverses out of the archive root.

    """
    path = Path(filename)

    if path.is_absolute() or any(part == '..' for part in path.parts):
        msg = 'Archive holds an entry pointing outside of it'
        raise ArchiveContentError(msg, context={'file_path': filename})

    return path


def _find_project_root(
    entries: Iterable[zipfile.ZipInfo],
    config_filename: str,
) -> Path:
    """Return the path of the project root inside the archive.

    Raises
    ------
    ArchiveContentError
        If no entry or more than one entry at the same depth is named
        `config_filename`.

    """
    configs = [
        path
        for path in (
            _entry_path(entry.filename)
            for entry in entries
            if not entry.is_dir()
        )
        if path.name == config_filename
    ]

    if not configs:
        msg = 'Archive holds no generator configuration'
        raise ArchiveContentError(
            msg,
            context={'file_path': config_filename},
        )

    depth = min(len(path.parts) for path in configs)
    shallowest = [path for path in configs if len(path.parts) == depth]

    if len(shallowest) > 1:
        msg = 'Archive holds more than one generator configuration'
        raise ArchiveContentError(
            msg,
            context={'count': len(shallowest)},
        )

    return shallowest[0].parent


def _extract_entries(
    zip_file: zipfile.ZipFile,
    entries: Iterable[zipfile.ZipInfo],
    root: Path,
    destination: Path,
) -> int:
    """Extract entries under `root` into `destination`.

    Returns
    -------
    int
        Number of extracted files.

    Raises
    ------
    ArchiveContentError
        If an entry escapes the destination, or the written content
        exceeds the unpacked size limit. The declared size of an entry
        is what `_validate_entries` checks, and an archive is free to
        understate it, so the bytes are counted as they are written.

    OSError
        If the destination cannot be written.

    """
    destination.mkdir(parents=True, exist_ok=True)
    resolved_destination = destination.resolve()

    written_size = 0
    written_files = 0

    for entry in entries:
        path = _entry_path(entry.filename)

        if path == root or not path.is_relative_to(root):
            continue

        target = (destination / path.relative_to(root)).resolve()

        if not target.is_relative_to(resolved_destination):
            msg = 'Archive holds an entry pointing outside of it'
            raise ArchiveContentError(
                msg,
                context={'file_path': entry.filename},
            )

        if entry.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue

        target.parent.mkdir(parents=True, exist_ok=True)

        with zip_file.open(entry) as source, target.open('wb') as f:
            while chunk := source.read(_EXTRACT_CHUNK_SIZE):
                written_size += len(chunk)

                if written_size > MAX_UNPACKED_SIZE:
                    msg = 'Archive unpacks to more than the size limit'
                    raise ArchiveContentError(
                        msg,
                        context={
                            'size': written_size,
                            'limit': MAX_UNPACKED_SIZE,
                        },
                    )

                f.write(chunk)

        written_files += 1

    return written_files
