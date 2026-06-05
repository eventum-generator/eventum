"""Secret-introspection tool.

Lists the names of secrets stored in the keyring so an agent can
reference them as ``${secrets.<name>}`` in configs. Names only - no
secret value ever crosses the boundary.
"""

from mcp.server.fastmcp import FastMCP

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


def register(
    mcp: FastMCP,
    context: AuthoringContext,
    *,
    transport: str,
) -> None:
    """Register the secret-introspection tool on the server."""

    @mcp.tool(name='list_secrets')
    def _list_secrets_tool() -> list[str] | ToolFailure:
        """List the names of secrets available in the keyring.

        Use it to learn which secrets a config can reference as
        ``${secrets.<name>}``. Returns names only - never values.

        Returns
        -------
        list[str] | ToolFailure
            Sorted secret names (empty if none are configured), or a
            structured failure if the keyring cannot be read. Does not
            raise.

        """
        return observe_failure(
            list_secret_names(context),
            mcp_tool='list_secrets',
            mcp_transport=transport,
        )
