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
    max_stop_seconds,
)
from eventum.core.parameters import GeneratorParameters
from eventum.core.plugins_initializer import (
    InitializationError,
    InitializedPlugins,
    init_plugins,
)
from eventum.core.resources import (
    GeneratorResources,
    ThreadCpuTimes,
    collect_network_usage,
    collect_thread_usage,
    disown_threads,
)
from eventum.utils.net_accounting import NetUsage


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
        self._is_abandoned = False

        self._logger = structlog.stdlib.get_logger().bind(
            generator_id=self._params.id,
        )

        self._lock = Lock()

        # Orders the end of initialization against a start giving it up,
        # so an initialization the start abandoned never goes on to run.
        self._init_lock = Lock()
        self._init_cancelled = Event()

        self._start_time: datetime | None = None
        self._network_baseline = NetUsage(sent_bytes=0, received_bytes=0)

    def _start(self) -> None:  # noqa: C901, PLR0911, PLR0915
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

        if not self._mark_initialized(init_time):
            self._release()
            return

        self._logger.info('Initialization completed', seconds=init_time)

        self._logger.info(
            'Starting execution',
            parameters=self._params.model_dump_json(),
        )
        self._start_time = datetime.now().astimezone(tz=ZoneInfo('UTC'))

        # Network counters are kept per thread name, so a generator
        # started again under the same id inherits the traffic of its
        # earlier runs - the baseline leaves this run alone.
        self._network_baseline = collect_network_usage(self._params.id)

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

    def _mark_initialized(self, init_time: float) -> bool:
        """Mark initialization completed unless a start gave it up.

        Parameters
        ----------
        init_time : float
            Seconds the initialization took.

        Returns
        -------
        bool
            Whether the generator may go on to execute.

        """
        with self._init_lock:
            if self._init_cancelled.is_set():
                self._logger.warning(
                    'Initialization completed after it was cancelled, '
                    'execution is not started',
                    seconds=init_time,
                )
                return False

            self._initialized_event.set()
            return True

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
            if self.is_abandoned:
                self._logger.error(
                    'Generator cannot be started, its earlier run did not end',
                    hint=(
                        'Restart the Eventum process to release it, and '
                        'check the plugins of the generator for code that '
                        'does not return'
                    ),
                )
                return False

            if self.is_running:
                self._logger.debug('Generator is already running')
                return True

            self._logger.debug('Clearing status')
            self._initialized_event.clear()
            self._successfully_done_event.clear()
            self._init_cancelled.clear()
            self._is_abandoned = False

            # Threads earlier runs left behind are not counted for this
            # one.
            disown_threads(self._params.id)

            self._logger.debug('Creating and starting thread')
            # A daemon thread, as an execution that does not stop is
            # abandoned and must not keep the process from exiting.
            self._thread = Thread(
                target=self._start,
                name=f'generator:{self._params.id}',
                daemon=True,
            )
            self._thread.start()

            self._logger.debug('Waiting for initialization')
            deadline = time.monotonic() + self._params.init_timeout
            while self.is_initializing:
                if time.monotonic() >= deadline:
                    return self._abandon_initialization()

                time.sleep(0.1)

            return self._initialized_event.is_set()

    def _abandon_initialization(self) -> bool:
        """Give up an initialization that did not end in time.

        Returns
        -------
        bool
            Whether the generator started after all, as its
            initialization may end at this very moment.

        """
        with self._init_lock:
            if self._initialized_event.is_set():
                return True

            self._init_cancelled.set()

        self._is_abandoned = True
        self._logger.error(
            'Generator did not initialize in time, its initialization is '
            'abandoned',
            timeout=self._params.init_timeout,
            hint=(
                'Raise the init timeout if loading the generator takes '
                'this long, or check its plugins for code that does not '
                'return; restart the Eventum process to release it'
            ),
        )
        return False

    def stop(self) -> bool:
        """Stop generator within bounded time. Ignore call if generator
        is not running.

        The generator is given `stop_timeout` seconds to deliver the
        events it has already produced, after which its execution is
        aborted.

        Returns
        -------
        bool
            `True` if the generator stopped or was not running, `False`
            if its execution is still running after the abort, which
            leaves it to plugin code that does not return.

        """
        self._logger.info('Stopping generator')
        self._is_stopping = True

        try:
            # A start still loading the plugins holds the lock; asked
            # not to go on to execute, it lets go as soon as the loading
            # ends, or once its init timeout runs out.
            self._cancel_initialization()

            # Neither a stop under way nor a start may hold this stop
            # for good.
            self._logger.debug('Acquiring lock')
            lock_timeout = max(
                max_stop_seconds(self._params),
                self._params.init_timeout,
            )
            if not self._lock.acquire(timeout=lock_timeout):
                self._logger.error(
                    'Generator did not stop, it is still being started or '
                    'stopped',
                    hint=(
                        'Restart the Eventum process if it stays so, and '
                        'check the plugins of the generator for code that '
                        'does not return'
                    ),
                )
                return False

            try:
                return self._stop_locked()
            finally:
                self._lock.release()
        finally:
            self._is_stopping = False

    def _cancel_initialization(self) -> None:
        """Keep an initialization in progress from going on to execute.
        Ignored once the generator is initialized.
        """
        with self._init_lock:
            if not self._initialized_event.is_set():
                self._init_cancelled.set()

    def _stop_locked(self) -> bool:
        """Stop generator holding the lock, see `stop`."""
        if self.is_abandoned and not self.is_running:
            self._logger.error(
                'Generator did not stop, its initialization is abandoned',
            )
            return False

        if not self.is_running:
            self._logger.debug('Generator is not running')
            return True

        # The thread releases the executor as its execution ends,
        # which may happen at any moment before it is joined.
        executor = self._executor
        if executor is not None:
            self._logger.debug('Requesting executor to stop')

            if not executor.stop():
                self._is_abandoned = True
                self._logger.error(
                    'Generator did not stop, its execution is abandoned',
                    hint=(
                        'Restart the Eventum process to release it, and '
                        'check the plugins of the generator for code that '
                        'does not return'
                    ),
                )
                return False

        # The execution has ended, so the thread is only finishing its
        # own bookkeeping.
        self._logger.debug('Joining executing thread')
        self._thread.join()  # type: ignore[union-attr]

        return True

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

    def get_resources(
        self,
        cpu_times: ThreadCpuTimes | None = None,
    ) -> GeneratorResources:
        """Get runtime resources occupied by the generator.

        Parameters
        ----------
        cpu_times : ThreadCpuTimes | None, default=None
            Already sampled CPU times of the process threads to read
            from instead of sampling them. Pass a shared sample when
            accounting for several generators at once.

        Returns
        -------
        GeneratorResources
            Threads, what they consumed and the fill levels of the
            pipeline queues.

        Raises
        ------
        RuntimeError
            If the generator is not executing, so it holds no queues.

        """
        # Held, as the thread may release it while usage is collected.
        executor = self._executor
        if executor is None:
            msg = 'No information about resources is available'
            raise RuntimeError(msg)

        usage = collect_thread_usage(self._params.id, cpu_times)
        network = collect_network_usage(self._params.id)

        return GeneratorResources(
            thread_count=usage.count,
            cpu_seconds=usage.cpu_seconds,
            run_delay_seconds=usage.run_delay_seconds,
            disk_read_bytes=usage.disk_read_bytes,
            disk_written_bytes=usage.disk_written_bytes,
            network_sent_bytes=(
                network.sent_bytes - self._network_baseline.sent_bytes
            ),
            network_received_bytes=(
                network.received_bytes - self._network_baseline.received_bytes
            ),
            queues=executor.queue_usage(),
        )

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
    def is_abandoned(self) -> bool:
        """Whether the generator did not stop or did not initialize in
        time, and its run is left to plugin code that does not return.
        """
        return (
            self._is_abandoned
            and self._thread is not None
            and self._thread.is_alive()
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
