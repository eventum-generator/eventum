"""Secret name tools.

Lists the names of secrets stored in the keyring so an agent can
reference them as ``${secrets.<name>}`` in configs, and reports what
refers to a given secret. Names only - no secret value ever crosses
the boundary, and reading, adding and removing a value stay a human
task through the ``eventum-keyring`` CLI. Renaming lives with the other
rename tools, so it is available only on a writable live server.
"""

import asyncio
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from eventum.app.repositories import RepositoryError
from eventum.app.secrets import find_secret_references
from eventum.mcp.context import AuthoringContext
from eventum.mcp.errors import ToolFailure, to_tool_error
from eventum.mcp.observability import observe_failure
from eventum.security.manage import list_secrets


def list_secret_names(
    context: AuthoringContext,  # noqa: ARG001 - DI seam, unused here
) -> list[str] | ToolFailure:
    """Return the names of secrets stored in the keyring.

    The keyring location is a process-level setting (set by the HTTP
    app at startup, or by ``eventum mcp --keyring-cryptfile`` over
    stdio), so the context is not consulted for it here.

    Parameters
    ----------
    context : AuthoringContext
        Authoring context (DI seam; unused at this layer).

    Returns
    -------
    list[str]
        Sorted secret names. Empty if no keyring is configured or it
        holds no secrets. Never returns secret values.

    ToolFailure
        If the keyring cannot be read. Never raises; carries no path.

    """
    try:
        return sorted(list_secrets())
    except Exception:  # noqa: BLE001 - no raw error/path may escape
        return ToolFailure(error='Failed to read keyring')


async def list_secret_references(
    context: AuthoringContext, secret: str
) -> dict[str, list[str]] | ToolFailure:
    """Return what refers to a secret, by the kind of each referrer.

    A project refers to a secret through a ``${secrets.*}`` token in
    its configuration; a connected repository refers to one by name,
    to authenticate with the value behind it.

    Parameters
    ----------
    context : AuthoringContext
        Authoring context supplying the generators directory and the
        connected repositories.

    secret : str
        Name of the secret to look for.

    Returns
    -------
    dict[str, list[str]]
        Sorted names of the referring projects under ``projects`` and
        of the referring repositories under ``repositories``.

    ToolFailure
        If the projects or the connected repositories cannot be read.
        Never raises; carries no path.

    """
    try:
        references = await asyncio.to_thread(
            find_secret_references,
            generators_dir=context.generators_dir,
            config_filename=Path(context.config_filename),
            repositories=context.repositories,
            secret=secret,
        )
    except RepositoryError as e:
        return to_tool_error(e, context.generators_dir)
    except Exception:  # noqa: BLE001 - no raw error/path may escape
        return ToolFailure(error='Failed to read what refers to the secret')

    return {
        'projects': references.projects,
        'repositories': references.repositories,
    }


def register(
    mcp: FastMCP,
    context: AuthoringContext,
    *,
    transport: str,
) -> None:
    """Register the secret name tools on the server."""

    @mcp.tool(name='list_secret_names')
    def _list_secret_names_tool() -> list[str] | ToolFailure:
        """List the names of secrets available in the keyring.

        Use it to learn which secrets a config can reference as
        ``${secrets.<name>}``. Returns names only - never values.

        Reading, adding, and removing secret values is intentionally
        not exposed over MCP - managing them is a human task. If the
        user asks you to add, change, or read a secret value, tell them
        to run the ``eventum-keyring`` CLI themselves (for example
        ``eventum-keyring set <name> <value>``), then reference it in
        the config as ``${secrets.<name>}``. A secret's name can be
        changed with ``rename_secret``, which moves the value without
        exposing it.

        Returns
        -------
        list[str] | ToolFailure
            Sorted secret names (empty if none are configured), or a
            structured failure if the keyring cannot be read. Does not
            raise.

        """
        return observe_failure(
            list_secret_names(context),
            mcp_tool='list_secret_names',
            mcp_transport=transport,
        )

    @mcp.tool(name='list_secret_references')
    async def _list_secret_references_tool(
        secret: str,
    ) -> dict[str, list[str]] | ToolFailure:
        """List what refers to a secret, projects and repositories.

        Use it before renaming or removing a secret to see what would
        break. The projects listed carry a ``${secrets.<name>}`` token
        for it and keep the old name until their configuration is
        edited; the repositories listed authenticate with it and are
        repointed by ``rename_secret`` itself. The repositories are read
        from the file this server was pointed at, so over stdio they are
        the ones of that file alone.

        Parameters
        ----------
        secret : str
            Secret name, as returned by ``list_secret_names``.

        Returns
        -------
        dict[str, list[str]] | ToolFailure
            Sorted project names under ``projects`` and repository
            names under ``repositories``, either of them empty if
            nothing of that kind refers to the secret, or a structured
            failure if the projects or the connected repositories
            cannot be read. Does not raise.

        """
        return observe_failure(
            await list_secret_references(context, secret),
            mcp_tool='list_secret_references',
            mcp_transport=transport,
        )
