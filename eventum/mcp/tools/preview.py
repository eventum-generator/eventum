"""Validate and preview MCP tools.

These tools are read-only thin async wrappers over the stateless
``core.preview`` functions. Each resolves the generator config path,
offloads the sync IO-bound call to a thread, and serialises the result
to a plain JSON-able dict.

Security: config loading resolves ``${secrets.*}`` tokens. If loading
fails the resolved secret values would appear verbatim in the
``ConfigurationLoadError`` context. To prevent leakage, every error
path here extracts the secret names referenced by the config, resolves
their values, and passes them as ``redact_values`` to ``to_tool_error``
so they are replaced with ``[redacted]`` before the error is returned.
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from eventum.app import workspace
from eventum.app.workspace import WorkspaceError
from eventum.core import preview as core_preview
from eventum.core.config_loader import ConfigurationLoadError
from eventum.core.plugins_initializer import InitializationError
from eventum.mcp.context import AuthoringContext
from eventum.mcp.errors import (
    ToolFailure,
    scrub_context,
    scrub_message,
    to_tool_error,
)
from eventum.mcp.observability import observe_failure
from eventum.mcp.redaction import read_config_secret_values
from eventum.plugins.input.exceptions import PluginGenerationError


def _prepare_config(
    context: AuthoringContext,
    name: str,
) -> tuple[Path, list[str]] | ToolFailure:
    """Resolve the config path and load its secret values to redact.

    Returns a (cfg_path, redact_values) pair, or a path-safe
    ToolFailure if the generator name escapes the workspace.
    """
    try:
        gen_dir = workspace.resolve_generator_dir(context.generators_dir, name)
    except WorkspaceError as e:
        return to_tool_error(e, context.generators_dir)

    cfg_path = gen_dir / context.config_filename
    return cfg_path, read_config_secret_values(cfg_path)


def _serialize_timestamps_aggregate(
    agg: core_preview.TimestampsAggregate,
) -> dict[str, Any]:
    """Serialize a TimestampsAggregate to a plain dict.

    All ``datetime`` values are converted to ISO 8601 strings.
    ``None`` fields are preserved as ``None``.

    Parameters
    ----------
    agg : TimestampsAggregate
        Result from ``aggregate_sample_timestamps``.

    Returns
    -------
    dict[str, Any]
        JSON-serializable representation.

    """

    def iso_list(dts: list[datetime] | None) -> list[str] | None:
        if dts is None:
            return None
        return [dt.isoformat() for dt in dts]

    return {
        'total': agg.total,
        'span_edges': iso_list(agg.span_edges),
        'span_counts': agg.span_counts,
        'first': iso_list(agg.first),
        'last': iso_list(agg.last),
        'timestamps': iso_list(agg.timestamps),
    }


async def validate_generator(
    context: AuthoringContext,
    name: str,
    params: dict[str, Any] | None = None,
) -> dict[str, Any] | ToolFailure:
    """Validate a saved generator by loading and initialising every plugin.

    Loads the generator config at
    ``<generators_dir>/<name>/<config_filename>`` and initialises all
    plugins. Plugins are discarded after the call; no state is mutated.

    Parameters
    ----------
    context : AuthoringContext
        Authoring context supplying the generators directory.

    name : str
        Generator directory name, as returned by ``list_generators``.

    params : dict[str, Any] | None, default None
        Parameter substitutions for ``${params.*}`` tokens. Defaults to
        an empty dict when omitted.

    Returns
    -------
    dict[str, Any]
        ``{'valid': True}`` when all plugins initialise without error.

    ToolFailure
        Structured, path-safe, secret-redacted failure on any config or
        initialisation error. Does not raise.

    """
    resolved_params = params or {}
    prepared = _prepare_config(context, name)
    if isinstance(prepared, ToolFailure):
        return prepared
    cfg_path, redact_values = prepared

    try:
        await asyncio.to_thread(
            core_preview.validate_generator, cfg_path, resolved_params
        )
    except (ConfigurationLoadError, InitializationError) as e:
        return to_tool_error(e, context.generators_dir, redact_values)

    return {'valid': True}


async def preview_timestamps(
    context: AuthoringContext,
    name: str,
    size: int = 100,
    *,
    skip_past: bool = True,
    params: dict[str, Any] | None = None,
) -> dict[str, Any] | ToolFailure:
    """Generate a histogram of input timestamps for a saved generator.

    Loads the generator config, generates up to ``size`` timestamps from
    non-interactive input plugins, and returns them as a histogram.

    Parameters
    ----------
    context : AuthoringContext
        Authoring context supplying the generators directory.

    name : str
        Generator directory name.

    size : int, default 100
        Maximum number of timestamps to generate. Must be greater or
        equal to 1.

    skip_past : bool, default True
        Whether to skip timestamps that are in the past. Pass ``False``
        for generators with a static date range in the past.

    params : dict[str, Any] | None, default None
        Parameter substitutions for ``${params.*}`` tokens.

    Returns
    -------
    dict[str, Any]
        Histogram with keys ``total``, ``span_edges``, ``span_counts``,
        ``first``, ``last``, and ``timestamps``. Datetime values are ISO
        8601 strings.

    ToolFailure
        Structured, path-safe, secret-redacted failure. Does not raise.

    """
    if size < 1:
        return ToolFailure(
            error='Parameter `size` must be greater or equal to 1',
            details={'value': size},
        )

    resolved_params = params or {}
    prepared = _prepare_config(context, name)
    if isinstance(prepared, ToolFailure):
        return prepared
    cfg_path, redact_values = prepared

    try:
        agg = await asyncio.to_thread(
            core_preview.aggregate_sample_timestamps,
            cfg_path,
            size,
            resolved_params,
            skip_past=skip_past,
        )
    except (
        ConfigurationLoadError,
        InitializationError,
        PluginGenerationError,
    ) as e:
        return to_tool_error(e, context.generators_dir, redact_values)

    return _serialize_timestamps_aggregate(agg)


async def preview_events(
    context: AuthoringContext,
    name: str,
    count: int = 10,
    *,
    skip_past: bool = True,
    params: dict[str, Any] | None = None,
) -> dict[str, Any] | ToolFailure:
    """Produce sample events from a saved generator.

    Loads the generator config, generates up to ``count`` timestamps,
    and produces events for each one. Plugins are discarded after the
    call; no state is mutated.

    Parameters
    ----------
    context : AuthoringContext
        Authoring context supplying the generators directory.

    name : str
        Generator directory name.

    count : int, default 10
        Maximum number of input timestamps to generate. The produced
        events may exceed this count. Must be greater or equal to 1.

    skip_past : bool, default True
        Whether to skip timestamps that are in the past. Pass ``False``
        for generators with a static date range in the past.

    params : dict[str, Any] | None, default None
        Parameter substitutions for ``${params.*}`` tokens.

    Returns
    -------
    dict[str, Any]
        ``events`` (list of strings), ``errors`` (list of per-index
        error dicts with ``index``, ``message``, and ``context`` keys),
        and ``exhausted`` (bool).

    ToolFailure
        Structured, path-safe, secret-redacted failure. Does not raise.

    """
    if count < 1:
        return ToolFailure(
            error='Parameter `count` must be greater or equal to 1',
            details={'value': count},
        )

    resolved_params = params or {}
    prepared = _prepare_config(context, name)
    if isinstance(prepared, ToolFailure):
        return prepared
    cfg_path, redact_values = prepared

    try:
        sample = await asyncio.to_thread(
            core_preview.produce_sample_events,
            cfg_path,
            count,
            resolved_params,
            skip_past=skip_past,
        )
    except (
        ConfigurationLoadError,
        InitializationError,
        PluginGenerationError,
    ) as e:
        return to_tool_error(e, context.generators_dir, redact_values)

    errors = [
        {
            'index': e.index,
            'message': scrub_message(
                e.message, context.generators_dir, redact_values
            ),
            'context': scrub_context(
                e.context, context.generators_dir, redact_values
            ),
        }
        for e in sample.errors
    ]

    return {
        'events': sample.events,
        'errors': errors,
        'exhausted': sample.exhausted,
    }


def register(
    mcp: FastMCP,
    context: AuthoringContext,
    *,
    transport: str,
) -> None:
    """Register validate/preview tools on the server."""

    @mcp.tool(name='validate_generator')
    async def _validate_generator_tool(
        name: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any] | ToolFailure:
        """Validate a saved generator by loading and initialising every plugin.

        Parameters
        ----------
        name : str
            Generator directory name, as returned by ``list_generators``.

        params : dict[str, Any] | None, default None
            Parameter substitutions for ``${params.*}`` tokens.

        Returns
        -------
        dict[str, Any] | ToolFailure
            ``{'valid': True}`` on success, or a structured failure if
            the config is invalid or a plugin cannot be initialised. Does
            not raise.

        """
        return observe_failure(
            await validate_generator(context, name, params=params),
            mcp_tool='validate_generator',
            mcp_transport=transport,
        )

    @mcp.tool(name='preview_timestamps')
    async def _preview_timestamps_tool(
        name: str,
        size: int = 100,
        skip_past: bool = True,  # noqa: FBT001, FBT002
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any] | ToolFailure:
        """Generate a histogram of input timestamps for a saved generator.

        Parameters
        ----------
        name : str
            Generator directory name.

        size : int, default 100
            Maximum number of timestamps to generate. Must be greater
            or equal to 1.

        skip_past : bool, default True
            Whether to skip timestamps in the past. Pass ``false`` for
            generators with a static date range in the past.

        params : dict[str, Any] | None, default None
            Parameter substitutions for ``${params.*}`` tokens.

        Returns
        -------
        dict[str, Any] | ToolFailure
            Histogram with ``total``, ``span_edges``, ``span_counts``,
            ``first``, ``last``, and ``timestamps`` (ISO 8601 strings),
            or a structured failure. Does not raise.

        """
        return observe_failure(
            await preview_timestamps(
                context,
                name,
                size,
                skip_past=skip_past,
                params=params,
            ),
            mcp_tool='preview_timestamps',
            mcp_transport=transport,
        )

    @mcp.tool(name='preview_events')
    async def _preview_events_tool(
        name: str,
        count: int = 10,
        skip_past: bool = True,  # noqa: FBT001, FBT002
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any] | ToolFailure:
        """Produce sample events from a saved generator.

        Parameters
        ----------
        name : str
            Generator directory name.

        count : int, default 10
            Maximum number of input timestamps to generate. The
            produced events may exceed this count. Must be greater or
            equal to 1.

        skip_past : bool, default True
            Whether to skip timestamps in the past. Pass ``false`` for
            generators with a static date range in the past.

        params : dict[str, Any] | None, default None
            Parameter substitutions for ``${params.*}`` tokens.

        Returns
        -------
        dict[str, Any] | ToolFailure
            ``events`` (list of strings), ``errors`` (list of per-index
            dicts with ``index``, ``message``, and ``context``), and
            ``exhausted`` (bool); or a structured failure. Does not
            raise.

        """
        return observe_failure(
            await preview_events(
                context,
                name,
                count,
                skip_past=skip_past,
                params=params,
            ),
            mcp_tool='preview_events',
            mcp_transport=transport,
        )
