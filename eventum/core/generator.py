"""Module for managing event generation process."""

import os
import time
from datetime import datetime
from threading import Event, Lock, Thread, get_native_id
from zoneinfo import ZoneInfo

import structlog

from eventum.core.config import GeneratorConfig
from eventum.core.config_loader import ConfigurationLoadError, load
from eventum.core.executor import (
    ExecutionError,
    Executor,
    ImproperlyConfiguredError,
)
from eventum.core.parameters import GeneratorParameters
from eventum.core.plugins_initializer import (
    InitializationError,
    InitializedPlugins,
    init_plugins,
)
from eventum.logging.context import propagate_logger_context


class Generator:
    """Thread-wrapped generator."""

    def __init__(self, params: GeneratorParameters) -> None:
        """Initialize generator.

        Parameters
        ----------
        params : GeneratorParameters
            Generator parameters.

        """
        self._params = params

        self._config: GeneratorConfig | None = None
        self._plugins: InitializedPlugins | None = None
        self._executor: Executor | None = None

        self._thread: Thread | None = None
        self._initialized_event = Event()
        self._successfully_done_event = Event()
        self._is_stopping = False

        self._logger = structlog.stdlib.get_logger().bind(
            generator_id=self._params.id,
        )

        self._lock = Lock()

        self._start_time: datetime | None = None

    def _start(self) -> None:  # noqa: PLR0911, PLR0915
        """Start generation."""
        structlog.contextvars.bind_contextvars(generator_id=self._params.id)

        self._logger.info(
            'Generator is started',
            process_id=os.getpid(),
            thread_id=get_native_id(),
        )

        init_start_time = time.monotonic()

        self._logger.info(
            'Loading configuration',
            file_path=str(self._params.path),
        )
        try:
            self._config = load(self._params.path, self._params.params)
        except ConfigurationLoadError as e:
            self._logger.error(str(e), **e.context)
            self._release()
            return
        except Exception as e:
            self._logger.exception(
                'Unexpected error occurred during loading config',
                reason=str(e),
                file_path=str(self._params.path),
            )
            self._release()
            return

        self._logger.info('Initializing plugins')
        try:
            self._plugins = init_plugins(
                input=self._config.input,
                event=self._config.event,
                output=self._config.output,
                params=self._params,
            )
        except InitializationError as e:
            self._logger.error(str(e), **e.context)
            self._release()
            return
        except Exception as e:
            self._logger.exception(
                'Unexpected error occurred during initializing plugins',
                reason=str(e),
            )
            self._release()
            return

        self._logger.info('Initializing plugins executor')
        try:
            self._executor = Executor(
                input=self._plugins.input,
                event=self._plugins.event,
                output=self._plugins.output,
                params=self._params,
            )
        except ImproperlyConfiguredError as e:
            self._logger.error(str(e), **e.context)
            self._release()
            return
        except Exception as e:
            self._logger.exception(
                'Unexpected error occurred during initializing',
                reason=str(e),
            )
            self._release()
            return

        init_time = round(time.monotonic() - init_start_time, 3)
        self._logger.info('Initialization completed', seconds=init_time)

        self._logger.info(
            'Starting execution',
            parameters=self._params.model_dump_json(),
        )
        self._start_time = datetime.now().astimezone(tz=ZoneInfo('UTC'))
        self._initialized_event.set()
        try:
            self._executor.execute()
        except ExecutionError as e:
            self._logger.error(str(e), **e.context)
            return
        except Exception as e:
            self._logger.exception(
                'Unexpected error occurred during execution',
                reason=str(e),
            )
            return
        else:
            self._logger.info('Ending execution')
            self._successfully_done_event.set()
        finally:
            self._release()

    def start(self) -> bool:
        """Start generator in separate thread waiting for its
        initialization. Ignore call if generator is already running.

        Returns
        -------
        bool
            `True` if generator successfully started or it is already
            running, `False` otherwise.

        """
        self._logger.info('Starting generator')
        self._logger.debug('Acquiring lock')
        with self._lock:
            if self.is_running:
                self._logger.debug('Generator is already running')
                return True

            self._logger.debug('Clearing status')
            self._initialized_event.clear()
            self._successfully_done_event.clear()

            self._logger.debug('Creating and starting thread')
            self._thread = Thread(
                target=propagate_logger_context()(self._start),
                name=f'generator:{self._params.id}',
            )
            self._thread.start()

            self._logger.debug('Waiting for initialization')
            while self.is_initializing:
                time.sleep(0.1)

            return self._initialized_event.is_set()

    def stop(self) -> None:
        """Stop generator with joining underlying thread. Ignore call
        if generator is not running.
        """
        self._logger.info('Stopping generator')
        self._is_stopping = True

        self._logger.debug('Acquiring lock')
        with self._lock:
            if not self.is_running:
                self._logger.debug('Generator is not running')
                self._is_stopping = False
                return

            self._logger.debug('Requesting executor to stop')
            self._executor.request_stop()  # type: ignore[union-attr]

            self._logger.debug('Joining executing thread')
            self._thread.join()  # type: ignore[union-attr]

        self._is_stopping = False

    def _release(self) -> None:
        """Release resources of generator runtime after stopping or
        ending execution.
        """
        self._plugins = None
        self._executor = None
        self._config = None

    def join(self) -> None:
        """Wait until generator terminates."""
        if self._thread is not None:
            self._thread.join()
        else:
            self._logger.debug('There is no executing thread')

    def get_plugins_info(self) -> InitializedPlugins:
        """Get plugins information.

        Returns
        -------
        InitializedPlugins
            Information about plugins.

        Raises
        ------
        RuntimeError
            If information about plugins is unavailable (e.g
            generator wasn't yet started).

        """
        if self._plugins is None:
            msg = 'No information about plugins is available'
            raise RuntimeError(msg)

        return self._plugins

    def get_config(self) -> GeneratorConfig:
        """Get generator config.

        Returns
        -------
        GeneratorConfig
            Generator config.

        Raises
        ------
        RuntimeError
            If information about plugins is unavailable (e.g
            generator wasn't yet started).

        """
        if self._config is None:
            msg = 'No information about config is available'
            raise RuntimeError(msg)

        return self._config

    @property
    def params(self) -> GeneratorParameters:
        """Generator parameters."""
        return self._params

    @property
    def is_initializing(self) -> bool:
        """Whether the generator is initializing."""
        return (
            self._thread is not None
            and self._thread.is_alive()
            and not self._initialized_event.is_set()
        )

    @property
    def is_running(self) -> bool:
        """Whether the generator is running."""
        return (
            self._thread is not None
            and self._thread.is_alive()
            and self._initialized_event.is_set()
        )

    @property
    def is_stopping(self) -> bool:
        """Whether the generator is stopping."""
        return self._is_stopping

    @property
    def is_ended_up(self) -> bool:
        """Whether the generator has ended execution with or without
        errors.
        """
        return self._thread is not None and not self._thread.is_alive()

    @property
    def is_ended_up_successfully(self) -> bool:
        """Whether the generator has ended execution successfully."""
        return self.is_ended_up and self._successfully_done_event.is_set()

    @property
    def is_ended_up_with_error(self) -> bool:
        """Whether the generator has ended execution with error."""
        return self.is_ended_up and not self._successfully_done_event.is_set()

    @property
    def start_time(self) -> datetime | None:
        """Start time of the generator."""
        return self._start_time
