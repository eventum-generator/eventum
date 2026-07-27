"""Secret name tools.

Lists the names of secrets stored in the keyring so an agent can
reference them as ``${secrets.<name>}`` in configs, and reports which
projects read a given secret. Names only - no secret value ever crosses
the boundary, and reading, adding and removing a value stay a human
task through the ``eventum-keyring`` CLI. Renaming lives with the other
rename tools, so it is available only on a writable live server.
"""

import asyncio
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from eventum.app.workspace import find_secret_references
from eventum.mcp.context import AuthoringContext
from eventum.mcp.errors import ToolFailure
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
) -> list[str] | ToolFailure:
    """Return the projects whose configuration reads a secret.

    Only generator configurations are scanned, since ``${secrets.*}``
    tokens are substituted in them alone.

    Parameters
    ----------
    context : AuthoringContext
        Authoring context supplying the generators directory.

    secret : str
        Name of the secret to look for.

    Returns
    -------
    list[str]
        Sorted names of the projects referencing the secret.

    ToolFailure
        If the generators directory cannot be scanned. Never raises;
        carries no path.

    """
    try:
        return await asyncio.to_thread(
            find_secret_references,
            context.generators_dir,
            Path(context.config_filename),
            secret,
        )
    except Exception:  # noqa: BLE001 - no raw error/path may escape
        return ToolFailure(error='Failed to scan generator configurations')


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
    ) -> list[str] | ToolFailure:
        """List the projects whose configuration reads a secret.

        Use it before renaming or removing a secret to see what would
        break: the projects listed carry a ``${secrets.<name>}`` token
        for it.

        Parameters
        ----------
        secret : str
            Secret name, as returned by ``list_secret_names``.

        Returns
        -------
        list[str] | ToolFailure
            Sorted project names (empty if none reference the secret),
            or a structured failure if the generator configurations
            cannot be scanned. Does not raise.

        """
        return observe_failure(
            await list_secret_references(context, secret),
            mcp_tool='list_secret_references',
            mcp_transport=transport,
        )
