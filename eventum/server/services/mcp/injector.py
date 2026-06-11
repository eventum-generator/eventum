"""MCP HTTP service injector.

The single SDK-aware server-side module: builds the FastMCP server for
the HTTP transport, configures Streamable HTTP, gates it behind Basic
auth, registers its session manager into the server lifespan, and
mounts it. Keeping all Streamable-HTTP wiring here isolates the eventual
SDK migration to one file.
"""

from fastapi import FastAPI
from mcp.server.transport_security import TransportSecuritySettings
from starlette.requests import Request
from starlette.responses import RedirectResponse

from eventum.app.manager import GeneratorManager
from eventum.app.models.settings import Settings
from eventum.app.startup import Startup
from eventum.mcp.context import ServerLiveContext
from eventum.mcp.server import build_server
from eventum.server.exceptions import ServiceBuildingError
from eventum.server.services.mcp.auth import BasicAuthMiddleware


def inject_service(
    app: FastAPI,
    generator_manager: GeneratorManager,
    settings: Settings,
    startup: Startup,
) -> None:
    """Mount the MCP Streamable-HTTP app onto the server app.

    Parameters
    ----------
    app : FastAPI
        The server application to mount onto.

    generator_manager : GeneratorManager
        Manager of generators, exposed to the live tools.

    settings : Settings
        Resolved settings providing the generators directory, the
        ``server.mcp.*`` parameters, and the ``server.auth``
        credentials.

    startup : Startup
        Shared startup-config service, used by ``register_generator``
        to persist generators.

    Raises
    ------
    ServiceBuildingError
        If the MCP service fails to build.

    """
    try:
        context = ServerLiveContext(
            generators_dir=settings.path.generators_dir,
            read_only=not settings.server.mcp.allow_write,
            manager=generator_manager,
            startup=startup,
            generation=settings.generation,
            logs_dir=settings.path.logs,
            log_format=settings.log.format,
            config_filename=str(settings.path.generator_config_filename),
        )
        mcp = build_server(context, transport='http', live=True)

        # Configure Streamable HTTP BEFORE building the sub-app: the
        # session manager is created lazily inside streamable_http_app().
        mcp.settings.streamable_http_path = '/'
        allowed_hosts = settings.server.mcp.allowed_hosts
        mcp.settings.transport_security = TransportSecuritySettings(
            enable_dns_rebinding_protection=bool(allowed_hosts),
            allowed_hosts=allowed_hosts,
            allowed_origins=_derive_allowed_origins(allowed_hosts),
        )
        mcp_app = mcp.streamable_http_app()

        gated = BasicAuthMiddleware(
            mcp_app,
            user=settings.server.auth.user,
            password=settings.server.auth.password,
        )

        # session_manager is available only after streamable_http_app().
        # Mounted sub-apps do not run their own lifespan, so register the
        # session manager into the server lifespan.
        app.state.lifespan_cms.append(mcp.session_manager.run)

        mcp_path = settings.server.mcp.path
        app.mount(mcp_path, gated, name='MCP')

        # A Mount never matches its own slashless path, and the
        # router-level slash redirect is unreachable once the UI SPA
        # catch-all route is registered, so redirect the configured
        # path to the mount root explicitly.
        if mcp_path != '/':
            app.add_route(
                mcp_path,
                _redirect_to_mount_root,
                methods=['GET', 'POST', 'DELETE'],
                include_in_schema=False,
            )
    except Exception as e:
        msg = 'Failed to build MCP service'
        raise ServiceBuildingError(msg, context={'reason': str(e)}) from e


def _derive_allowed_origins(allowed_hosts: list[str]) -> list[str]:
    """Build the Origin allowlist matching the allowed hosts.

    Origin validation is part of the SDK DNS-rebinding protection:
    with an empty allowlist every request carrying an Origin header
    is rejected. Allowing http and https origins for each allowed
    host (including ``:*`` port wildcards, which the SDK matches the
    same way for origins) lets same-host clients through while
    foreign origins stay blocked.
    """
    return [
        f'{scheme}://{host}'
        for host in allowed_hosts
        for scheme in ('http', 'https')
    ]


async def _redirect_to_mount_root(request: Request) -> RedirectResponse:
    """Redirect the slashless mount path to the mount root."""
    url = request.url.replace(path=f'{request.url.path}/')
    return RedirectResponse(url=str(url), status_code=307)
