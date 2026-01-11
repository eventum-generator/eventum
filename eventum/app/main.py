"""Main application definition."""

import ssl
from threading import Thread

import structlog
import uvicorn
import yaml
from pydantic import ValidationError, validate_call

from eventum.app.hooks import InstanceHooks
from eventum.app.manager import GeneratorManager, ManagingError
from eventum.app.models.generators import (
    StartupGeneratorParameters,
    StartupGeneratorParametersList,
)
from eventum.app.models.settings import Settings
from eventum.exceptions import ContextualError
from eventum.security.manage import SECURITY_SETTINGS
from eventum.utils.validation_prettier import prettify_validation_errors

logger = structlog.stdlib.get_logger()


class AppError(ContextualError):
    """Application error."""


class App:
    """Main application."""

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

    @validate_call
    def _validate_generators_params(
        self,
        object: list[dict],
    ) -> StartupGeneratorParametersList:
        """Validate list of startup generator params.

        Parameters
        ----------
        object : list[dict]
            List with startup parameters of generators.

        Returns
        -------
        StartupGeneratorParametersList
            Validated list of startup generator parameters applied
            above generation parameters from settings.

        Raises
        ------
        ValidationError
            If validation of provided object fails.

        """
        generators_parameters = (
            StartupGeneratorParametersList.build_over_generation_parameters(
                object=object,
                generation_parameters=self._settings.generation,
            )
        )

        logger.debug(
            'Next base generation parameters will be used for generators',
            parameters=self._settings.generation.model_dump(mode='json'),
        )

        normalized_params_list: list[StartupGeneratorParameters] = []
        for params in generators_parameters.root:
            normalized_params = params.as_absolute(
                base_dir=self._settings.path.generators_dir,
            )
            normalized_params_list.append(normalized_params)

            if not normalized_params.path.is_relative_to(
                self._settings.path.generators_dir,
            ):
                logger.warning(
                    'Generator is outside the configured generators '
                    'directory. Consider moving it into specified directory '
                    'so it can be observed by the API service.',
                    generator_id=normalized_params.id,
                    path=str(self._settings.path.generators_dir),
                )

        return StartupGeneratorParametersList(
            root=tuple(normalized_params_list),
        )

    def _load_startup_generators_params(
        self,
    ) -> StartupGeneratorParametersList:
        """Load params of generators from the startup file specified in
        config.

        Returns
        -------
        StartupGeneratorParametersList
            List of startup generator params.

        Raises
        ------
        AppError
            If error occurs during loading generators list.

        """
        logger.debug(
            'Reading generators list from startup file',
            file_path=str(self._settings.path.startup),
        )
        try:
            with self._settings.path.startup.open() as f:
                content = f.read()
        except OSError as e:
            msg = 'Failed to read generators list from startup file'
            raise AppError(
                msg,
                context={
                    'file_path': str(self._settings.path.startup),
                    'reason': str(e),
                },
            ) from None

        logger.debug('Parsing yaml content of generators list')
        try:
            obj = yaml.load(content, Loader=yaml.SafeLoader)
        except yaml.error.YAMLError as e:
            msg = 'Failed to parse generators list'
            raise AppError(
                msg,
                context={
                    'file_path': str(self._settings.path.startup),
                    'reason': str(e),
                },
            ) from None

        logger.debug('Validating generators list')
        try:
            return self._validate_generators_params(obj)
        except ValidationError as e:
            msg = 'Invalid structure of generators list'
            raise AppError(
                msg,
                context={'reason': prettify_validation_errors(e.errors())},
            ) from None

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
                **ssl_settings,  # type: ignore[arg-type]
            ),
        )
        self._server_thread.start()

    def _stop_server(self) -> None:
        """Stop application server."""
        if self._server is None:
            return

        self._server.should_exit = True

        if self._server_thread.is_alive():
            self._server_thread.join()
