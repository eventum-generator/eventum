"""Live generator-management tools (HTTP transport only)."""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from eventum.app.manager import ManagingError
from eventum.app.startup import (
    StartupError,
    StartupGeneratorParameters,
    StartupNotFoundError,
)
from eventum.core.generator import Generator
from eventum.logging.file_paths import construct_generator_logfile_path
from eventum.mcp.context import LiveContext
from eventum.mcp.errors import ToolFailure, scrub_log_line, to_tool_error
from eventum.mcp.observability import observe_failure
from eventum.security.manage import get_secret_values_for_scrubbing

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
    if not config_path.is_file():
        return ToolFailure(
            error='Generator config not found',
            details={'name': name},
        )
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


async def unregister_generator(
    context: LiveContext,
    name: str,
) -> dict[str, Any] | ToolFailure:
    """Stop and unregister a generator, dropping its startup entry.

    The inverse of register_generator. Removes the generator from the
    runtime (stopping it if running) and from the startup file, so it
    will not be reloaded. Tolerates a generator that exists in only one
    of the two; fails only if it is absent from both. If the runtime
    removal succeeds but the startup file cannot be rewritten, that
    error is reported and the runtime removal stands.
    """
    if context.read_only:
        return ToolFailure(error='Server is read-only', details={'name': name})

    removed_runtime = True
    try:
        await asyncio.to_thread(context.manager.remove, name)
    except ManagingError:
        removed_runtime = False

    try:
        await asyncio.to_thread(context.startup.delete, name)
    except StartupNotFoundError:
        if not removed_runtime:
            return ToolFailure(
                error='Generator not found',
                details={'name': name},
            )
    except StartupError as e:
        return to_tool_error(e, context.generators_dir)

    return {'id': name, 'unregistered': True}


_DEFAULT_LOG_LINES = 200
_MAX_LOG_LINES = 1000
_TAIL_MAX_BYTES = 65536


def _tail_lines(path: Path, count: int) -> list[str]:
    """Return the last ``count`` lines, reading a bounded tail."""
    size = path.stat().st_size
    read = min(size, _TAIL_MAX_BYTES)
    with path.open('rb') as f:
        f.seek(size - read)
        data = f.read()
    lines = data.decode('utf-8', errors='replace').splitlines()
    if read < size and lines:
        lines = lines[1:]  # drop the partial first line
    return lines[-count:]


async def get_generator_logs(
    context: LiveContext,
    generator_id: str,
    lines: int = _DEFAULT_LOG_LINES,
) -> dict[str, Any] | ToolFailure:
    """Return the scrubbed tail of a managed generator's log file.

    Reads the per-generator log, keeps the last ``lines`` entries, and
    scrubs each: absolute paths are relativized and configured secret
    values are redacted. Restricted to currently managed generators so
    the id cannot be used to read arbitrary files.
    """
    count = max(1, min(lines, _MAX_LOG_LINES))

    def _read() -> dict[str, Any] | ToolFailure:
        if generator_id not in context.manager.generator_ids:
            return ToolFailure(
                error='Generator not found',
                details={'id': generator_id},
            )
        try:
            path = construct_generator_logfile_path(
                format=context.log_format,
                logs_dir=context.logs_dir,
                generator_id=generator_id,
            )
            # Defense in depth: the id is already constrained to a
            # managed generator, but reject a path escaping the logs dir.
            if not path.resolve().is_relative_to(context.logs_dir.resolve()):
                return ToolFailure(
                    error='Generator not found',
                    details={'id': generator_id},
                )
            if not path.is_file():
                return {'id': generator_id, 'lines': []}
            raw = _tail_lines(path, count)
        except OSError, ValueError:
            return ToolFailure(
                error='Failed to read logs',
                details={'id': generator_id},
            )

        redact = get_secret_values_for_scrubbing()
        scrubbed = [
            scrub_log_line(
                line, context.generators_dir, context.logs_dir, redact
            )
            for line in raw
        ]
        return {'id': generator_id, 'lines': scrubbed}

    return await asyncio.to_thread(_read)


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

    @mcp.tool(name='unregister_generator')
    async def _unregister_generator_tool(
        name: str,
    ) -> dict[str, Any] | ToolFailure:
        """Stop a generator and drop it from runtime and startup.

        The inverse of register_generator; run it before
        delete_generator to fully retire a generator. Blocked when the
        server is read-only.
        """
        return observe_failure(
            await unregister_generator(context, name),
            mcp_tool='unregister_generator',
            mcp_transport=transport,
        )

    @mcp.tool(name='get_generator_logs')
    async def _get_generator_logs_tool(
        generator_id: str,
        lines: int = _DEFAULT_LOG_LINES,
    ) -> dict[str, Any] | ToolFailure:
        """Return the scrubbed tail of a managed generator's log file.

        Use it to diagnose why a generator failed or what it is doing.
        Absolute paths are stripped and configured secrets redacted
        before the lines are returned.

        Parameters
        ----------
        generator_id : str
            Id of a managed generator.

        lines : int, default 200
            Number of trailing log lines to return (capped at 1000).

        Returns
        -------
        dict[str, Any] | ToolFailure
            ``{'id', 'lines'}`` with the scrubbed tail, or a structured
            failure if the generator is unknown. Does not raise.

        """
        return observe_failure(
            await get_generator_logs(context, generator_id, lines),
            mcp_tool='get_generator_logs',
            mcp_transport=transport,
        )
