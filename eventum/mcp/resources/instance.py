"""Instance resources (HTTP transport only).

Expose the running instance's host info and its settings. The settings
view is scrubbed: auth credentials are redacted and absolute paths are
reduced to file names, so neither a credential nor the host filesystem
layout reaches the agent.
"""

import asyncio
import json
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from eventum.app.models.instance import InstanceInfo
from eventum.app.models.settings import Settings
from eventum.mcp.context import LiveContext

_REDACTED = '[redacted]'


def _basename(value: Any) -> Any:
    """Reduce a non-empty path-like string to its final component."""
    if isinstance(value, str) and value:
        return Path(value).name
    return value


def safe_settings_view(settings: Settings) -> dict[str, Any]:
    """Return a settings dump safe to expose to an agent.

    Auth credentials are redacted and every absolute path (the
    ``path.*`` and ``server.ssl.*`` fields) is reduced to its final
    component, so no credential and no host filesystem layout reach
    the agent.

    Parameters
    ----------
    settings : Settings
        Running instance settings.

    Returns
    -------
    dict[str, Any]
        Scrubbed settings tree.

    """
    dump = settings.model_dump(mode='json')

    server = dump.get('server')
    if isinstance(server, dict):
        auth = server.get('auth')
        if isinstance(auth, dict):
            server['auth'] = dict.fromkeys(auth, _REDACTED)
        ssl = server.get('ssl')
        if isinstance(ssl, dict):
            for key in ('ca_cert', 'cert', 'cert_key'):
                if key in ssl:
                    ssl[key] = _basename(ssl[key])

    path = dump.get('path')
    if isinstance(path, dict):
        for key, value in path.items():
            path[key] = _basename(value)

    return dump


def register(mcp: FastMCP, context: LiveContext) -> None:
    """Register the instance info and settings resources."""

    @mcp.resource(
        'eventum://instance/info',
        name='Instance info',
        description=(
            'Version, runtime, and host metrics of the running instance.'
        ),
        mime_type='application/json',
    )
    async def instance_info() -> str:
        # InstanceInfo reads host metrics via blocking syscalls.
        info = await asyncio.to_thread(InstanceInfo)
        return info.model_dump_json(indent=2)

    @mcp.resource(
        'eventum://instance/settings',
        name='Instance settings',
        description=(
            'The running instance settings, with auth credentials '
            'redacted and absolute paths reduced to file names.'
        ),
        mime_type='application/json',
    )
    def instance_settings() -> str:
        return json.dumps(safe_settings_view(context.settings), indent=2)
