"""Installing a published generator into the workspace."""

import errno
import shutil
import stat
import tempfile
import zipfile
from collections.abc import Iterator
from pathlib import Path, PurePosixPath
from typing import cast

from dulwich.object_store import BaseObjectStore
from dulwich.objects import Blob, ObjectID, Tree

from eventum.app.archiving import (
    MAX_ARCHIVE_ENTRIES,
    MAX_UNPACKED_SIZE,
    ArchiveContentError,
    ArchiveError,
    unpack_project,
)
from eventum.app.repositories.catalog import (
    open_repository,
    resolve_entry_tree,
    walk_tree,
)
from eventum.app.repositories.exceptions import (
    InstallConflictError,
    InstallContentError,
    InstallError,
    InstallNameError,
)
from eventum.app.repositories.models import GeneratorSource
from eventum.app.repositories.source import write_source
from eventum.app.workspace import WorkspaceError, resolve_generator_dir

_ARCHIVE_FILENAME = 'source.zip'
_UNPACKED_DIRNAME = 'project'


def install_entry(  # noqa: PLR0913 - a source, a target and a name
    *,
    repo_path: Path,
    revision: str,
    entry: str,
    generators_dir: Path,
    project_name: str,
    config_filename: str,
    source: GeneratorSource,
) -> int:
    """Install a published generator as a project of the workspace.

    The generator is packed out of the fetched repository and unpacked
    through the path an imported project takes, so what a repository
    publishes lands under the same guards, limits and staging as what
    a user uploads. Only regular files are packed: a symbolic link or
    a submodule the repository carries is left behind rather than
    resolved against the host.

    Parameters
    ----------
    repo_path : Path
        Directory of the bare repository the remote was fetched into.

    revision : str
        Hash of the fetched commit.

    entry : str
        Name of the published generator to install.

    generators_dir : Path
        Directory the projects of the workspace live in.

    project_name : str
        Name of the project directory to install into.

    config_filename : str
        Name of the generator configuration file.

    source : GeneratorSource
        Origin to write into the project, so that what it came from
        arrives with it rather than after it.

    Returns
    -------
    int
        Number of installed files.

    Raises
    ------
    CatalogError
        If the fetched repository cannot be read.

    CatalogEntryNotFoundError
        If the repository publishes no such generator.

    InstallNameError
        If the project name cannot name a project directory.

    InstallConflictError
        If a project with the requested name already exists.

    InstallContentError
        If the published generator holds no installable project or
        exceeds the size limits.

    InstallError
        If the workspace cannot be written.

    """
    destination = _resolve_destination(generators_dir, project_name)

    with open_repository(repo_path) as repo:
        tree = resolve_entry_tree(repo.object_store, revision, entry)

        try:
            generators_dir.mkdir(parents=True, exist_ok=True)
            staging = Path(tempfile.mkdtemp(dir=generators_dir))
        except OSError as e:
            msg = 'Failed to prepare the workspace for installation'
            raise InstallError(
                msg,
                context={'path': str(generators_dir), 'reason': str(e)},
            ) from None

        # The project is unpacked one level below the staging
        # directory, so that a directory holding a generator
        # configuration appears in the list of projects only once the
        # installation is complete.
        archive_path = staging / _ARCHIVE_FILENAME
        unpacked = staging / _UNPACKED_DIRNAME

        try:
            _pack_tree(repo.object_store, tree, archive_path)

            with archive_path.open('rb') as archive:
                installed = unpack_project(
                    archive,
                    unpacked,
                    config_filename,
                )

            # The origin is written before the project takes its
            # place, so that a project either appears complete or does
            # not appear at all.
            write_source(unpacked, source)
            unpacked.rename(destination)
        except ArchiveContentError as e:
            msg = 'Published generator cannot be installed'
            raise InstallContentError(
                msg,
                context={**e.context, 'reason': str(e)},
            ) from None
        except ArchiveError as e:
            msg = 'Failed to install published generator'
            raise InstallError(msg, context=e.context) from None
        except OSError as e:
            if e.errno in (errno.EEXIST, errno.ENOTEMPTY):
                msg = 'Project with the requested name already exists'
                raise InstallConflictError(
                    msg,
                    context={'name': project_name},
                ) from None

            msg = 'Failed to install published generator'
            raise InstallError(
                msg,
                context={'path': str(destination), 'reason': str(e)},
            ) from None
        finally:
            shutil.rmtree(staging, ignore_errors=True)

    return installed


def _resolve_destination(generators_dir: Path, project_name: str) -> Path:
    """Return the directory a project is installed into.

    Raises
    ------
    InstallConflictError
        If the directory already exists.

    InstallNameError
        If the name is not a single directory name inside the
        generators directory.

    """
    is_single_name = (
        project_name not in {'', '.', '..'}
        and project_name == Path(project_name).name
    )

    if not is_single_name:
        msg = 'Project name must be a single directory name'
        raise InstallNameError(msg, context={'name': project_name})

    try:
        destination = resolve_generator_dir(generators_dir, project_name)
    except WorkspaceError as e:
        msg = 'Project name is not allowed'
        raise InstallNameError(msg, context=e.context) from None

    if destination.exists():
        msg = 'Project with the requested name already exists'
        raise InstallConflictError(msg, context={'name': project_name})

    return destination


def _pack_tree(
    store: BaseObjectStore,
    tree: Tree,
    archive_path: Path,
) -> None:
    """Pack the regular files of a tree into a ZIP archive.

    Raises
    ------
    InstallContentError
        If the tree holds more entries or more content than a project
        may carry.

    InstallError
        If the archive cannot be written.

    """
    written_count = 0
    written_size = 0

    try:
        with zipfile.ZipFile(
            archive_path,
            mode='w',
            compression=zipfile.ZIP_DEFLATED,
        ) as archive:
            for path, sha in _iter_files(store, tree):
                blob = cast('Blob', store[sha])

                written_count += 1
                written_size += blob.raw_length()

                if written_count > MAX_ARCHIVE_ENTRIES:
                    msg = 'Published generator holds too many files'
                    raise InstallContentError(
                        msg,
                        context={
                            'count': written_count,
                            'limit': MAX_ARCHIVE_ENTRIES,
                        },
                    )

                if written_size > MAX_UNPACKED_SIZE:
                    msg = 'Published generator is larger than the size limit'
                    raise InstallContentError(
                        msg,
                        context={
                            'size': written_size,
                            'limit': MAX_UNPACKED_SIZE,
                        },
                    )

                with archive.open(str(path), 'w') as target:
                    for chunk in blob.chunked:
                        target.write(chunk)
    except OSError as e:
        msg = 'Failed to pack published generator'
        raise InstallError(
            msg,
            context={'file_path': str(archive_path), 'reason': str(e)},
        ) from None


def _iter_files(
    store: BaseObjectStore,
    tree: Tree,
) -> Iterator[tuple[PurePosixPath, ObjectID]]:
    """Yield the regular files of a tree with their relative paths.

    Raises
    ------
    CatalogError
        If the tree is deeper or holds more entries than a published
        generator may, or refers to an object the repository does not
        hold.

    """
    for path, entry in walk_tree(store, tree):
        if stat.S_ISREG(entry.mode):
            yield path, ObjectID(entry.sha)
