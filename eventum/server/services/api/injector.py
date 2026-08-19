"""Service injector."""

from fastapi import FastAPI

from eventum.api.exceptions import APISchemaGenerationError
from eventum.api.main import build_api_app
from eventum.app.hooks import InstanceHooks
from eventum.app.manager import GeneratorManager
from eventum.app.models.settings import Settings
from eventum.app.repositories import Repositories
from eventum.app.startup import Startup
from eventum.server.exceptions import ServiceBuildingError


def inject_service(  # noqa: PLR0913 - one argument per wired dependency
    app: FastAPI,
    generator_manager: GeneratorManager,
    settings: Settings,
    instance_hooks: InstanceHooks,
    startup: Startup,
    repositories: Repositories | None = None,
) -> None:
    """Inject service to server app.

    Parameters
    ----------
    app : FastAPI
        App to inject service in.

    generator_manager : GeneratorManager
        Manager of generators.

    settings : Settings
        Application settings.

    instance_hooks : InstanceHooks
        Instance hooks.

    startup : Startup
        Shared startup-config service.

    repositories : Repositories | None, default None
        Shared connected-repositories service. When omitted, a new
        instance is created from settings.

    Raises
    ------
    ServiceBuildingError
        If service building fails.

    """
    try:
        api_app = build_api_app(
            generator_manager=generator_manager,
            settings=settings,
            instance_hooks=instance_hooks,
            startup=startup,
            repositories=repositories,
        )
    except APISchemaGenerationError as e:
        raise ServiceBuildingError(str(e), context=e.context) from e

    app.mount(path='/api', app=api_app, name='REST API')
