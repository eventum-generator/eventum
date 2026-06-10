"""Server application definition."""

import contextlib
from collections.abc import AsyncIterator, Callable
from typing import NotRequired, TypedDict

import structlog
from fastapi import FastAPI

from eventum.app.hooks import InstanceHooks
from eventum.app.manager import GeneratorManager
from eventum.app.models.settings import Settings
from eventum.app.startup import Startup

logger = structlog.stdlib.get_logger()


class EnabledServices(TypedDict):
    """Enabled services."""

    api: NotRequired[bool]
    ui: NotRequired[bool]
    mcp: NotRequired[bool]


def build_server_app(
    enabled_services: EnabledServices,
    generator_manager: GeneratorManager,
    settings: Settings,
    instance_hooks: InstanceHooks,
    startup: Startup,
) -> FastAPI:
    """Build server FastAPI application.

    Parameters
    ----------
    enabled_services : EnabledServices
        Enabled services.

    generator_manager : GeneratorManager
        Manager of generators.

    settings : Settings
        Application settings.

    instance_hooks : InstanceHooks
        Instance hooks.

    startup : Startup
        Shared startup-config service, passed to the API and MCP
        services so they operate on a single instance.

    Returns
    -------
    Built server FastAPI application.

    Raises
    ------
    ServiceBuildingError
        If some of the services fails to build.

    """
    lifespan_cms: list[
        Callable[[], contextlib.AbstractAsyncContextManager[None]]
    ] = []

    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:  # noqa: ARG001
        async with contextlib.AsyncExitStack() as stack:
            for make_cm in lifespan_cms:
                await stack.enter_async_context(make_cm())
            yield

    app = FastAPI(title='Eventum Server', lifespan=lifespan)
    app.state.lifespan_cms = lifespan_cms

    if enabled_services.get('api', False):
        logger.info('Starting REST API service')
        from eventum.server.services.api.injector import (
            inject_service as inject_api_service,
        )

        inject_api_service(
            app, generator_manager, settings, instance_hooks, startup
        )

    if enabled_services.get('mcp', False):
        logger.info('Starting MCP service')
        from eventum.server.services.mcp.injector import (
            inject_service as inject_mcp_service,
        )

        inject_mcp_service(app, generator_manager, settings, startup)

    # The UI service registers an SPA catch-all route, so it must be
    # injected last: routes and mounts registered after it would be
    # shadowed and never matched.
    if enabled_services.get('ui', False):
        logger.info('Starting web UI service')
        from eventum.server.services.ui.injector import (
            inject_service as inject_ui_service,
        )

        inject_ui_service(app)

    return app
