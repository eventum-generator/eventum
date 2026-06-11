"""Module for managing multiple generators."""

import threading
from collections.abc import Callable, Iterable, Iterator
from concurrent.futures import Future, ThreadPoolExecutor

import structlog

from eventum.core.generator import Generator
from eventum.core.parameters import GeneratorParameters

logger = structlog.stdlib.get_logger()

_STOPPING_POOL_PREFIX = 'generators-stopping:'


class ManagingError(Exception):
    """Error in managing generators."""


class GeneratorManager:
    """Manager of generators."""

    def __init__(self) -> None:
        """Initialize manager."""
        self._generators: dict[str, Generator] = {}
        self._lock = threading.RLock()

    def add(self, params: GeneratorParameters) -> None:
        """Add new generator with provided parameters to list of managed
        generators.

        Parameters
        ----------
        params : GeneratorParameters
            Parameters for generator.

        Raises
        ------
        ManagingError
            If generator with this id is already added.

        """
        with self._lock:
            if params.id in self._generators:
                msg = 'Generator with this id is already added'
                raise ManagingError(msg)

            self._generators[params.id] = Generator(params)

    def remove(self, generator_id: str) -> None:
        """Remove generator from list of managed generators. Stop it in
        case it is running.

        Parameters
        ----------
        generator_id : str
            ID of generator to remove.

        Raises
        ------
        ManagingError
            If generator is not found in list of managed generators.

        """
        with self._lock:
            generator = self.get_generator(generator_id)
            del self._generators[generator_id]

        generator.stop()

    def bulk_remove(self, generator_ids: Iterable[str]) -> None:
        """Remove generators from list of managed generators. Stop
        generators that are running. If no generator of specified id
        found in list of managed generators it is just skipped.

        Parameters
        ----------
        generator_ids : Iterable[str]
            ID of generators to remove.

        """
        with self._lock:
            work = []
            for id in generator_ids:
                try:
                    generator = self._generators.pop(id)
                    work.append(generator)
                except KeyError:
                    continue

        with ThreadPoolExecutor(
            thread_name_prefix=_STOPPING_POOL_PREFIX,
        ) as executor:
            for generator in work:
                executor.submit(generator.stop)

    def start(self, generator_id: str) -> bool:
        """Start generator. Ignore call if generator is already
        running.

        Parameters
        ----------
        generator_id : str
            ID of generator to run.

        Returns
        -------
        bool
            `True` if generator successfully started or it is already
            running, `False` otherwise.

        Raises
        ------
        ManagingError
            If generator is not found in list of managed generators.

        """
        generator = self.get_generator(generator_id)
        return generator.start()

    def bulk_start(
        self,
        generator_ids: Iterable[str],
    ) -> tuple[list[str], list[str]]:
        """Start generators. Ignore call for those that are already
        running. If no generator of specified id found in list of
        managed generators it is just skipped.

        Parameters
        ----------
        generator_ids : Iterable[str]
            ID of generators to start.

        Returns
        -------
        tuple[list[str], list[str]]
            Ids of running and non running generators.

        Notes
        -----
        IDs of not existing generators are also presented in list of
        non running generators.

        """
        running_generators: list[str] = []
        non_running_generators: list[str] = []

        def callback(future: Future[bool], id: str) -> None:
            if future.result():
                running_generators.append(id)
            else:
                non_running_generators.append(id)

        with self._lock:
            work = []
            for id in generator_ids:
                try:
                    work.append((id, self._generators[id]))
                except KeyError:
                    non_running_generators.append(id)

        with ThreadPoolExecutor(
            thread_name_prefix='generators-starting:',
        ) as executor:
            for id, generator in work:
                future = executor.submit(generator.start)
                future.add_done_callback(
                    lambda future, id=id: callback(future, id),  # type: ignore[misc]
                )

        return running_generators, non_running_generators

    def stop(self, generator_id: str) -> None:
        """Stop generator. Ignore call if generator is not running.

        Parameters
        ----------
        generator_id : str
            ID of generator to stop.

        Raises
        ------
        ManagingError
            If generator is not found in list of managed generators.

        """
        generator = self.get_generator(generator_id)
        generator.stop()

    def _run_on_generators(
        self,
        generator_ids: Iterable[str],
        op: Callable[[Generator], object],
        thread_name_prefix: str,
    ) -> None:
        """Snapshot live generators under the lock and submit `op` for
        each to a named thread pool.

        Parameters
        ----------
        generator_ids : Iterable[str]
            ID of generators to operate on. Unknown ids are skipped.
        op : Callable[[Generator], object]
            Operation to submit for each live generator.
        thread_name_prefix : str
            Prefix for the worker thread names.

        """
        with self._lock:
            work = [
                g
                for id in generator_ids
                if (g := self._generators.get(id)) is not None
            ]

        with ThreadPoolExecutor(
            thread_name_prefix=thread_name_prefix,
        ) as executor:
            for generator in work:
                executor.submit(op, generator)

    def bulk_stop(self, generator_ids: Iterable[str]) -> None:
        """Stop generators. Ignore call for those that are not running.
        If no generator of specified id found in list of managed
        generators it is just skipped.

        Parameters
        ----------
        generator_ids : Iterable[str]
            ID of generators to stop.

        """
        self._run_on_generators(
            generator_ids,
            lambda generator: generator.stop(),
            _STOPPING_POOL_PREFIX,
        )

    def bulk_join(self, generator_ids: Iterable[str]) -> None:
        """Wait until all running generator terminates.

        Parameters
        ----------
        generator_ids : Iterable[str]
            ID of generators to join.

        """
        self._run_on_generators(
            generator_ids,
            lambda generator: generator.join(),
            'generators-joining:',
        )

    def get_generator(self, generator_id: str) -> Generator:
        """Get generator from list of managed generators.

        Parameters
        ----------
        generator_id : str
            ID of generator to get.

        Returns
        -------
        Generator
            Generator with provided ID.

        Raises
        ------
        ManagingError
            If no generator with provided ID found in managed
            generators.

        """
        with self._lock:
            try:
                return self._generators[generator_id]
            except KeyError as e:
                msg = f'No such generator `{e}`'
                raise ManagingError(msg) from None

    @property
    def generator_ids(self) -> list[str]:
        """List of generator ids."""
        with self._lock:
            return list(self._generators.keys())

    def iter_generators(self) -> Iterator[Generator]:
        """Iterate over all generators that are added to manager.

        Yields
        ------
        Generator
            Generator instance.

        """
        with self._lock:
            snapshot = list(self._generators.values())

        yield from snapshot
