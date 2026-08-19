"""Origin a project installed from a repository carries with it."""

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import yaml
from pydantic import ValidationError

from eventum.app.repositories.exceptions import RepositoryError
from eventum.app.repositories.models import (
    GeneratorSource,
    identify_repository,
)

# The project carries its own origin the way a package carries its
# manifest: the file travels with the project through a rename, an
# export and an import, and nothing outside the project has to be kept
# in step with it.
SOURCE_FILENAME = '.eventum-source.yml'

# The origin is a handful of scalars, so a file that is not one is not
# worth reading whatever it holds.
MAX_SOURCE_SIZE = 64 * 1024


def write_source(project_dir: Path, source: GeneratorSource) -> None:
    """Write the origin of an installed generator into a project.

    Parameters
    ----------
    project_dir : Path
        Directory of the project.

    source : GeneratorSource
        Origin to write.

    Raises
    ------
    RepositoryError
        If the file cannot be written.

    """
    path = project_dir / SOURCE_FILENAME
    content = yaml.dump(
        source.model_dump(mode='json'),
        sort_keys=False,
        allow_unicode=True,
    )

    try:
        path.write_text(content, encoding='utf-8')
    except OSError as e:
        msg = 'Cannot write the origin of the installed generator'
        raise RepositoryError(
            msg,
            context={'file_path': str(path), 'reason': str(e)},
        ) from None


def build_source(  # noqa: PLR0913 - the origin is what it is
    *,
    repository: str,
    url: str,
    ref: str | None,
    entry: str,
    revision: str,
    tree: str,
) -> GeneratorSource:
    """Build the origin of an installation happening now.

    Parameters
    ----------
    repository : str
        Name the repository was connected under.

    url : str
        URL the repository was fetched from.

    ref : str | None
        Branch or tag the generator was installed from.

    entry : str
        Name of the published generator.

    revision : str
        Commit the catalog was read from.

    tree : str
        Content hash of the generator directory.

    Returns
    -------
    GeneratorSource
        Origin of the installation.

    """
    return GeneratorSource(
        repository=repository,
        url=url,
        ref=ref,
        entry=entry,
        revision=revision,
        tree=tree,
        installed_at=datetime.now(tz=UTC),
    )


def read_source(project_dir: Path) -> GeneratorSource | None:
    """Read the origin a project carries.

    A project without a readable origin - one created in Studio, or
    one whose file was edited into something else - simply has none.

    Parameters
    ----------
    project_dir : Path
        Directory of the project.

    Returns
    -------
    GeneratorSource | None
        Origin of the project, or `None` when it carries none.

    """
    path = project_dir / SOURCE_FILENAME

    try:
        if not path.is_file() or path.stat().st_size > MAX_SOURCE_SIZE:
            return None

        parsed = yaml.safe_load(path.read_text(encoding='utf-8'))
    except OSError, UnicodeDecodeError, yaml.YAMLError:
        return None

    try:
        return GeneratorSource.model_validate(parsed)
    except ValidationError:
        return None


def iter_installed(
    generators_dir: Path,
) -> Iterator[tuple[str, GeneratorSource]]:
    """Yield every project of a workspace that carries an origin.

    Parameters
    ----------
    generators_dir : Path
        Directory the projects of the workspace live in.

    Yields
    ------
    tuple[str, GeneratorSource]
        Name of the project directory and the origin it carries.

    """
    try:
        projects = sorted(
            path for path in generators_dir.iterdir() if path.is_dir()
        )
    except OSError:
        return

    for project_dir in projects:
        source = read_source(project_dir)

        if source is not None:
            yield project_dir.name, source


def collect_installed(
    generators_dir: Path,
    url: str,
) -> dict[str, list[tuple[str, GeneratorSource]]]:
    """Return what a repository has installed in a workspace.

    A project counts as an installation when the origin it carries
    names the same repository, so a project that merely shares a name
    with a catalog entry is not mistaken for one, and a renamed
    project is still recognized. The workspace is walked once,
    whatever the size of the catalog.

    Parameters
    ----------
    generators_dir : Path
        Directory the projects of the workspace live in.

    url : str
        URL of the repository.

    Returns
    -------
    dict[str, list[tuple[str, GeneratorSource]]]
        Projects and the origin each of them carries, keyed by the
        name of the published generator they came from.

    """
    identity = identify_repository(url)
    installed: dict[str, list[tuple[str, GeneratorSource]]] = {}

    for project, source in iter_installed(generators_dir):
        if identify_repository(source.url) != identity:
            continue

        installed.setdefault(source.entry, []).append((project, source))

    return installed
