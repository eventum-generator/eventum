"""Server application definition."""

from typing import NotRequired, TypedDict

import structlog
from fastapi import FastAPI

from eventum.app.hooks import InstanceHooks
from eventum.app.manager import GeneratorManager
from eventum.app.models.settings import Settings

logger = structlog.stdlib.get_logger()


class EnabledServices(TypedDict):
    """Enabled services."""

    api: NotRequired[bool]
    ui: NotRequired[bool]


def build_server_app(
    enabled_services: EnabledServices,
    generator_manager: GeneratorManager,
    settings: Settings,
    instance_hooks: InstanceHooks,
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

    Returns
    -------
    Built server FastAPI application.

    Raises
    ------
    ServiceBuildingError
        If some of the services fails to build.

    """
    app = FastAPI(
        title='Eventum Server',
    )

    if enabled_services.get('api', False):
        logger.info('Starting REST API service')
        from eventum.server.services.api.injector import (
            inject_service as inject_api_service,
        )

        inject_api_service(app, generator_manager, settings, instance_hooks)

    if enabled_services.get('ui', False):
        logger.info('Starting web UI service')
        from eventum.server.services.ui.injector import (
            inject_service as inject_ui_service,
        )

        inject_ui_service(app)

    return app
