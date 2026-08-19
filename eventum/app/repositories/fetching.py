"""Fetching of connected repositories from their remotes."""

from collections.abc import Mapping
from pathlib import Path
from typing import cast

import urllib3
from dulwich.client import (
    GitClient,
    HTTPProxyUnauthorized,
    HTTPUnauthorized,
    default_urllib3_manager,
    get_transport_and_path,
)
from dulwich.object_store import peel_sha
from dulwich.objects import ObjectID
from dulwich.refs import Ref
from dulwich.repo import Repo

from eventum.app.repositories.exceptions import RepositoryFetchError
from eventum.app.repositories.models import Repository

# Every fetch is a request the server makes on behalf of a caller, so
# it is bounded: only the tip commit of the wanted reference is asked
# for, no single operation may stall longer than the timeout, and the
# whole exchange has a deadline, so that a remote answering one byte
# at a time releases the worker thread rather than holding it for as
# long as it likes.
#
# What is not bounded is where the request goes: the URL is the one an
# operator connected, and an address inside the network of the host is
# as reachable as any other. Connecting a repository is an
# authenticated operation for that reason.
FETCH_DEPTH = 1
DEFAULT_FETCH_TIMEOUT = 60.0
FETCH_DEADLINE_FACTOR = 10

_HEAD_REF = Ref(b'HEAD')

# A host answers a request for a repository it does not serve the same
# way it answers one it serves privately: by asking who is calling. A
# caller that named no credentials reads that as being about
# credentials it never meant to give, so the other reading is offered
# alongside.
_AUTH_HINT = (
    'The repository may not exist at this address, or may be private - '
    'provide a user name and a secret to reach it'
)


def fetch_repository(
    repository: Repository,
    destination: Path,
    *,
    password: str | None = None,
    timeout: float = DEFAULT_FETCH_TIMEOUT,
) -> str:
    """Fetch a repository into a bare git repository.

    Only the tip commit of the wanted reference is fetched, and it is
    fetched into a bare repository - nothing of the remote is written
    out as files, so what the repository holds is inspected as git
    objects before any of it reaches the workspace.

    Parameters
    ----------
    repository : Repository
        Repository to fetch.

    destination : Path
        Directory to initialize the bare repository in. Created if
        missing; left in a partial state if the fetch fails.

    password : str | None, default=None
        Password or access token to authenticate with.

    timeout : float, default=DEFAULT_FETCH_TIMEOUT
        Timeout of a single HTTP operation, in seconds.

    Returns
    -------
    str
        Hash of the fetched commit.

    Raises
    ------
    RepositoryFetchError
        If the remote cannot be reached, refuses the credentials,
        publishes no wanted reference, or the fetched reference does
        not resolve to a commit.

    """
    wanted: list[ObjectID] = []

    def determine_wants(
        refs: Mapping[Ref, ObjectID],
        depth: int | None = None,  # noqa: ARG001
    ) -> list[ObjectID]:
        wanted.append(_resolve_ref(refs, repository))
        return wanted

    try:
        client, path, pool_manager = _build_client(
            repository,
            password,
            timeout,
        )

        try:
            with Repo.init_bare(str(destination), mkdir=True) as repo:
                client.fetch(
                    path,
                    repo,
                    determine_wants=determine_wants,
                    depth=FETCH_DEPTH,
                )

                return _peel_commit(repo, _wanted_object(wanted, repository))
        finally:
            pool_manager.clear()
    except RepositoryFetchError:
        raise
    except Exception as e:  # noqa: BLE001 - transports fail in many ways
        msg = 'Failed to fetch repository'
        raise RepositoryFetchError(
            msg,
            context=_failure_context(repository, password, e),
        ) from None


def _wanted_object(
    wanted: list[ObjectID],
    repository: Repository,
) -> ObjectID:
    """Return the object the fetch asked the remote for.

    Raises
    ------
    RepositoryFetchError
        If the remote published nothing to ask for.

    """
    if not wanted:
        msg = 'Repository publishes no branches or tags'
        raise RepositoryFetchError(
            msg,
            context={'name': repository.name, 'url': repository.url},
        )

    return wanted[0]


def probe_repository(
    repository: Repository,
    *,
    password: str | None = None,
    timeout: float = DEFAULT_FETCH_TIMEOUT,
) -> None:
    """Check that a repository answers and publishes the wanted ref.

    Asks the remote for the references it publishes and nothing else,
    so a repository is checked without transferring any of it.

    Parameters
    ----------
    repository : Repository
        Repository to check.

    password : str | None, default=None
        Password or access token to authenticate with.

    timeout : float, default=DEFAULT_FETCH_TIMEOUT
        Timeout of a single HTTP operation, in seconds.

    Raises
    ------
    RepositoryFetchError
        If the remote cannot be reached, refuses the credentials, or
        publishes no wanted reference.

    """
    try:
        client, path, pool_manager = _build_client(
            repository,
            password,
            timeout,
        )

        try:
            result = client.get_refs(
                path.encode() if isinstance(path, str) else path,
            )
        finally:
            pool_manager.clear()
    except Exception as e:  # noqa: BLE001 - transports fail in many ways
        msg = 'Failed to reach repository'
        raise RepositoryFetchError(
            msg,
            context=_failure_context(repository, password, e),
        ) from None

    published = {
        ref: sha for ref, sha in result.refs.items() if sha is not None
    }

    _resolve_ref(published, repository)


def _build_client(
    repository: Repository,
    password: str | None,
    timeout: float,
) -> tuple[GitClient, str, urllib3.PoolManager]:
    """Build the client that talks to the remote of a repository.

    The pool it holds belongs to one exchange: the caller closes it,
    so a server that fetches all day does not accumulate one pool per
    fetch.
    """
    pool_manager = cast(
        'urllib3.PoolManager',
        default_urllib3_manager(
            config=None,
            base_url=repository.url,
            timeout=timeout,
        ),
    )

    # The timeout dulwich sets bounds one read; the deadline bounds
    # the exchange, which is what a remote answering slowly but never
    # stopping would otherwise stretch without end.
    pool_manager.connection_pool_kw['timeout'] = urllib3.Timeout(
        connect=timeout,
        read=timeout,
        total=timeout * FETCH_DEADLINE_FACTOR,
    )

    client, path = get_transport_and_path(
        repository.url,
        username=repository.username,
        password=password,
        pool_manager=pool_manager,
    )

    return client, path, pool_manager


def _resolve_ref(
    refs: Mapping[Ref, ObjectID],
    repository: Repository,
) -> ObjectID:
    """Return the hash of the object the wanted reference points at.

    Raises
    ------
    RepositoryFetchError
        If the remote publishes no wanted reference.

    """
    for candidate in _ref_candidates(repository.ref):
        if candidate in refs:
            return refs[candidate]

    msg = 'Repository publishes no such branch or tag'
    raise RepositoryFetchError(
        msg,
        context={
            'name': repository.name,
            'url': repository.url,
            'ref': repository.ref or _HEAD_REF.decode(),
        },
    )


def _ref_candidates(ref: str | None) -> tuple[Ref, ...]:
    """Return the reference names to look for, most specific first."""
    if ref is None:
        return (_HEAD_REF,)

    encoded = ref.encode()

    if encoded.startswith(b'refs/'):
        return (Ref(encoded),)

    # The peeled entry of an annotated tag comes first, so that a tag
    # resolves to the commit it marks rather than to the tag object.
    return (
        Ref(b'refs/heads/' + encoded),
        Ref(b'refs/tags/' + encoded + b'^{}'),
        Ref(b'refs/tags/' + encoded),
    )


def _peel_commit(repo: Repo, sha: ObjectID) -> str:
    """Return the hash of the commit a fetched object resolves to.

    Raises
    ------
    RepositoryFetchError
        If the object does not resolve to a commit.

    """
    try:
        _, peeled = peel_sha(repo.object_store, sha)
    except KeyError:
        peeled = None

    if peeled is None or peeled.type_name != b'commit':
        msg = 'Fetched reference does not point at a commit'
        raise RepositoryFetchError(
            msg,
            context={'value': sha.decode(errors='replace')},
        )

    return peeled.id.decode()


def _failure_context(
    repository: Repository,
    password: str | None,
    error: Exception,
) -> dict[str, str]:
    """Build the context of a remote that could not be reached."""
    reason = _hide_password(str(error), password)
    context = {
        'name': repository.name,
        'url': repository.url,
        'reason': reason,
    }

    named_credentials = repository.username is not None or password is not None
    asked_who_is_calling = isinstance(
        error,
        (HTTPUnauthorized, HTTPProxyUnauthorized),
    )

    if not named_credentials and asked_who_is_calling:
        context['hint'] = _AUTH_HINT

    return context


def _hide_password(reason: str, password: str | None) -> str:
    """Return a failure reason with the password taken out of it."""
    if not password:
        return reason

    return reason.replace(password, '***')
