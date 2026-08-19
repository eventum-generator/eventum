"""Global-state tools (HTTP transport only).

Generators coordinate at runtime through the process-wide ``globals``
state of the event stage. These tools read and edit that shared state.
Values are arbitrary runtime data written by event plugins (not keyring
secrets) and are returned as-is, normalized to JSON-able types.
"""

import asyncio
from typing import Any

from mcp.server.fastmcp import FastMCP

from eventum.mcp.context import LiveContext
from eventum.mcp.errors import ToolFailure, read_only_failure
from eventum.mcp.observability import observe_failure
from eventum.plugins.event.state import GLOBAL_STATE
from eventum.utils.json_utils import normalize_types


async def get_global_state() -> dict[str, Any] | ToolFailure:
    """Return the whole global state as a JSON-able dict."""
    state = await asyncio.to_thread(GLOBAL_STATE.as_dict)
    try:
        return await asyncio.to_thread(normalize_types, state)
    except RuntimeError:
        return ToolFailure(error='Failed to serialize global state')


async def get_global_state_key(key: str) -> Any | ToolFailure:
    """Return one global-state value, or a failure if it is absent."""
    value = await asyncio.to_thread(GLOBAL_STATE.get, key)
    if value is None:
        return ToolFailure(
            error='Key not found in global state', details={'key': key}
        )
    try:
        return await asyncio.to_thread(normalize_types, value)
    except RuntimeError:
        return ToolFailure(
            error='Failed to serialize global state value',
            details={'key': key},
        )


async def set_global_state(
    context: LiveContext, content: dict[str, Any]
) -> dict[str, Any] | ToolFailure:
    """Merge a mapping into the global state (existing keys overwritten)."""
    if context.read_only:
        return read_only_failure({})
    await asyncio.to_thread(GLOBAL_STATE.update, content)
    return {'updated': sorted(content)}


async def delete_global_state_key(
    context: LiveContext, key: str
) -> dict[str, Any] | ToolFailure:
    """Remove one key from the global state (no-op if absent)."""
    if context.read_only:
        return read_only_failure({'key': key})
    await asyncio.to_thread(GLOBAL_STATE.pop, key)
    return {'deleted': key}


async def clear_global_state(
    context: LiveContext,
) -> dict[str, Any] | ToolFailure:
    """Remove every key from the global state."""
    if context.read_only:
        return read_only_failure({})
    await asyncio.to_thread(GLOBAL_STATE.clear)
    return {'cleared': True}


def register(mcp: FastMCP, context: LiveContext, *, transport: str) -> None:
    """Register global-state tools on the server."""

    @mcp.tool(name='get_global_state')
    async def _get_global_state_tool() -> dict[str, Any] | ToolFailure:
        """Return the shared global state of running generators.

        The ``globals`` state is shared across every event plugin in
        the process; use it to inspect cross-generator coordination
        state.

        Returns
        -------
        dict[str, Any] | ToolFailure
            The global state as a JSON-able dict (empty if unset), or a
            structured failure if it cannot be serialized. Does not
            raise.

        """
        return observe_failure(
            await get_global_state(),
            mcp_tool='get_global_state',
            mcp_transport=transport,
        )

    @mcp.tool(name='get_global_state_key')
    async def _get_global_state_key_tool(
        key: str,
    ) -> Any | ToolFailure:
        """Return one value from the shared global state.

        Parameters
        ----------
        key : str
            Key to read.

        Returns
        -------
        Any | ToolFailure
            The JSON-able value, or a structured failure if the key is
            absent. Does not raise.

        """
        return observe_failure(
            await get_global_state_key(key),
            mcp_tool='get_global_state_key',
            mcp_transport=transport,
        )

    @mcp.tool(name='set_global_state')
    async def _set_global_state_tool(
        content: dict[str, Any],
    ) -> dict[str, Any] | ToolFailure:
        """Merge a mapping into the shared global state.

        Existing keys are overwritten; keys not in ``content`` are
        left untouched. Blocked when the server is read-only.

        Parameters
        ----------
        content : dict[str, Any]
            Keys and values to set.

        Returns
        -------
        dict[str, Any] | ToolFailure
            ``{'updated': [keys]}``, or a structured failure if the
            server is read-only. Does not raise.

        """
        return observe_failure(
            await set_global_state(context, content),
            mcp_tool='set_global_state',
            mcp_transport=transport,
        )

    @mcp.tool(name='delete_global_state_key')
    async def _delete_global_state_key_tool(
        key: str,
    ) -> dict[str, Any] | ToolFailure:
        """Remove one key from the shared global state.

        A no-op if the key is absent. Blocked when the server is
        read-only.

        Parameters
        ----------
        key : str
            Key to remove.

        Returns
        -------
        dict[str, Any] | ToolFailure
            ``{'deleted': key}``, or a structured failure if the server
            is read-only. Does not raise.

        """
        return observe_failure(
            await delete_global_state_key(context, key),
            mcp_tool='delete_global_state_key',
            mcp_transport=transport,
        )

    @mcp.tool(name='clear_global_state')
    async def _clear_global_state_tool() -> dict[str, Any] | ToolFailure:
        """Remove every key from the shared global state.

        Blocked when the server is read-only.

        Returns
        -------
        dict[str, Any] | ToolFailure
            ``{'cleared': True}``, or a structured failure if the server
            is read-only. Does not raise.

        """
        return observe_failure(
            await clear_global_state(context),
            mcp_tool='clear_global_state',
            mcp_transport=transport,
        )
