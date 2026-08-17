"""Instance-control tools (HTTP transport only).

Update the running instance's settings file and control its lifecycle.
These delegate to the instance hooks and the shared settings writer;
they hold no logic beyond merging the settings patch and refusing to
change credentials.
"""

import asyncio
from typing import Any

from mcp.server.fastmcp import FastMCP
from pydantic import ValidationError

from eventum.app.models.settings import Settings, write_settings
from eventum.logging.channels import CHANNEL_MAIN, InstanceChannel
from eventum.logging.file_paths import construct_channel_logfile_path
from eventum.mcp.context import LiveContext
from eventum.mcp.errors import (
    ToolFailure,
    read_only_failure,
    scrub_log_line,
    scrub_message,
)
from eventum.mcp.log_tail import (
    DEFAULT_LOG_LINES,
    MAX_LOG_LINES,
    tail_lines,
)
from eventum.mcp.observability import observe_failure
from eventum.utils.validation_prettier import prettify_validation_errors


def _deep_merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge ``patch`` over ``base``, returning a new dict."""
    merged = dict(base)
    for key, value in patch.items():
        current = merged.get(key)
        if isinstance(value, dict) and isinstance(current, dict):
            merged[key] = _deep_merge(current, value)
        else:
            merged[key] = value
    return merged


async def update_settings(
    context: LiveContext, patch: dict[str, Any]
) -> dict[str, Any] | ToolFailure:
    """Merge a patch into the settings file after validating it.

    ``patch`` is deep-merged over the running settings, validated, and
    written. Changing ``server.auth`` is refused. Takes effect on the
    next restart.
    """
    if context.read_only:
        return read_only_failure({})

    server_patch = patch.get('server')
    if isinstance(server_patch, dict) and 'auth' in server_patch:
        return ToolFailure(
            error='Changing auth credentials over MCP is not allowed',
        )

    merged = _deep_merge(context.settings.model_dump(mode='json'), patch)

    try:
        new_settings = Settings.model_validate(merged)
    except ValidationError as e:
        return ToolFailure(
            error='Invalid settings',
            details={
                'reason': scrub_message(
                    prettify_validation_errors(e.errors()),
                    context.generators_dir,
                ),
            },
        )

    try:
        path = await asyncio.to_thread(context.hooks['get_settings_file_path'])
    except Exception:  # noqa: BLE001 - hook may raise anything; no leak
        return ToolFailure(error='Failed to resolve the settings file path')

    try:
        await asyncio.to_thread(write_settings, new_settings, path)
    except OSError:
        return ToolFailure(error='Failed to write the settings file')

    return {'updated': True}


async def stop_instance(
    context: LiveContext,
) -> dict[str, Any] | ToolFailure:
    """Stop the running instance (terminates this MCP endpoint too)."""
    if context.read_only:
        return read_only_failure({})
    try:
        await asyncio.to_thread(context.hooks['terminate'])
    except Exception:  # noqa: BLE001 - hook may raise anything; no leak
        return ToolFailure(error='Failed to stop the instance')
    return {'stopping': True}


async def restart_instance(
    context: LiveContext,
) -> dict[str, Any] | ToolFailure:
    """Restart the running instance (briefly drops this MCP endpoint)."""
    if context.read_only:
        return read_only_failure({})
    try:
        await asyncio.to_thread(context.hooks['restart'])
    except Exception:  # noqa: BLE001 - hook may raise anything; no leak
        return ToolFailure(error='Failed to restart the instance')
    return {'restarting': True}


async def get_instance_logs(
    context: LiveContext,
    channel: InstanceChannel = CHANNEL_MAIN,
    lines: int = DEFAULT_LOG_LINES,
) -> dict[str, Any] | ToolFailure:
    """Return the scrubbed tail of one instance log channel.

    Reads the log file of the channel, keeps the last ``lines``
    entries, and scrubs each: absolute paths are relativized and the
    configured server password is redacted, since a channel carries the
    settings of the instance.
    """
    count = max(1, min(lines, MAX_LOG_LINES))

    def _read() -> dict[str, Any] | ToolFailure:
        path = construct_channel_logfile_path(
            format=context.log_format,
            logs_dir=context.logs_dir,
            channel=channel,
        )
        if not path.is_file():
            return {'channel': channel, 'lines': []}

        try:
            raw = tail_lines(path, count)
        except OSError, ValueError:
            return ToolFailure(
                error='Failed to read logs',
                details={'channel': channel},
            )

        scrubbed = [
            scrub_log_line(
                line,
                context.generators_dir,
                context.logs_dir,
                [context.settings.server.auth.password],
            )
            for line in raw
        ]

        return {'channel': channel, 'lines': scrubbed}

    return await asyncio.to_thread(_read)


def register(mcp: FastMCP, context: LiveContext, *, transport: str) -> None:
    """Register instance-control tools on the server."""

    @mcp.tool(name='get_instance_logs')
    async def _get_instance_logs_tool(
        channel: InstanceChannel = CHANNEL_MAIN,
        lines: int = DEFAULT_LOG_LINES,
    ) -> dict[str, Any] | ToolFailure:
        """Return the scrubbed tail of one instance log channel.

        Use it to diagnose the instance itself rather than a single
        generator: `main` carries its startup and shutdown, `server`
        the API and the HTTP server, `server_access` the requests they
        served, `mcp` this server. Absolute paths are stripped and the
        server password redacted before the lines are returned.

        Parameters
        ----------
        channel : InstanceChannel, default 'main'
            Channel to read.

        lines : int, default 200
            Number of trailing log lines to return (capped at 1000).

        Returns
        -------
        dict[str, Any] | ToolFailure
            ``{'channel', 'lines'}`` with the scrubbed tail, the lines
            empty when the channel has logged nothing. Does not raise.

        """
        return observe_failure(
            await get_instance_logs(context, channel, lines),
            mcp_tool='get_instance_logs',
            mcp_transport=transport,
        )

    @mcp.tool(name='update_settings')
    async def _update_settings_tool(
        patch: dict[str, Any],
    ) -> dict[str, Any] | ToolFailure:
        """Update the instance settings file with a partial patch.

        ``patch`` is a partial settings tree (only the keys you want to
        change, e.g. ``{"generation": {"timezone": "UTC"}}``); it is
        deep-merged over the current settings, validated as a whole,
        and written. The change takes effect on the next instance
        restart, not immediately. Changing ``server.auth`` is refused.
        Blocked when the server is read-only.

        Parameters
        ----------
        patch : dict[str, Any]
            Partial settings tree to merge over the current settings.

        Returns
        -------
        dict[str, Any] | ToolFailure
            ``{'updated': True}``, or a structured failure if the server
            is read-only, the patch targets auth, the merged settings
            are invalid, or the file cannot be written. Does not raise.

        """
        return observe_failure(
            await update_settings(context, patch),
            mcp_tool='update_settings',
            mcp_transport=transport,
        )

    @mcp.tool(name='stop_instance')
    async def _stop_instance_tool() -> dict[str, Any] | ToolFailure:
        """Stop the running Eventum instance.

        The MCP endpoint runs inside the instance, so a successful stop
        also terminates this connection - expect the call to end
        abruptly. Blocked when the server is read-only.

        Returns
        -------
        dict[str, Any] | ToolFailure
            ``{'stopping': True}``, or a structured failure if the
            server is read-only or termination fails. Does not raise.

        """
        return observe_failure(
            await stop_instance(context),
            mcp_tool='stop_instance',
            mcp_transport=transport,
        )

    @mcp.tool(name='restart_instance')
    async def _restart_instance_tool() -> dict[str, Any] | ToolFailure:
        """Restart the running Eventum instance.

        Use it to apply a settings change made with update_settings. The
        MCP endpoint runs inside the instance, so the connection drops
        briefly while it restarts. Blocked when the server is read-only.

        Returns
        -------
        dict[str, Any] | ToolFailure
            ``{'restarting': True}``, or a structured failure if the
            server is read-only or the restart fails. Does not raise.

        """
        return observe_failure(
            await restart_instance(context),
            mcp_tool='restart_instance',
            mcp_transport=transport,
        )
