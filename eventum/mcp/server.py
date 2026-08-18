"""FastMCP server factory.

The only FastMCP-aware module besides the transport roots. Wires the
tool, resource, and prompt registrations onto one server bound to an
injected context.
"""

from mcp.server.fastmcp import FastMCP

from eventum import __version__ as _eventum_version
from eventum.mcp.context import AuthoringContext
from eventum.mcp.prompts import authoring as authoring_prompts
from eventum.mcp.resources import examples as examples_resource
from eventum.mcp.resources import schema as schema_resource
from eventum.mcp.resources import templating as templating_resource
from eventum.mcp.resources import workspace as workspace_resource
from eventum.mcp.tools import archives as archive_tools
from eventum.mcp.tools import discovery
from eventum.mcp.tools import formatters as fmt_tools
from eventum.mcp.tools import preview as preview_tools
from eventum.mcp.tools import renaming as renaming_tools
from eventum.mcp.tools import run as run_tools
from eventum.mcp.tools import samples as sample_tools
from eventum.mcp.tools import secrets as secrets_tools
from eventum.mcp.tools import workspace_files as ws_tools

_INSTRUCTIONS = (
    'Eventum MCP server. Author, inspect, and operate synthetic data '
    'generators: discover plugins and their config schemas, read the '
    'template-context reference, the generator schema, and worked '
    'examples, then write, validate, preview, and run generators, and '
    'move a whole generator project in or out as a ZIP archive. Over '
    'HTTP it also manages running generators - register, start, stop, '
    'unregister, rename, and read their logs - groups them into '
    'scenarios, renames a project or a scenario, '
    'reads and edits the shared global state, and reads or updates the '
    'instance settings and lifecycle. Write tools are gated on a '
    'writable server: the HTTP mount is read-only unless '
    '`server.mcp.allow_write` is enabled, and the stdio server is '
    'writable unless started with `--read-only`. Tool failures '
    'are returned in-band as an object with an `error` field, not as a '
    'protocol error - check for it before using a result. Secret values '
    'never cross the boundary - list or rename secret names only, and '
    'direct the user to the eventum-keyring CLI to add or read a value.'
)

_REST_API_NOTE = (
    'This server also exposes a REST API at `/api` (OpenAPI schema at '
    '`/api/openapi.json`, Swagger UI at `/api/swagger`) behind the same '
    'credentials as this MCP endpoint. When an operation has no MCP '
    'tool - for example uploading a large sample file, or moving a '
    'project archive above the inline transfer limit - read that '
    'schema and call the REST API directly.'
)


def build_server(
    context: AuthoringContext,
    *,
    transport: str = 'stdio',
    live: bool = False,
) -> FastMCP:
    """Build a FastMCP server bound to the given context.

    Parameters
    ----------
    context : AuthoringContext
        Authoring context injected into each tool. When ``live`` is
        True it must also be a ``LiveContext``.

    transport : str, default 'stdio'
        Transport label, forwarded to tool failure logging.

    live : bool, default False
        Whether to also register live generator-management tools.
        Requires ``context`` to be a ``LiveContext``.

    Returns
    -------
    FastMCP
        Server with discovery, formatter, sample, secret-listing,
        workspace, archive, validate/preview, and run tools; the
        templating-reference, generator-schema, examples, and
        workspace-configs resources; the authoring prompts; and,
        when ``live`` is set, the live generator-management, scenario,
        global-state, instance-control, and rename tools; the instance
        info/settings resources; and REST-API-fallback guidance in the
        server instructions.

    """
    instructions = (
        f'{_INSTRUCTIONS} {_REST_API_NOTE}' if live else _INSTRUCTIONS
    )
    mcp = FastMCP('eventum', instructions=instructions)
    mcp._mcp_server.version = _eventum_version  # noqa: SLF001

    discovery.register(mcp, context, transport=transport)
    fmt_tools.register(mcp, context, transport=transport)
    sample_tools.register(mcp, context, transport=transport)
    secrets_tools.register(mcp, context, transport=transport)
    ws_tools.register(mcp, context, transport=transport)
    archive_tools.register(mcp, context, transport=transport)
    preview_tools.register(mcp, context, transport=transport)
    run_tools.register(mcp, context, transport=transport)

    templating_resource.register(mcp)
    schema_resource.register(mcp)
    examples_resource.register(mcp)
    workspace_resource.register(mcp, context)

    authoring_prompts.register(mcp)

    if live:
        from eventum.mcp.context import LiveContext
        from eventum.mcp.prompts import operations as operations_prompts
        from eventum.mcp.resources import instance as instance_resource
        from eventum.mcp.tools import global_state as global_state_tools
        from eventum.mcp.tools import instance as instance_tools
        from eventum.mcp.tools import live as live_tools
        from eventum.mcp.tools import scenarios as scenario_tools

        if not isinstance(context, LiveContext):
            msg = 'live mode requires a LiveContext'
            raise TypeError(msg)
        live_tools.register(mcp, context, transport=transport)
        scenario_tools.register(mcp, context, transport=transport)
        global_state_tools.register(mcp, context, transport=transport)
        instance_tools.register(mcp, context, transport=transport)
        renaming_tools.register(mcp, context, transport=transport)
        instance_resource.register(mcp, context)
        operations_prompts.register(mcp)

    return mcp
