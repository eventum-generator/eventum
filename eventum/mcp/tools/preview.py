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
import contextlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from eventum.app import workspace
from eventum.app.workspace import WorkspaceError
from eventum.core import preview as core_preview
from eventum.core.config_loader import ConfigurationLoadError, extract_secrets
from eventum.core.plugins_initializer import InitializationError
from eventum.mcp.context import AuthoringContext
from eventum.mcp.errors import ToolFailure, scrub_context, to_tool_error
from eventum.mcp.observability import observe_failure
from eventum.security.manage import get_secret

_CONFIG_FILENAME = 'generator.yml'


def _read_secret_values(cfg_path: Path) -> list[str]:
    """Return resolved values for secrets referenced in the config file.

    Reads the raw config text, extracts secret names via
    ``extract_secrets``, then resolves each with ``get_secret``.
    Secrets that cannot be resolved (missing, keyring error) are
    silently skipped - this is best-effort redaction; a missing secret
    value means the corresponding token was never substituted and
    therefore cannot appear in error text anyway.

    Parameters
    ----------
    cfg_path : Path
        Absolute path to the generator config file.

    Returns
    -------
    list[str]
        Resolved secret values to redact. May be empty.

    """
    try:
        text = cfg_path.read_text()
    except OSError:
        return []

    names = extract_secrets(text)
    values: list[str] = []

    for name in names:
        with contextlib.suppress(ValueError, OSError):
            values.append(get_secret(name))

    return values


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
    ``<generators_dir>/<name>/generator.yml`` and initialises all
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

    try:
        gen_dir = workspace.resolve_generator_dir(context.generators_dir, name)
    except WorkspaceError as e:
        return to_tool_error(e, context.generators_dir)

    cfg_path = gen_dir / _CONFIG_FILENAME
    redact_values = _read_secret_values(cfg_path)

    try:
        await asyncio.to_thread(
            core_preview.validate_generator, cfg_path, resolved_params
        )
    except (ConfigurationLoadError, InitializationError) as e:
        return to_tool_error(e, context.generators_dir, redact_values)

    return {'valid': True}


async def preview_timestamps(  # noqa: PLR0913
    context: AuthoringContext,
    name: str,
    size: int = 100,
    *,
    skip_past: bool = True,
    span: str | None = None,
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
        Maximum number of timestamps to generate.

    skip_past : bool, default True
        Whether to skip timestamps that are in the past. Pass ``False``
        for generators with a static date range in the past.

    span : str | None, default None
        Histogram bucket width as an ISO 8601 duration string (e.g.
        ``'PT1H'`` for 1 hour). ``None`` triggers auto-span selection.
        Duration parsing is not yet implemented; callers should omit
        this parameter for now.

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
    resolved_params = params or {}

    try:
        gen_dir = workspace.resolve_generator_dir(context.generators_dir, name)
    except WorkspaceError as e:
        return to_tool_error(e, context.generators_dir)

    cfg_path = gen_dir / _CONFIG_FILENAME
    redact_values = _read_secret_values(cfg_path)

    # span string -> timedelta conversion is not implemented yet;
    # the parameter is accepted for forward compatibility but ignored.
    _ = span
    span_td: timedelta | None = None

    try:
        agg = await asyncio.to_thread(
            core_preview.aggregate_sample_timestamps,
            cfg_path,
            size,
            resolved_params,
            skip_past=skip_past,
            span=span_td,
        )
    except (ConfigurationLoadError, InitializationError) as e:
        return to_tool_error(e, context.generators_dir, redact_values)

    return _serialize_timestamps_aggregate(agg)


async def preview_events(
    context: AuthoringContext,
    name: str,
    count: int = 10,
    params: dict[str, Any] | None = None,
    *,
    skip_past: bool = True,
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
        Maximum number of events to produce.

    params : dict[str, Any] | None, default None
        Parameter substitutions for ``${params.*}`` tokens.

    skip_past : bool, default True
        Whether to skip timestamps that are in the past. Pass ``False``
        for generators with a static date range in the past.

    Returns
    -------
    dict[str, Any]
        ``events`` (list of strings), ``errors`` (list of per-index
        error dicts with ``index``, ``message``, and ``context`` keys),
        and ``exhausted`` (bool).

    ToolFailure
        Structured, path-safe, secret-redacted failure. Does not raise.

    """
    resolved_params = params or {}

    try:
        gen_dir = workspace.resolve_generator_dir(context.generators_dir, name)
    except WorkspaceError as e:
        return to_tool_error(e, context.generators_dir)

    cfg_path = gen_dir / _CONFIG_FILENAME
    redact_values = _read_secret_values(cfg_path)

    try:
        sample = await asyncio.to_thread(
            core_preview.produce_sample_events,
            cfg_path,
            count,
            resolved_params,
            skip_past=skip_past,
        )
    except (ConfigurationLoadError, InitializationError) as e:
        return to_tool_error(e, context.generators_dir, redact_values)

    errors = [
        {
            'index': e.index,
            'message': e.message,
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
        span: str | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any] | ToolFailure:
        """Generate a histogram of input timestamps for a saved generator.

        Parameters
        ----------
        name : str
            Generator directory name.

        size : int, default 100
            Maximum number of timestamps to generate.

        skip_past : bool, default True
            Whether to skip timestamps in the past. Pass ``false`` for
            generators with a static date range in the past.

        span : str | None, default None
            Histogram bucket width. ``null`` triggers auto-span
            selection. Duration parsing is not yet implemented; omit
            this parameter for now.

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
                span=span,
                params=params,
            ),
            mcp_tool='preview_timestamps',
            mcp_transport=transport,
        )

    @mcp.tool(name='preview_events')
    async def _preview_events_tool(
        name: str,
        count: int = 10,
        params: dict[str, Any] | None = None,
        skip_past: bool = True,  # noqa: FBT001, FBT002
    ) -> dict[str, Any] | ToolFailure:
        """Produce sample events from a saved generator.

        Parameters
        ----------
        name : str
            Generator directory name.

        count : int, default 10
            Maximum number of events to produce.

        params : dict[str, Any] | None, default None
            Parameter substitutions for ``${params.*}`` tokens.

        skip_past : bool, default True
            Whether to skip timestamps in the past. Pass ``false`` for
            generators with a static date range in the past.

        Returns
        -------
        dict[str, Any] | ToolFailure
            ``events`` (list of strings), ``errors`` (list of per-index
            dicts), and ``exhausted`` (bool), or a structured failure.
            Does not raise.

        """
        return observe_failure(
            await preview_events(
                context,
                name,
                count,
                params=params,
                skip_past=skip_past,
            ),
            mcp_tool='preview_events',
            mcp_transport=transport,
        )
