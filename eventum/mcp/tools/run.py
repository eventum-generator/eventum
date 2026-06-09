"""One-shot generator-run tool (bounded execution to real outputs).

Runs a saved generator to its configured output plugins in sample mode.
The run is always bounded - it finishes naturally for a finite
generator, or is stopped at a timeout or event cap for an open-ended
one - so the call can never hang on an unbounded generator.
"""

import asyncio
from typing import Any

from mcp.server.fastmcp import FastMCP
from pydantic import ValidationError

from eventum.app import workspace
from eventum.app.workspace import WorkspaceError
from eventum.core.generator import Generator
from eventum.core.parameters import GeneratorParameters
from eventum.core.plugins_initializer import InitializedPlugins
from eventum.mcp.context import AuthoringContext
from eventum.mcp.errors import ToolFailure, to_tool_error
from eventum.mcp.observability import observe_failure

_CONFIG_FILENAME = 'generator.yml'
_DEFAULT_TIMEOUT = 30.0
_MAX_TIMEOUT = 300.0
_POLL_INTERVAL = 0.05


def _output_counts(plugins: InitializedPlugins | None) -> tuple[int, int]:
    """Return (written, failed) summed across the output plugins.

    The executor mutates the plugin instances in place, so a reference
    captured while the generator is running still reflects the final
    counts after the run ends and the generator releases its own.
    """
    if plugins is None:
        return 0, 0
    written = sum(p.written for p in plugins.output)
    failed = sum(p.write_failed + p.format_failed for p in plugins.output)
    return written, failed


async def _await_run(
    generator: Generator,
    plugins: InitializedPlugins | None,
    max_events: int | None,
) -> None:
    """Wait until the run ends, returning early once max_events written."""
    while generator.is_initializing or generator.is_running:
        if max_events is not None:
            written, _ = _output_counts(plugins)
            if written >= max_events:
                return
        await asyncio.sleep(_POLL_INTERVAL)


async def run_generator(  # noqa: PLR0913 - context is a DI seam; 5 tool params
    context: AuthoringContext,
    name: str,
    *,
    timeout_seconds: float = _DEFAULT_TIMEOUT,
    max_events: int | None = None,
    skip_past: bool = True,
    params: dict[str, Any] | None = None,
) -> dict[str, Any] | ToolFailure:
    """Run a generator to its configured outputs, bounded and safe.

    Runs in sample mode (no wall-clock waiting) and always terminates:
    naturally for a finite generator, or on the timeout / max_events
    bound for an open-ended one. Writes real events to the generator's
    configured output plugins, so it is a write operation.
    """
    if context.read_only:
        return ToolFailure(error='Server is read-only', details={'name': name})

    if await asyncio.to_thread(context.is_live_managed, name):
        return ToolFailure(
            error=(
                'Generator is managed live; start it with start_generator '
                'instead'
            ),
            details={'name': name},
        )

    try:
        gen_dir = workspace.resolve_generator_dir(context.generators_dir, name)
    except WorkspaceError as e:
        return to_tool_error(e, context.generators_dir)

    try:
        run_params = GeneratorParameters(
            id=name,
            path=gen_dir / _CONFIG_FILENAME,
            params=params or {},
            live_mode=False,
            skip_past=skip_past,
        )
    except ValidationError:
        return ToolFailure(
            error='Invalid run parameters', details={'name': name}
        )

    if max_events is not None and max_events < 1:
        max_events = None

    bounded = max(_POLL_INTERVAL, min(timeout_seconds, _MAX_TIMEOUT))
    generator = Generator(run_params)

    started = await asyncio.to_thread(generator.start)
    if not started:
        return ToolFailure(
            error='Generator failed to start; check its logs',
            details={'name': name},
        )

    # Capture a live reference to the plugin instances while they
    # exist. The generator nulls its own reference on completion, but
    # the executor keeps mutating these same objects, so this reference
    # still carries the final counts once the run ends.
    try:
        plugins: InitializedPlugins | None = generator.get_plugins_info()
    except RuntimeError:
        plugins = None

    reason: str | None = None
    try:
        await asyncio.wait_for(
            _await_run(generator, plugins, max_events), bounded
        )
    except TimeoutError:
        reason = 'timeout'

    if generator.is_running:
        await asyncio.to_thread(generator.stop)
        reason = reason or 'max_events'
    else:
        await asyncio.to_thread(generator.join)
        reason = 'completed' if generator.is_ended_up_successfully else 'error'

    written, failed = _output_counts(plugins)

    return {
        'id': name,
        'reason': reason,
        'events_written': written,
        'events_failed': failed,
    }


def register(
    mcp: FastMCP,
    context: AuthoringContext,
    *,
    transport: str,
) -> None:
    """Register the run tool on the server."""

    @mcp.tool(name='run_generator')
    async def _run_generator_tool(
        name: str,
        timeout_seconds: float = _DEFAULT_TIMEOUT,
        max_events: int | None = None,
        skip_past: bool = True,  # noqa: FBT001, FBT002
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any] | ToolFailure:
        """Run a saved generator to its configured outputs.

        Runs in sample mode and is always bounded: it finishes
        naturally for a finite generator, or stops at timeout_seconds
        (capped at 300) or after max_events events. Writes real events
        to the configured outputs, so it is a write operation, gated
        like every other write tool.

        Parameters
        ----------
        name : str
            Generator directory name.

        timeout_seconds : float, default 30.0
            Maximum seconds to run before stopping (capped at 300).

        max_events : int | None, default None
            Stop after this many written events, if set.

        skip_past : bool, default True
            Whether to skip timestamps in the past. Pass false to run a
            generator whose configured range is in the past.

        params : dict[str, Any] | None, default None
            Parameter substitutions for ``${params.*}`` tokens.

        Returns
        -------
        dict[str, Any] | ToolFailure
            ``{'id', 'reason', 'events_written', 'events_failed'}``
            where reason is completed, timeout, max_events, or error;
            or a structured failure. Does not raise.

        """
        return observe_failure(
            await run_generator(
                context,
                name,
                timeout_seconds=timeout_seconds,
                max_events=max_events,
                skip_past=skip_past,
                params=params,
            ),
            mcp_tool='run_generator',
            mcp_transport=transport,
        )
