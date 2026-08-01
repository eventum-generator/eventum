"""Transport-neutral rename operations for projects and instances.

Renaming a project or an instance touches several places at once - the
generator directory on disk, the entries in the startup file, and the
generators held by the manager. Sequencing, guards, and rollback of a
partially applied rename live here, so every driver adapter gets the
same behaviour.
"""

from collections.abc import Iterator
from pathlib import Path

from eventum.app.manager import GeneratorManager, ManagingError
from eventum.app.startup import Startup, StartupError
from eventum.app.workspace import (
    WorkspaceError,
    rename_generator_dir,
    resolve_generator_dir,
)
from eventum.core.generator import Generator
from eventum.exceptions import ContextualError


class RenameError(ContextualError):
    """Rename cannot be performed."""


class RenameNotFoundError(RenameError):
    """Object to rename does not exist."""


class RenameConflictError(RenameError):
    """New name is already taken."""


class RenameBlockedError(RenameError):
    """Object cannot be renamed in its current state."""


def rename_project(
    *,
    manager: GeneratorManager,
    startup: Startup,
    generators_dir: Path,
    name: str,
    new_name: str,
) -> list[str]:
    """Rename a project directory and repoint instances that use it.

    Instances using the project are repointed at the new directory in
    the startup file and in the manager. All of them must be stopped,
    since a running generator reads its templates and samples from the
    directory while it works.

    Parameters
    ----------
    manager : GeneratorManager
        Manager holding the instances.

    startup : Startup
        Startup file service.

    generators_dir : Path
        Base directory that contains project directories.

    name : str
        Current name of the project.

    new_name : str
        Name to rename the project to.

    Returns
    -------
    list[str]
        Ids of instances that were repointed.

    Raises
    ------
    RenameNotFoundError
        If the project does not exist.

    RenameConflictError
        If the new name is already taken.

    RenameBlockedError
        If any instance using the project is active.

    RenameError
        If the new name is not allowed, or the rename fails midway.

    """
    project_dir = _resolve_dir(generators_dir, name)
    destination_dir = _resolve_dir(generators_dir, new_name)

    if not project_dir.is_dir():
        msg = 'Project does not exist'
        raise RenameNotFoundError(msg, context={'name': name})

    if destination_dir.exists():
        msg = 'Project with this name already exists'
        raise RenameConflictError(msg, context={'name': new_name})

    dependents = list(_iter_dependents(manager, generators_dir, name))
    active_ids = [
        generator.params.id
        for generator in dependents
        if _is_active(generator)
    ]

    if active_ids:
        msg = 'Instances using the project must be stopped before renaming'
        raise RenameBlockedError(
            msg,
            context={'name': name, 'generator_ids': active_ids},
        )

    try:
        rename_generator_dir(generators_dir, name, new_name)
    except WorkspaceError as e:
        raise RenameError(str(e), context=e.context) from None

    try:
        startup.rebase_generator_dir(name, new_name)
    except StartupError as e:
        _revert_dir_rename(generators_dir, name, new_name)
        raise RenameError(str(e), context=e.context) from None

    _repoint_dependents(manager, dependents, generators_dir, name, new_name)

    return [generator.params.id for generator in dependents]


def rename_instance(
    *,
    manager: GeneratorManager,
    startup: Startup,
    id: str,
    new_id: str,
) -> None:
    """Rename an instance in the manager and in the startup file.

    An instance may be defined in the startup file, held by the
    manager, or both; whichever holds it is updated. The instance must
    not be active, since renaming rebuilds it from its parameters.

    Parameters
    ----------
    manager : GeneratorManager
        Manager holding the instance.

    startup : Startup
        Startup file service.

    id : str
        Current id of the instance.

    new_id : str
        Id to rename the instance to.

    Raises
    ------
    RenameNotFoundError
        If the instance is neither defined nor managed.

    RenameConflictError
        If the new id is already taken.

    RenameBlockedError
        If the instance is active.

    RenameError
        If the startup file cannot be read or written, or the rename
        fails midway.

    """
    managed_ids = manager.generator_ids
    defined_ids = _list_defined_ids(startup)

    is_managed = id in managed_ids
    is_defined = id in defined_ids

    if not is_managed and not is_defined:
        msg = 'Instance does not exist'
        raise RenameNotFoundError(msg, context={'value': id})

    if new_id in managed_ids or new_id in defined_ids:
        msg = 'Instance with this id already exists'
        raise RenameConflictError(msg, context={'value': new_id})

    if is_managed and _is_active(manager.get_generator(id)):
        msg = 'Instance must be stopped before renaming'
        raise RenameBlockedError(msg, context={'value': id})

    if is_defined:
        try:
            startup.rename(id, new_id)
        except StartupError as e:
            raise RenameError(str(e), context=e.context) from None

    if not is_managed:
        return

    params = manager.get_generator(id).params
    try:
        manager.replace(id, params.model_copy(update={'id': new_id}))
    except ManagingError as e:
        _revert_startup_rename(startup, id, new_id, revert=is_defined)
        raise RenameError(str(e), context={'value': id}) from None


def _resolve_dir(generators_dir: Path, name: str) -> Path:
    """Resolve a project directory, translating path rejections."""
    try:
        return resolve_generator_dir(generators_dir, name)
    except WorkspaceError as e:
        raise RenameError(str(e), context=e.context) from None


def _iter_dependents(
    manager: GeneratorManager,
    generators_dir: Path,
    name: str,
) -> Iterator[Generator]:
    """Iterate over managed generators configured from a project.

    Matches against the unresolved directory, since generator paths are
    built from `generators_dir` as configured.
    """
    project_dir = generators_dir / name

    for generator in manager.iter_generators():
        if generator.params.path.is_relative_to(project_dir):
            yield generator


def _repoint_dependents(
    manager: GeneratorManager,
    dependents: list[Generator],
    generators_dir: Path,
    name: str,
    new_name: str,
) -> None:
    """Point managed generators at the renamed project directory."""
    old_dir = generators_dir / name
    new_dir = generators_dir / new_name

    for generator in dependents:
        params = generator.params
        rebased = new_dir / params.path.relative_to(old_dir)

        try:
            manager.replace(
                params.id,
                params.model_copy(update={'path': rebased}),
            )
        except ManagingError as e:
            msg = (
                'Project is renamed but some instances still point at the '
                'old directory'
            )
            raise RenameError(
                msg,
                context={'reason': str(e), 'value': params.id},
            ) from None


def _is_active(generator: Generator) -> bool:
    """Whether a generator is initializing, running or stopping."""
    return (
        generator.is_initializing
        or generator.is_running
        or generator.is_stopping
    )


def _list_defined_ids(startup: Startup) -> set[str]:
    """Ids of all entries in the startup file."""
    try:
        params_list = startup.get_all()
    except StartupError as e:
        raise RenameError(str(e), context=e.context) from None

    return {params.id for params in params_list.root}


def _revert_dir_rename(
    generators_dir: Path,
    name: str,
    new_name: str,
) -> None:
    """Rename a project directory back, reporting a failed revert."""
    try:
        rename_generator_dir(generators_dir, new_name, name)
    except WorkspaceError as e:
        msg = (
            'Project directory is renamed but instances still point '
            'at the old name'
        )
        raise RenameError(
            msg, context={**e.context, 'name': new_name}
        ) from None


def _revert_startup_rename(
    startup: Startup,
    id: str,
    new_id: str,
    *,
    revert: bool,
) -> None:
    """Rename a startup entry back, reporting a failed revert."""
    if not revert:
        return

    try:
        startup.rename(new_id, id)
    except StartupError as e:
        msg = 'Instance is renamed in the startup file but not in the manager'
        raise RenameError(
            msg, context={**e.context, 'value': new_id}
        ) from None
