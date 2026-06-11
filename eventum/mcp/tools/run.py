"""One-shot generator-run tool (bounded execution to real outputs).

Runs a saved generator to its configured output plugins in sample
mode via the bounded-run application service. The run is always
bounded - it finishes naturally for a finite generator, or is stopped
at a timeout or event cap for an open-ended one - so the call can
never hang on an unbounded generator.

Security: config loading resolves ``${secrets.*}`` tokens, so load
errors may carry resolved secret values; the config's secret values
are passed as ``redact_values`` to ``to_tool_error`` so none leak
into the returned error text.
"""

import asyncio
from typing import Any

from mcp.server.fastmcp import FastMCP
from pydantic import ValidationError

from eventum.app import workspace
from eventum.app.bounded_run import run_bounded
from eventum.app.workspace import WorkspaceError
from eventum.core.config_loader import ConfigurationLoadError
from eventum.core.executor import ImproperlyConfiguredError
from eventum.core.parameters import GeneratorParameters
from eventum.core.plugins_initializer import InitializationError
from eventum.mcp.context import AuthoringContext
from eventum.mcp.errors import (
    ToolFailure,
    read_only_failure,
    to_tool_error,
)
from eventum.mcp.observability import observe_failure
from eventum.mcp.redaction import read_config_secret_values

_DEFAULT_TIMEOUT = 30.0


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
        return read_only_failure({'name': name})

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

    cfg_path = gen_dir / context.config_filename

    try:
        run_params = GeneratorParameters(
            id=name,
            path=cfg_path,
            params=params or {},
            live_mode=False,
            skip_past=skip_past,
        )
    except ValidationError:
        return ToolFailure(
            error='Invalid run parameters', details={'name': name}
        )

    redact_values = read_config_secret_values(cfg_path)

    try:
        summary = await asyncio.to_thread(
            run_bounded,
            run_params,
            timeout_seconds=timeout_seconds,
            max_events=max_events,
        )
    except (
        ConfigurationLoadError,
        InitializationError,
        ImproperlyConfiguredError,
    ) as e:
        return to_tool_error(e, context.generators_dir, redact_values)

    return {
        'id': name,
        'reason': summary.outcome,
        'events_written': summary.events_written,
        'events_failed': summary.events_failed,
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
