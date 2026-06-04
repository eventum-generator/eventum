"""MCP HTTP service injector.

The single SDK-aware server-side module: builds the FastMCP server for
the HTTP transport, configures Streamable HTTP, gates it behind Basic
auth, registers its session manager into the server lifespan, and
mounts it. Keeping all Streamable-HTTP wiring here isolates the eventual
SDK migration to one file.
"""

from fastapi import FastAPI
from mcp.server.transport_security import TransportSecuritySettings

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

    Raises
    ------
    ServiceBuildingError
        If the MCP service fails to build.

    """
    try:
        startup = Startup(
            file_path=settings.path.startup,
            generators_dir=settings.path.generators_dir,
            generation_parameters=settings.generation,
        )
        context = ServerLiveContext(
            generators_dir=settings.path.generators_dir,
            read_only=not settings.server.mcp.allow_write,
            manager=generator_manager,
            startup=startup,
            generation=settings.generation,
        )
        mcp = build_server(context, transport='http', live=True)

        # Configure Streamable HTTP BEFORE building the sub-app: the
        # session manager is created lazily inside streamable_http_app().
        mcp.settings.streamable_http_path = '/'
        mcp.settings.transport_security = TransportSecuritySettings(
            enable_dns_rebinding_protection=False,
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
        app.mount(settings.server.mcp.path, gated, name='MCP')
    except Exception as e:
        msg = 'Failed to build MCP service'
        raise ServiceBuildingError(msg, context={'reason': str(e)}) from e
