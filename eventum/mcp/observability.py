"""Observability helpers for the MCP adapter boundary.

Centralises structured logging so every transport records a forwarded
tool failure with the same fields. Successes are not logged - tool
calls are a hot path and the agent already receives the result.
"""

from typing import TypeVar

import structlog

from eventum.mcp.errors import ToolFailure

logger = structlog.stdlib.get_logger()

T = TypeVar('T')


def observe_failure(
    result: T,
    *,
    mcp_tool: str,
    mcp_transport: str,
) -> T:
    """Log the result if it is a tool failure; return it unchanged.

    Parameters
    ----------
    result : T
        A tool's return value (a JSON-serialisable value or a
        ``ToolFailure``).

    mcp_tool : str
        Name of the tool that produced ``result``.

    mcp_transport : str
        Transport the tool ran under (``'stdio'`` or ``'http'``).

    Returns
    -------
    T
        ``result`` unchanged.

    """
    if isinstance(result, ToolFailure):
        logger.warning(
            'MCP tool returned a failure',
            mcp_tool=mcp_tool,
            mcp_transport=mcp_transport,
            reason=result.error,
        )
    return result
