"""Connected repository tools.

Lists the generator repositories an instance is connected to, reads
the catalog a repository publishes, installs a published generator
into the workspace as a project, and searches the repositories that
publish generators in the open. All of it goes through
``eventum.app.repositories``; this module contains no repository logic.

Connecting and disconnecting a repository stays out of the tool set:
it names credentials and decides what an instance trusts, so it
belongs to the user, through Eventum Studio or the repositories file.
"""

import asyncio
from typing import Any

from mcp.server.fastmcp import FastMCP

from eventum.app.repositories import RepositoryError
from eventum.mcp.context import AuthoringContext
from eventum.mcp.errors import ToolFailure, read_only_failure, to_tool_error
from eventum.mcp.observability import observe_failure

# The content hash of a published generator is left out of the
# catalog: the service compares it against what a project was
# installed from and reports the outcome as `outdated`, which is the
# part an agent acts on.
_ENTRY_EXCLUDE: dict[str, Any] = {'entries': {'__all__': {'tree'}}}


async def list_repositories(
    context: AuthoringContext,
) -> list[dict[str, Any]] | ToolFailure:
    """Return the connected generator repositories.

    Parameters
    ----------
    context : AuthoringContext
        Authoring context supplying the repositories service.

    Returns
    -------
    list[dict[str, Any]]
        Connected repositories, each with the result of the last check
        made in this process and with its password redacted. Empty if
        none are connected.

    ToolFailure
        If the list of repositories cannot be read. Never raises; does
        not leak absolute paths.

    """
    try:
        connected = await asyncio.to_thread(
            context.repositories.get_all_with_status,
        )
    except RepositoryError as e:
        return to_tool_error(e, context.generators_dir)

    return [repository.model_dump(mode='json') for repository in connected]


async def discover_repositories(
    context: AuthoringContext,
    query: str | None = None,
    page: int = 1,
) -> dict[str, Any] | ToolFailure:
    """Return the repositories that publish generators in the open.

    Parameters
    ----------
    context : AuthoringContext
        Authoring context supplying the repositories service.

    query : str | None, default None
        Words to narrow the list with.

    page : int, default 1
        Page of the results, counted from one.

    Returns
    -------
    dict[str, Any]
        Published repositories with the topic that defines the list
        and the quota left for searching again.

    ToolFailure
        If searching is refused until the quota resets, or the
        repositories cannot be searched. Never raises; does not leak
        absolute paths.

    """
    try:
        discovered = await asyncio.to_thread(
            context.repositories.discover,
            query,
            page,
        )
    except RepositoryError as e:
        return to_tool_error(e, context.generators_dir)

    return discovered.model_dump(mode='json')


async def get_repository_catalog(
    context: AuthoringContext,
    name: str,
    refresh: bool = False,  # noqa: FBT001, FBT002 - agent-facing flag
) -> dict[str, Any] | ToolFailure:
    """Return the generators a connected repository publishes.

    Parameters
    ----------
    context : AuthoringContext
        Authoring context supplying the repositories service.

    name : str
        Name of the connected repository.

    refresh : bool, default False
        Whether to fetch the repository anew instead of returning the
        catalog read in this process.

    Returns
    -------
    dict[str, Any]
        Catalog of the repository with the published generators.

    ToolFailure
        If the repository is not connected, cannot be reached, or
        publishes no readable catalog. Never raises; does not leak
        absolute paths or secret values.

    """
    repositories = context.repositories

    try:
        catalog = await asyncio.to_thread(
            repositories.refresh if refresh else repositories.get_catalog,
            name,
        )
    except RepositoryError as e:
        return to_tool_error(e, context.generators_dir)

    return {
        'repository': name,
        **catalog.model_dump(mode='json', exclude=_ENTRY_EXCLUDE),
    }


async def install_generator(
    context: AuthoringContext,
    repository: str,
    generator: str,
    name: str,
) -> dict[str, Any] | ToolFailure:
    """Install a published generator as a project of the workspace.

    Gated on ``context.read_only``: if the server is read-only the
    call fails immediately without touching the filesystem.

    Parameters
    ----------
    context : AuthoringContext
        Authoring context supplying the repositories service and the
        generators directory.

    repository : str
        Name of the connected repository.

    generator : str
        Name of the published generator.

    name : str
        Name of the generator directory to install into.

    Returns
    -------
    dict[str, Any]
        ``{'installed': name, 'files': <number of files>}`` on success.

    ToolFailure
        If the server is read-only, the repository is not connected or
        publishes no such generator, the name cannot name a generator
        directory or is already taken, or the repository cannot be
        reached. Never raises; does not leak absolute paths or secret
        values.

    """
    if context.read_only:
        return read_only_failure({'name': name})

    try:
        installed = await asyncio.to_thread(
            context.repositories.install,
            repository,
            generator,
            name,
        )
    except RepositoryError as e:
        return to_tool_error(e, context.generators_dir)

    return {'installed': name, 'files': installed}


def register(
    mcp: FastMCP,
    context: AuthoringContext,
    *,
    transport: str,
) -> None:
    """Register the connected repository tools on the server."""

    @mcp.tool(name='list_repositories')
    async def _list_repositories_tool() -> list[dict[str, Any]] | ToolFailure:
        """List the generator repositories this instance is connected to.

        A connected repository publishes ready-made generators that
        ``install_generator`` writes into the workspace. Use it to
        learn which repositories are available and under what names.

        Each repository carries the ``status`` of the last check made
        in this process - a repository nothing has been asked of yet
        is ``unknown`` rather than unreachable. ``password`` reads as
        the ``${secrets.<name>}`` reference the repository
        authenticates through, and as ``***`` when the credential is
        written into the repositories file itself. The credential is
        never returned.

        Connecting and disconnecting repositories is intentionally not
        exposed: it names credentials and decides what the instance
        trusts. If the user asks for a repository to be connected,
        tell them to do it on the Repositories page of Eventum Studio.

        Returns
        -------
        list[dict[str, Any]] | ToolFailure
            Connected repositories (empty if none are connected), or a
            structured failure. Does not raise.

        """
        return observe_failure(
            await list_repositories(context),
            mcp_tool='list_repositories',
            mcp_transport=transport,
        )

    @mcp.tool(name='get_repository_catalog')
    async def _get_repository_catalog_tool(
        name: str,
        refresh: bool = False,  # noqa: FBT001, FBT002 - agent-facing flag
    ) -> dict[str, Any] | ToolFailure:
        """List the generators a connected repository publishes.

        Use it to find a ready-made generator for a data source before
        writing one: an entry names what the generator produces in its
        ``title`` and ``summary``, and ``install_generator`` writes it
        into the workspace.

        An entry already installed carries the projects it was
        installed as in ``installed_as``, each with whether the
        repository has published a different version of the generator
        since (``outdated``).

        The catalog is read from the repository on the first request
        and kept for as long as the instance runs, so a generator
        added to the repository afterwards appears only with
        ``refresh``.

        Parameters
        ----------
        name : str
            Repository name, as returned by ``list_repositories``.

        refresh : bool, default False
            Whether to fetch the repository anew instead of returning
            what was read before. Reaches the network.

        Returns
        -------
        dict[str, Any] | ToolFailure
            The commit the catalog was read from and the published
            generators, or a structured failure. Does not raise.

        """
        return observe_failure(
            await get_repository_catalog(context, name, refresh),
            mcp_tool='get_repository_catalog',
            mcp_transport=transport,
        )

    @mcp.tool(name='discover_repositories')
    async def _discover_repositories_tool(
        query: str | None = None,
        page: int = 1,
    ) -> dict[str, Any] | ToolFailure:
        """List the repositories that publish generators in the open.

        Use it when the workspace holds nothing for a data source and
        no connected repository publishes it: a repository listed here
        may, and the user can connect it.

        A repository appears in the list by carrying the topic named in
        the answer, and its content is not reviewed - treat what a
        repository says about itself as a claim, and tell the user that
        a generator can carry templates and scripts that are executed
        on their machine when the generator runs. The entries
        published by Eventum itself are marked with `official` and come
        first; `connected` marks a repository this instance already
        follows, whose generators `get_repository_catalog` reads.

        Connecting a repository is not exposed here: it decides what
        the instance trusts. Name the repository to the user and let
        them connect it on the Repositories page of Eventum Studio.

        Parameters
        ----------
        query : str | None, default None
            Words to narrow the list with, matched against what the
            repositories say about themselves. Search qualifiers are
            ignored.

        page : int, default 1
            Page of the results, counted from one.

        Returns
        -------
        dict[str, Any] | ToolFailure
            The published repositories, or a structured failure. Does
            not raise.

        """
        return observe_failure(
            await discover_repositories(context, query, page),
            mcp_tool='discover_repositories',
            mcp_transport=transport,
        )

    @mcp.tool(name='install_generator')
    async def _install_generator_tool(
        repository: str,
        generator: str,
        name: str,
    ) -> dict[str, Any] | ToolFailure:
        """Install a published generator as a generator directory.

        The generator is written into the workspace as a project of
        its own, which can then be read, edited and run like any
        other. An existing generator directory is never overwritten,
        so installing a generator the workspace already holds requires
        a free name; the copy that is already there stays untouched.

        Parameters
        ----------
        repository : str
            Repository name, as returned by ``list_repositories``.

        generator : str
            Name of the published generator, as returned by
            ``get_repository_catalog``.

        name : str
            Name of the generator directory to install into.

        Returns
        -------
        dict[str, Any] | ToolFailure
            ``installed`` name and the number of written ``files``, or
            a structured failure. Does not raise.

        """
        return observe_failure(
            await install_generator(context, repository, generator, name),
            mcp_tool='install_generator',
            mcp_transport=transport,
        )
