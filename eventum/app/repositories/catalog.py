"""Reading the catalog a fetched repository publishes."""

import re
import stat
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from dulwich.errors import NotGitRepository
from dulwich.object_store import BaseObjectStore
from dulwich.objects import Blob, Commit, ObjectID, Tree
from dulwich.repo import Repo

from eventum.app.repositories.exceptions import (
    CatalogEntryNotFoundError,
    CatalogError,
)
from eventum.app.repositories.models import Catalog, CatalogEntry

# Directory a repository publishes its generators from. Each of its
# subdirectories holding a generator configuration is one catalog
# entry, which is the layout of the Eventum content packs.
GENERATORS_DIR = 'generators'

README_FILENAME = 'README.md'

# A readme is read only to take a title and a summary out of it, so an
# unreasonably large one is left unread rather than decoded in full.
MAX_README_SIZE = 256 * 1024

MAX_SUMMARY_LENGTH = 400

_HEADING = re.compile(r'^#\s+(?P<title>.+?)\s*$')
_SKIPPED_LINE = re.compile(r'^(?:#{1,6}\s|[-*+>|]|\d+\.\s|```|<|!?\[)')
_LINK = re.compile(r'\[([^\]]*)\]\([^)]*\)')
_EMPHASIS = re.compile(r'\*{1,2}|`')


def read_catalog(
    repo_path: Path,
    revision: str,
    *,
    config_filename: str,
) -> Catalog:
    """Read the catalog of a fetched repository.

    Parameters
    ----------
    repo_path : Path
        Directory of the bare repository the remote was fetched into.

    revision : str
        Hash of the fetched commit.

    config_filename : str
        Name of the generator configuration file that marks a
        directory as a published generator.

    Returns
    -------
    Catalog
        Catalog of the repository.

    Raises
    ------
    CatalogError
        If the repository cannot be read or publishes no generators
        directory.

    """
    with open_repository(repo_path) as repo:
        store = repo.object_store
        generators = _resolve_generators_tree(store, revision)

        entries = [
            _read_entry(store, name, tree)
            for name, tree in _iter_directories(store, generators)
            if config_filename.encode() in tree
        ]

    return Catalog(
        revision=revision,
        refreshed_at=datetime.now(tz=UTC),
        entries=sorted(entries, key=lambda entry: entry.name),
    )


def resolve_entry_tree(
    store: BaseObjectStore,
    revision: str,
    entry: str,
) -> Tree:
    """Return the tree of a published generator.

    Parameters
    ----------
    store : BaseObjectStore
        Object store of the fetched repository.

    revision : str
        Hash of the fetched commit.

    entry : str
        Name of the published generator.

    Returns
    -------
    Tree
        Tree of the generator directory.

    Raises
    ------
    CatalogError
        If the repository publishes no generators directory.

    CatalogEntryNotFoundError
        If the generators directory holds no such generator.

    """
    generators = _resolve_generators_tree(store, revision)

    for name, tree in _iter_directories(store, generators):
        if name == entry:
            return tree

    msg = 'Repository publishes no such generator'
    raise CatalogEntryNotFoundError(msg, context={'name': entry})


def open_repository(repo_path: Path) -> Repo:
    """Open the bare repository a remote was fetched into.

    Parameters
    ----------
    repo_path : Path
        Directory of the bare repository.

    Returns
    -------
    Repo
        Opened repository. The caller closes it.

    Raises
    ------
    CatalogError
        If the repository cannot be opened.

    """
    try:
        return Repo(str(repo_path))
    except (NotGitRepository, OSError) as e:
        msg = 'Failed to read fetched repository'
        raise CatalogError(
            msg,
            context={'path': str(repo_path), 'reason': str(e)},
        ) from None


def _resolve_generators_tree(store: BaseObjectStore, revision: str) -> Tree:
    """Return the tree of the generators directory.

    Raises
    ------
    CatalogError
        If the revision cannot be read or the directory is missing.

    """
    try:
        commit = cast('Commit', store[ObjectID(revision.encode())])
        root = cast('Tree', store[commit.tree])
    except KeyError:
        msg = 'Fetched repository does not hold the revision'
        raise CatalogError(msg, context={'value': revision}) from None

    try:
        mode, sha = root[GENERATORS_DIR.encode()]
    except KeyError:
        mode, sha = None, None

    if mode is None or sha is None or not stat.S_ISDIR(mode):
        msg = 'Repository publishes no generators directory'
        raise CatalogError(msg, context={'path': GENERATORS_DIR})

    return cast('Tree', store[sha])


def _iter_directories(
    store: BaseObjectStore,
    tree: Tree,
) -> list[tuple[str, Tree]]:
    """Return the subdirectories of a tree, named and loaded."""
    return [
        (
            entry.path.decode(errors='replace'),
            cast('Tree', store[entry.sha]),
        )
        for entry in tree.items()
        if stat.S_ISDIR(entry.mode)
    ]


def _read_entry(
    store: BaseObjectStore,
    name: str,
    tree: Tree,
) -> CatalogEntry:
    """Read a single catalog entry from the tree of a generator."""
    file_count, size = _measure(store, tree)
    title, summary = _read_readme(store, tree)

    return CatalogEntry(
        name=name,
        title=title,
        summary=summary,
        file_count=file_count,
        size=size,
    )


def _measure(store: BaseObjectStore, tree: Tree) -> tuple[int, int]:
    """Return the number and the total size of the files of a tree.

    Only regular files are counted, since only they are installed.
    """
    file_count = 0
    size = 0

    for entry in tree.items():
        if stat.S_ISDIR(entry.mode):
            nested_count, nested_size = _measure(
                store,
                cast('Tree', store[entry.sha]),
            )
            file_count += nested_count
            size += nested_size
        elif stat.S_ISREG(entry.mode):
            file_count += 1
            size += store[entry.sha].raw_length()

    return file_count, size


def _read_readme(
    store: BaseObjectStore,
    tree: Tree,
) -> tuple[str | None, str | None]:
    """Return the title and the summary the readme of a tree carries."""
    try:
        mode, sha = tree[README_FILENAME.encode()]
    except KeyError:
        return None, None

    if not stat.S_ISREG(mode):
        return None, None

    blob = cast('Blob', store[sha])

    if blob.raw_length() > MAX_README_SIZE:
        return None, None

    return _parse_readme(blob.data.decode('utf-8', errors='replace'))


def _parse_readme(content: str) -> tuple[str | None, str | None]:
    """Return the title and the summary a readme text carries.

    The title is the first top level heading and the summary is the
    first paragraph of prose that follows it.
    """
    lines = content.splitlines()
    title: str | None = None
    index = 0

    for position, line in enumerate(lines):
        match = _HEADING.match(line)

        if match is not None:
            title = match.group('title')
            index = position + 1
            break

    paragraph: list[str] = []

    for line in lines[index:]:
        stripped = line.strip()

        if not stripped:
            if paragraph:
                break
            continue

        if _SKIPPED_LINE.match(stripped):
            if paragraph:
                break
            continue

        paragraph.append(stripped)

    if not paragraph:
        return title, None

    summary = _strip_markup(' '.join(paragraph))

    if len(summary) > MAX_SUMMARY_LENGTH:
        summary = summary[:MAX_SUMMARY_LENGTH].rstrip() + '...'

    return title, summary


def _strip_markup(text: str) -> str:
    """Return a line of readme prose as plain text.

    A summary is shown as text, so a link keeps its label and the
    emphasis markers around a word are dropped rather than read out.
    """
    return _EMPHASIS.sub('', _LINK.sub(r'\1', text))
