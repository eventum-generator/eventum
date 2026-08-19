"""Reading the catalog a fetched repository publishes."""

import re
import stat
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import cast

from dulwich.errors import NotGitRepository
from dulwich.object_store import BaseObjectStore
from dulwich.objects import Blob, Commit, ObjectID, Tree, TreeEntry
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
MAX_TITLE_LENGTH = 200

# A tree is walked before anything about the repository that published
# it is known, and a tree is a graph rather than a hierarchy: one
# subtree may be listed by many others, so a walk that follows every
# entry of a handful of objects can visit an exponential number of
# paths. What is visited is therefore counted and remembered, and a
# tree that reaches either bound is refused instead of walked.
MAX_TREE_NODES = 100_000
MAX_TREE_DEPTH = 64

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
        commit = _resolve_commit(store, revision)
        generators = _resolve_generators_tree(store, commit)

        entries = [
            _read_entry(store, name, tree)
            for name, tree in _iter_directories(store, generators)
            if config_filename.encode() in tree
        ]

    return Catalog(
        revision=revision,
        refreshed_at=datetime.now(tz=UTC),
        committed_at=_commit_time(commit),
        author=_commit_author(commit),
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
    generators = _resolve_generators_tree(
        store,
        _resolve_commit(store, revision),
    )

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


def _resolve_commit(store: BaseObjectStore, revision: str) -> Commit:
    """Return the commit the catalog is read from.

    Raises
    ------
    CatalogError
        If the fetched repository does not hold the revision.

    """
    try:
        return cast('Commit', store[ObjectID(revision.encode())])
    except KeyError:
        msg = 'Fetched repository does not hold the revision'
        raise CatalogError(msg, context={'value': revision}) from None


def _commit_time(commit: Commit) -> datetime:
    """Return the moment a commit was authored at."""
    return datetime.fromtimestamp(
        commit.author_time,
        tz=timezone(timedelta(seconds=commit.author_timezone)),
    )


def _commit_author(commit: Commit) -> str | None:
    """Return the name of the author of a commit."""
    author = commit.author.decode('utf-8', errors='replace')
    name = author.split('<')[0].strip()

    return name or None


def _resolve_generators_tree(store: BaseObjectStore, commit: Commit) -> Tree:
    """Return the tree of the generators directory.

    Raises
    ------
    CatalogError
        If the directory is missing.

    """
    root = load_tree(store, commit.tree)

    try:
        mode, sha = root[GENERATORS_DIR.encode()]
    except KeyError:
        mode, sha = None, None

    if mode is None or sha is None or not stat.S_ISDIR(mode):
        msg = 'Repository publishes no generators directory'
        raise CatalogError(msg, context={'path': GENERATORS_DIR})

    return load_tree(store, sha)


def _iter_directories(
    store: BaseObjectStore,
    tree: Tree,
) -> list[tuple[str, Tree]]:
    """Return the subdirectories of a tree, named and loaded."""
    return [
        (entry.path.decode(errors='replace'), load_tree(store, entry.sha))
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
        path=f'{GENERATORS_DIR}/{name}',
        tree=tree.id.decode(),
        title=title,
        summary=summary,
        file_count=file_count,
        size=size,
    )


def load_tree(store: BaseObjectStore, sha: bytes) -> Tree:
    """Return the tree with the provided hash.

    What a repository publishes is read before anything about it is
    known, so the mode bits of an entry are a claim rather than a
    fact: an entry marked as a directory may name a blob, or name
    nothing at all.

    Parameters
    ----------
    store : BaseObjectStore
        Object store of the fetched repository.

    sha : bytes
        Hash of the object to load.

    Returns
    -------
    Tree
        Loaded tree.

    Raises
    ------
    CatalogError
        If the repository holds no such object, or holds something
        other than a tree under that hash.

    """
    try:
        obj = store[ObjectID(sha)]
    except KeyError:
        msg = 'Repository refers to an object it does not hold'
        raise CatalogError(
            msg,
            context={'value': sha.decode(errors='replace')},
        ) from None

    if not isinstance(obj, Tree):
        msg = 'Repository holds a directory entry that is not a directory'
        raise CatalogError(
            msg,
            context={'value': sha.decode(errors='replace')},
        )

    return obj


def _measure(store: BaseObjectStore, tree: Tree) -> tuple[int, int]:
    """Return the number and the total size of the files of a tree.

    Only regular files are counted, since only they are installed.

    Raises
    ------
    CatalogError
        If the tree is deeper or larger than a published generator may
        be, or refers to an object the repository does not hold.

    """
    file_count = 0
    size = 0

    for _, entry in walk_tree(store, tree):
        if stat.S_ISREG(entry.mode):
            file_count += 1
            size += store[ObjectID(entry.sha)].raw_length()

    return file_count, size


def walk_tree(
    store: BaseObjectStore,
    tree: Tree,
) -> Iterator[tuple[PurePosixPath, TreeEntry]]:
    """Yield every entry of a tree with the path it sits at.

    The walk is bounded and remembers the subtrees it has seen, so a
    tree that lists one subtree from many places is walked once rather
    than once per path leading to it.

    Parameters
    ----------
    store : BaseObjectStore
        Object store of the fetched repository.

    tree : Tree
        Tree to walk.

    Yields
    ------
    tuple[PurePosixPath, TreeEntry]
        Path of the entry relative to the walked tree, and the entry.

    Raises
    ------
    CatalogError
        If the tree is deeper or holds more entries than a published
        generator may, or refers to an object the repository does not
        hold.

    """
    pending: list[tuple[PurePosixPath, Tree, int]] = [
        (PurePosixPath(), tree, 0),
    ]
    seen: set[bytes] = {bytes(tree.id)}
    visited = 0

    while pending:
        prefix, current, depth = pending.pop()

        for entry in current.items():
            visited += 1

            if visited > MAX_TREE_NODES:
                msg = 'Repository holds more entries than can be read'
                raise CatalogError(
                    msg,
                    context={'count': visited, 'limit': MAX_TREE_NODES},
                )

            path = prefix / entry.path.decode(errors='replace')

            yield path, entry

            if not stat.S_ISDIR(entry.mode) or bytes(entry.sha) in seen:
                continue

            if depth + 1 > MAX_TREE_DEPTH:
                msg = 'Repository holds a directory nested too deeply'
                raise CatalogError(
                    msg,
                    context={'count': depth + 1, 'limit': MAX_TREE_DEPTH},
                )

            seen.add(bytes(entry.sha))
            pending.append((path, load_tree(store, entry.sha), depth + 1))


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
            title = _clip(
                _strip_markup(match.group('title')),
                MAX_TITLE_LENGTH,
            )
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

    summary = _clip(_strip_markup(' '.join(paragraph)), MAX_SUMMARY_LENGTH)

    return title, summary


def _clip(text: str, limit: int) -> str:
    """Return a line of readme prose no longer than a limit."""
    if len(text) <= limit:
        return text

    return text[:limit].rstrip() + '...'


def _strip_markup(text: str) -> str:
    """Return a line of readme prose as plain text.

    A summary is shown as text, so a link keeps its label and the
    emphasis markers around a word are dropped rather than read out.
    """
    return _EMPHASIS.sub('', _LINK.sub(r'\1', text))
