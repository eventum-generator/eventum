"""General app dependencies."""

from typing import Annotated

from fastapi import Depends, FastAPI, Request, WebSocket

from eventum.app.hooks import InstanceHooks
from eventum.app.manager import GeneratorManager
from eventum.app.models.settings import Settings
from eventum.app.startup import Startup


async def get_app(
    request: Request = None,  # type: ignore[assignment]
    websocket: WebSocket = None,  # type: ignore[assignment]
) -> FastAPI:
    """Get application.

    Parameters
    ----------
    request : Request, default=None
        Current request.

    websocket : WebSocket, default=None
        Websocket connection.

    Returns
    -------
    FastAPI
        Obtained application.

    Raises
    ------
    RuntimeError
        If app instance cannot be obtained

    """
    source = request or websocket
    if source is None:
        msg = 'Cannot obtain app instance'
        raise RuntimeError(msg)

    return source.app


AppDep = Annotated[
    FastAPI,
    Depends(get_app),
]


async def get_settings(app: AppDep) -> Settings:
    """Get application settings.

    Parameters
    ----------
    app : AppDep
        App dependency.

    Returns
    -------
    Settings
        Obtained application settings.

    Raises
    ------
    RuntimeError
        If app instance cannot be obtained

    """
    return app.state.settings


SettingsDep = Annotated[
    Settings,
    Depends(get_settings),
]


async def get_generator_manager(app: AppDep) -> GeneratorManager:
    """Get generator manager.

    Parameters
    ----------
    app : AppDep
        App dependency.

    Returns
    -------
    GeneratorManager
        Obtained generator manager.

    """
    return app.state.generator_manager


GeneratorManagerDep = Annotated[
    GeneratorManager,
    Depends(get_generator_manager),
]


async def get_startup(app: AppDep) -> Startup:
    """Get Startup entry point.

    Parameters
    ----------
    app : AppDep
        App dependency.

    Returns
    -------
    Startup
        Startup entry point held on app state.

    """
    return app.state.startup


StartupDep = Annotated[
    Startup,
    Depends(get_startup),
]


async def get_instance_hooks(request: Request) -> InstanceHooks:
    """Get instance hooks.

    Parameters
    ----------
    request : Request
        Current request.

    Returns
    -------
    InstanceHooks
        Obtained instance hooks.

    """
    return request.app.state.instance_hooks


InstanceHooksDep = Annotated[
    InstanceHooks,
    Depends(get_instance_hooks),
]
