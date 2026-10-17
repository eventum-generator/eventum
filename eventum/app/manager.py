"""Module for managing multiple generators."""

import threading
from collections.abc import Iterable, Iterator
from concurrent.futures import Future, ThreadPoolExecutor

import structlog

from eventum.core.generator import Generator
from eventum.core.parameters import GeneratorParameters

logger = structlog.stdlib.get_logger()

_STOPPING_POOL_PREFIX = 'generators-stopping:'

_STARTING_CONCURRENCY = 4
"""Number of generators started at a time.

Starting a generator loads its configuration and compiles its
templates, so an unbounded number of them at once spikes the memory and
the processor time of the whole application. Starting many takes longer
as a result, which is preferable to the spike.
"""


class ManagingError(Exception):
    """Error in managing generators."""


class GeneratorStopError(ManagingError):
    """Generator did not stop, its execution is abandoned."""


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

    def replace(
        self,
        generator_id: str,
        params: GeneratorParameters,
    ) -> None:
        """Replace parameters of a managed generator.

        The generator is rebuilt from the provided parameters and, when
        `params.id` differs from `generator_id`, is managed under the
        new id afterwards. Runtime state of the generator is not
        carried over, so it must not be active.

        Parameters
        ----------
        generator_id : str
            ID of the generator to replace.

        params : GeneratorParameters
            New parameters for the generator.

        Raises
        ------
        ManagingError
            If the generator is not found, is initializing, running or
            stopping, or another generator already uses `params.id`.

        """
        with self._lock:
            generator = self.get_generator(generator_id)

            if (
                generator.is_initializing
                or generator.is_running
                or generator.is_stopping
            ):
                msg = 'Generator must be stopped before replacing'
                raise ManagingError(msg)

            if params.id != generator_id and params.id in self._generators:
                msg = 'Generator with this id is already added'
                raise ManagingError(msg)

            del self._generators[generator_id]
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
        GeneratorStopError
            If generator did not stop, so it stays managed with its
            execution abandoned.

        ManagingError
            If generator is not found in list of managed generators.

        """
        with self._lock:
            generator = self.get_generator(generator_id)
            del self._generators[generator_id]

        if not generator.stop():
            self._keep_abandoned([generator])
            msg = 'Generator did not stop, its execution is abandoned'
            raise GeneratorStopError(msg)

    def bulk_remove(self, generator_ids: Iterable[str]) -> list[str]:
        """Remove generators from list of managed generators. Stop
        generators that are running. If no generator of specified id
        found in list of managed generators it is just skipped.

        Parameters
        ----------
        generator_ids : Iterable[str]
            ID of generators to remove.

        Returns
        -------
        list[str]
            IDs of generators that did not stop, so they stay managed
            with their execution abandoned.

        """
        with self._lock:
            work = []
            for id in generator_ids:
                try:
                    generator = self._generators.pop(id)
                    work.append(generator)
                except KeyError:
                    continue

        abandoned = self._stop_all(work)
        self._keep_abandoned(abandoned)

        return [generator.params.id for generator in abandoned]

    def _keep_abandoned(self, generators: Iterable[Generator]) -> None:
        """Put back generators that did not stop, so the ones still
        executing are not lost from management. An id taken by another
        generator meanwhile is left to it.
        """
        with self._lock:
            for generator in generators:
                self._generators.setdefault(generator.params.id, generator)

    @staticmethod
    def _stop_all(generators: list[Generator]) -> list[Generator]:
        """Stop generators at once and return those that did not stop.

        Every generator gets a thread of its own, so stopping many takes
        as long as stopping the slowest of them.
        """
        if not generators:
            return []

        with ThreadPoolExecutor(
            max_workers=len(generators),
            thread_name_prefix=_STOPPING_POOL_PREFIX,
        ) as executor:
            stopped = list(executor.map(lambda g: g.stop(), generators))

        return [
            generator
            for generator, is_stopped in zip(generators, stopped, strict=True)
            if not is_stopped
        ]

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
            max_workers=_STARTING_CONCURRENCY,
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
        GeneratorStopError
            If generator did not stop, so its execution is abandoned.

        ManagingError
            If generator is not found in list of managed generators.

        """
        generator = self.get_generator(generator_id)

        if not generator.stop():
            msg = 'Generator did not stop, its execution is abandoned'
            raise GeneratorStopError(msg)

    def _snapshot(self, generator_ids: Iterable[str]) -> list[Generator]:
        """Live generators of the ids, unknown ones skipped."""
        with self._lock:
            return [
                g
                for id in generator_ids
                if (g := self._generators.get(id)) is not None
            ]

    def bulk_stop(self, generator_ids: Iterable[str]) -> list[str]:
        """Stop generators. Ignore call for those that are not running.
        If no generator of specified id found in list of managed
        generators it is just skipped.

        Parameters
        ----------
        generator_ids : Iterable[str]
            ID of generators to stop.

        Returns
        -------
        list[str]
            IDs of generators that did not stop, so their execution is
            abandoned.

        """
        abandoned = self._stop_all(self._snapshot(generator_ids))
        return [generator.params.id for generator in abandoned]

    def bulk_join(self, generator_ids: Iterable[str]) -> None:
        """Wait until all running generator terminates.

        Parameters
        ----------
        generator_ids : Iterable[str]
            ID of generators to join.

        """
        work = self._snapshot(generator_ids)

        if not work:
            return

        with ThreadPoolExecutor(
            max_workers=len(work),
            thread_name_prefix='generators-joining:',
        ) as executor:
            for generator in work:
                executor.submit(generator.join)

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
