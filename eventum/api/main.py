"""API application definition."""

import structlog
from fastapi import FastAPI

import eventum
from eventum.api.dependencies.authentication import (
    HttpAuthDepends,
    WebsocketAuthDepends,
)
from eventum.api.exceptions import APISchemaGenerationError
from eventum.api.routers.auth import router as auth_router
from eventum.api.routers.docs import router as docs_router
from eventum.api.routers.docs.routes import ASYNCAPI_SCHEMA_PATH
from eventum.api.routers.docs.ws_schema_generator import (
    generate_asyncapi_schema,
    register_asyncapi_schema,
)
from eventum.api.routers.generator_configs import (
    router as generator_configs_router,
)
from eventum.api.routers.generators import router as generators_router
from eventum.api.routers.generators import ws_router as ws_generators_router
from eventum.api.routers.instance import router as instance_router
from eventum.api.routers.instance import ws_router as ws_instance_router
from eventum.api.routers.preview import router as preview_router
from eventum.api.routers.secrets import router as secrets_router
from eventum.api.routers.startup import router as startup_router
from eventum.app.hooks import InstanceHooks
from eventum.app.manager import GeneratorManager
from eventum.app.models.settings import Settings

logger = structlog.stdlib.get_logger()


def build_api_app(
    generator_manager: GeneratorManager,
    settings: Settings,
    instance_hooks: InstanceHooks,
) -> FastAPI:
    """Build FastAPI application.

    Parameters
    ----------
    generator_manager : GeneratorManager
        Manager of generators.

    settings : Settings
        Application settings.

    instance_hooks : InstanceHooks
        Instance hooks.

    Returns
    -------
    Built FastAPI application.

    Raises
    ------
    SchemaGenerationError
        If API schema generation fails.

    """
    app = FastAPI(
        title='Eventum API',
        description=(
            'API for managing generators, plugins and its dependencies'
        ),
        version=eventum.__version__,
        docs_url='/swagger',
        redoc_url='/redoc',
        contact={
            'name': 'Eventum',
            'url': 'https://github.com/eventum-generator',
        },
        license_info={
            'name': 'Apache 2.0',
            'url': 'https://github.com/eventum-generator/eventum/blob/master/LICENSE',
        },
        openapi_external_docs={
            'description': 'Eventum Documentation',
            'url': 'https://eventum.run',
        },
    )

    logger.debug('Injecting API runtime dependencies')
    app.state.generator_manager = generator_manager
    app.state.settings = settings
    app.state.instance_hooks = instance_hooks

    logger.debug('Connecting routers')
    app.include_router(
        auth_router,
        prefix='/auth',
        tags=['Authentication'],
    )
    app.include_router(
        instance_router,
        prefix='/instance',
        tags=['Instance'],
        dependencies=[HttpAuthDepends],
    )
    app.include_router(
        ws_instance_router,
        prefix='/instance',
        tags=['Instance', 'Websocket'],
        dependencies=[WebsocketAuthDepends],
    )
    app.include_router(
        generator_configs_router,
        prefix='/generator-configs',
        tags=['Generator configs'],
        dependencies=[HttpAuthDepends],
    )
    app.include_router(
        preview_router,
        prefix='/preview',
        tags=['Preview'],
        dependencies=[HttpAuthDepends],
    )
    app.include_router(
        generators_router,
        prefix='/generators',
        tags=['Generators'],
        dependencies=[HttpAuthDepends],
    )
    app.include_router(
        ws_generators_router,
        prefix='/generators',
        tags=['Generators', 'Websocket'],
        dependencies=[WebsocketAuthDepends],
    )
    app.include_router(
        startup_router,
        prefix='/startup',
        tags=['Startup'],
        dependencies=[HttpAuthDepends],
    )
    app.include_router(
        secrets_router,
        prefix='/secrets',
        tags=['Secrets'],
        dependencies=[HttpAuthDepends],
    )
    app.include_router(docs_router, tags=['Docs'])

    asyncapi_schema = generate_asyncapi_schema(
        app=app,
        host=settings.server.host,
        port=settings.server.port,
    )

    try:
        register_asyncapi_schema(
            schema=asyncapi_schema,
            target_path=ASYNCAPI_SCHEMA_PATH,
        )
    except RuntimeError as e:
        msg = 'Failed to generate asyncapi schema for websocket endpoints'
        raise APISchemaGenerationError(msg, context={'reason': str(e)}) from e

    return app
