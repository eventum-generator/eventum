"""Live generator-management tools (HTTP transport only)."""

import asyncio
from datetime import datetime
from typing import Any

from mcp.server.fastmcp import FastMCP

from eventum.app.manager import ManagingError
from eventum.app.startup import StartupError, StartupGeneratorParameters
from eventum.core.generator import Generator
from eventum.mcp.context import LiveContext
from eventum.mcp.errors import ToolFailure, to_tool_error
from eventum.mcp.observability import observe_failure

_CONFIG_FILENAME = 'generator.yml'


def _isoformat(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _status_dict(generator: Generator) -> dict[str, Any]:
    return {
        'id': generator.params.id,
        'is_initializing': generator.is_initializing,
        'is_running': generator.is_running,
        'is_ended_up': generator.is_ended_up,
        'is_ended_up_successfully': generator.is_ended_up_successfully,
        'is_stopping': generator.is_stopping,
        'start_time': _isoformat(generator.start_time),
    }


async def list_generators_live(
    context: LiveContext,
) -> list[dict[str, Any]]:
    """Return a status dict for every managed generator."""

    def _collect() -> list[dict[str, Any]]:
        statuses: list[dict[str, Any]] = []
        for generator_id in context.manager.generator_ids:
            try:
                generator = context.manager.get_generator(generator_id)
            except ManagingError:
                continue
            statuses.append(_status_dict(generator))
        return statuses

    return await asyncio.to_thread(_collect)


async def get_generator_status(
    context: LiveContext, generator_id: str
) -> dict[str, Any] | ToolFailure:
    """Return the status of one managed generator."""
    try:
        generator = await asyncio.to_thread(
            context.manager.get_generator, generator_id
        )
    except ManagingError as e:
        return ToolFailure(error=str(e), details={'id': generator_id})
    return _status_dict(generator)


async def start_generator(
    context: LiveContext, generator_id: str
) -> dict[str, Any] | ToolFailure:
    """Start a managed generator (idempotent)."""
    if context.read_only:
        return ToolFailure(
            error='Server is read-only', details={'id': generator_id}
        )
    try:
        started = await asyncio.to_thread(context.manager.start, generator_id)
    except ManagingError as e:
        return ToolFailure(error=str(e), details={'id': generator_id})
    return {'id': generator_id, 'started': started}


async def stop_generator(
    context: LiveContext, generator_id: str
) -> dict[str, Any] | ToolFailure:
    """Stop a managed generator."""
    if context.read_only:
        return ToolFailure(
            error='Server is read-only', details={'id': generator_id}
        )
    try:
        await asyncio.to_thread(context.manager.stop, generator_id)
    except ManagingError as e:
        return ToolFailure(error=str(e), details={'id': generator_id})
    return {'id': generator_id, 'stopped': True}


async def register_generator(
    context: LiveContext,
    name: str,
    params: dict[str, Any] | None = None,
) -> dict[str, Any] | ToolFailure:
    """Register an authored generator: add it live and persist it."""
    if context.read_only:
        return ToolFailure(error='Server is read-only', details={'name': name})
    config_path = context.generators_dir / name / _CONFIG_FILENAME
    generator_params = StartupGeneratorParameters(
        **context.generation.model_dump(),
        id=name,
        path=config_path,
        params=params or {},
    )
    try:
        await asyncio.to_thread(context.manager.add, generator_params)
    except ManagingError as e:
        return ToolFailure(error=str(e), details={'name': name})
    try:
        await asyncio.to_thread(context.startup.add, generator_params)
    except StartupError as e:
        await asyncio.to_thread(context.manager.remove, name)
        return to_tool_error(e, context.generators_dir)
    return {'id': name, 'registered': True}


def register(mcp: FastMCP, context: LiveContext, *, transport: str) -> None:
    """Register live-management tools on the server."""

    @mcp.tool(name='list_generators_live')
    async def _list_generators_live_tool() -> list[dict[str, Any]]:
        """List every managed generator with its status."""
        return await list_generators_live(context)

    @mcp.tool(name='get_generator_status')
    async def _get_generator_status_tool(
        generator_id: str,
    ) -> dict[str, Any] | ToolFailure:
        """Return the status of a managed generator by id."""
        return observe_failure(
            await get_generator_status(context, generator_id),
            mcp_tool='get_generator_status',
            mcp_transport=transport,
        )

    @mcp.tool(name='start_generator')
    async def _start_generator_tool(
        generator_id: str,
    ) -> dict[str, Any] | ToolFailure:
        """Start a managed generator (no-op if already running)."""
        return observe_failure(
            await start_generator(context, generator_id),
            mcp_tool='start_generator',
            mcp_transport=transport,
        )

    @mcp.tool(name='stop_generator')
    async def _stop_generator_tool(
        generator_id: str,
    ) -> dict[str, Any] | ToolFailure:
        """Stop a managed generator."""
        return observe_failure(
            await stop_generator(context, generator_id),
            mcp_tool='stop_generator',
            mcp_transport=transport,
        )

    @mcp.tool(name='register_generator')
    async def _register_generator_tool(
        name: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any] | ToolFailure:
        """Add an authored generator live and persist it to startup."""
        return observe_failure(
            await register_generator(context, name, params),
            mcp_tool='register_generator',
            mcp_transport=transport,
        )
