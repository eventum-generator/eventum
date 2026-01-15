"""Service injector."""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from eventum.server.exceptions import ServiceBuildingError
from eventum.server.services.ui.routes import WWW_DIR, router

ASSETS_DIR = WWW_DIR / 'assets'


def inject_service(
    app: FastAPI,
) -> None:
    """Inject service to server app.

    Parameters
    ----------
    app : FastAPI
        App to inject service in.

    Raises
    ------
    ServiceBuildingError
        If service building fails.

    """
    if not WWW_DIR.exists():
        msg = 'www directory does not exist'
        raise ServiceBuildingError(msg, context={'path': str(WWW_DIR)})

    if not ASSETS_DIR.exists():
        msg = 'www directory has not assets'
        raise ServiceBuildingError(msg, context={'path': str(ASSETS_DIR)})

    app.mount(
        path='/assets',
        app=StaticFiles(directory=ASSETS_DIR),
        name='Web UI assets',
    )
    app.include_router(router)
