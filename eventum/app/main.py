"""Main application definition."""

import ssl
from threading import Thread

import structlog
import uvicorn

from eventum.app.hooks import InstanceHooks
from eventum.app.manager import GeneratorManager, ManagingError
from eventum.app.models.settings import Settings
from eventum.app.models.startup import StartupGeneratorParametersList
from eventum.app.startup import Startup, StartupError
from eventum.exceptions import ContextualError
from eventum.security.manage import SECURITY_SETTINGS

logger = structlog.stdlib.get_logger()


class AppError(ContextualError):
    """Application error."""


class App:
    """Main application."""

    SERVER_SHUTDOWN_TIMEOUT = 10

    def __init__(
        self,
        settings: Settings,
        instance_hooks: InstanceHooks,
    ) -> None:
        """Initialize App.

        Parameters
        ----------
        settings : Settings
            Settings of the applications.

        instance_hooks : InstanceHooks
            Instance hooks.

        """
        logger.debug(
            'Initializing app with provided settings',
            parameters=settings.model_dump(mode='json', exclude_unset=True),
        )
        self._settings = settings
        self._instance_hooks = instance_hooks

        logger.debug('Setting up security parameters')
        SECURITY_SETTINGS['cryptfile_location'] = (
            settings.path.keyring_cryptfile
        )

        self._manager = GeneratorManager()
        self._startup = Startup(settings=settings)

        self._server: uvicorn.Server | None = None
        self._server_thread = Thread(target=self._run_server, name='server')

    def start(self) -> None:
        """Start the app.

        Raises
        ------
        AppError
            If error occurs during initialization.

        """
        logger.info('Loading generators list')
        generators_params = self._load_startup_generators_params()

        logger.info('Starting generators')
        self._start_generators(generators_params=generators_params)

        if (
            self._settings.server.api_enabled
            or self._settings.server.ui_enabled
        ):
            from eventum.server.exceptions import ServiceBuildingError

            logger.info(
                'Starting Server',
                port=self._settings.server.port,
                host=self._settings.server.host,
            )
            try:
                self._start_server()
            except ServiceBuildingError as e:
                raise AppError(str(e), context=e.context) from e

    def stop(self) -> None:
        """Stop the app."""
        if (
            self._settings.server.api_enabled
            or self._settings.server.ui_enabled
        ):
            logger.info('Stopping the server')
            self._stop_server()

        logger.info('Stopping generators')
        self._stop_generators()

    def _load_startup_generators_params(
        self,
    ) -> StartupGeneratorParametersList:
        """Load params of generators from the startup file.

        Warns for entries whose path is outside the configured
        generators directory, since such generators cannot be observed
        by the API service.

        Returns
        -------
        StartupGeneratorParametersList
            List of startup generator params with absolute paths.

        Raises
        ------
        AppError
            If the startup file cannot be loaded or validated.

        """
        logger.debug(
            'Reading generators list from startup file',
            file_path=str(self._settings.path.startup),
        )
        try:
            params_list = self._startup.get_all()
        except StartupError as e:
            raise AppError(str(e), context=e.context) from e

        logger.debug(
            'Next base generation parameters will be used for generators',
            parameters=self._settings.generation.model_dump(mode='json'),
        )

        for params in params_list.root:
            if not params.path.is_relative_to(
                self._settings.path.generators_dir,
            ):
                logger.warning(
                    'Generator is outside the configured generators '
                    'directory. Consider moving it into specified directory '
                    'so it can be observed by the API service.',
                    generator_id=params.id,
                    path=str(self._settings.path.generators_dir),
                )

        return params_list

    def _start_generators(
        self,
        generators_params: StartupGeneratorParametersList,
    ) -> None:
        """Start generators.

        Parameters
        ----------
        generators_params : StartupGeneratorParametersList
            List of generators parameters.

        """
        added_generators: list[str] = []
        autostarted_generators: list[str] = []
        not_autostarted_generators: list[str] = []
        not_added_generators: list[str] = []

        for params in generators_params.root:
            try:
                self._manager.add(params)
                added_generators.append(params.id)

                if params.autostart:
                    autostarted_generators.append(params.id)
                else:
                    not_autostarted_generators.append(params.id)
            except ManagingError as e:
                not_added_generators.append(params.id)
                logger.error(
                    'Failed to add generator to execution manager',
                    generator_id=params.id,
                    reason=str(e),
                )

        logger.debug(
            'Bulk starting generators',
            generator_ids=autostarted_generators,
        )
        running_generators, non_running_generators = self._manager.bulk_start(
            generator_ids=autostarted_generators,
        )
        non_running_generators.extend(not_added_generators)
        non_running_generators.extend(not_autostarted_generators)

        if len(running_generators) > 0:
            logger.info(
                'Generators are running',
                count=len(running_generators),
                running_generators=running_generators,
                non_running_generators=non_running_generators,
            )
        else:
            logger.warning(
                'No generators are running',
                count=len(running_generators),
                running_generators=running_generators,
                non_running_generators=non_running_generators,
            )

    def _stop_generators(self) -> None:
        """Stop generators."""
        generator_ids = self._manager.generator_ids
        logger.debug(
            'Bulk stopping generators',
            generator_ids=generator_ids,
        )
        self._manager.bulk_stop(generator_ids)

    def _run_server(self) -> None:
        """Run server with handling possible errors."""
        if self._server is None:
            return

        try:
            self._server.run()
        except Exception as e:
            logger.exception(
                'Unexpected error occurred during server execution',
                reason=str(e),
            )

    def _start_server(self) -> None:
        """Start application server.

        Raises
        ------
        ServiceBuildingError
            If some of the service fails to build.

        """
        from eventum.server.main import build_server_app

        server_app = build_server_app(
            enabled_services={
                'api': self._settings.server.api_enabled,
                'ui': self._settings.server.ui_enabled,
            },
            generator_manager=self._manager,
            settings=self._settings,
            instance_hooks=self._instance_hooks,
        )

        if self._settings.server.ssl.enabled:
            ssl_settings = {
                'ssl_ca_certs': self._settings.server.ssl.ca_cert,
                'ssl_certfile': self._settings.server.ssl.cert,
                'ssl_keyfile': self._settings.server.ssl.cert_key,
                'ssl_cert_reqs': {
                    None: ssl.CERT_NONE,
                    'none': ssl.CERT_NONE,
                    'optional': ssl.CERT_OPTIONAL,
                    'required': ssl.CERT_REQUIRED,
                }[self._settings.server.ssl.verify_mode],
            }
        else:
            ssl_settings = {}

        self._server = uvicorn.Server(
            uvicorn.Config(
                server_app,
                host=self._settings.server.host,
                port=self._settings.server.port,
                access_log=True,
                log_config=None,
                timeout_graceful_shutdown=self.SERVER_SHUTDOWN_TIMEOUT,
                **ssl_settings,  # type: ignore[arg-type]
            ),
        )
        self._server_thread.start()

    def _stop_server(self) -> None:
        """Stop application server.

        Requests graceful shutdown. If the server does not stop within
        the timeout window, forces exit so long-lived connections (e.g.
        streaming WebSockets) cannot block termination indefinitely.
        """
        if self._server is None:
            return

        self._server.should_exit = True

        if not self._server_thread.is_alive():
            return

        self._server_thread.join(timeout=self.SERVER_SHUTDOWN_TIMEOUT)

        if not self._server_thread.is_alive():
            return

        logger.warning(
            'Server did not stop gracefully, forcing exit',
            timeout=self.SERVER_SHUTDOWN_TIMEOUT,
        )
        self._server.force_exit = True
        self._server_thread.join()
