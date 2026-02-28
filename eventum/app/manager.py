"""Module for managing multiple generators."""

from collections.abc import Iterable, Iterator
from concurrent.futures import Future, ThreadPoolExecutor

import structlog

from eventum.core.generator import Generator
from eventum.core.parameters import GeneratorParameters

logger = structlog.stdlib.get_logger()


class ManagingError(Exception):
    """Error in managing generators."""


class GeneratorManager:
    """Manager of generators."""

    def __init__(self) -> None:
        """Initialize manager."""
        self._generators: dict[str, Generator] = {}

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
        generator = self.get_generator(generator_id)
        generator.stop()

        del self._generators[generator_id]

    def bulk_remove(self, generator_ids: Iterable[str]) -> None:
        """Remove generators from list of managed generators. Stop
        generators that are running. If no generator of specified id
        found in list of managed generators it is just skipped.

        Parameters
        ----------
        generator_ids : Iterable[str]
            ID of generators to remove.

        """
        with ThreadPoolExecutor(
            thread_name_prefix='generators-stopping:',
        ) as executor:
            for id in generator_ids:
                try:
                    generator = self._generators[id]
                    executor.submit(
                        generator.stop,
                    )
                    del self._generators[id]
                except KeyError:
                    continue

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

        with ThreadPoolExecutor(
            thread_name_prefix='generators-starting:',
        ) as executor:
            for id in generator_ids:
                try:
                    generator = self._generators[id]
                    future = executor.submit(
                        generator.start,
                    )
                    future.add_done_callback(
                        lambda future, id=id: callback(future, id),  # type: ignore[misc]
                    )
                except KeyError:
                    non_running_generators.append(id)

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

    def bulk_stop(self, generator_ids: Iterable[str]) -> None:
        """Stop generators. Ignore call for those that are not running.
        If no generator of specified id found in list of managed
        generators it is just skipped.

        Parameters
        ----------
        generator_ids : Iterable[str]
            ID of generators to stop.

        """
        with ThreadPoolExecutor(
            thread_name_prefix='generators-stopping:',
        ) as executor:
            for id in generator_ids:
                if id in self._generators:
                    generator = self._generators[id]
                    executor.submit(
                        generator.stop,
                    )

    def bulk_join(self, generator_ids: Iterable[str]) -> None:
        """Wait until all running generator terminates.

        Parameters
        ----------
        generator_ids : Iterable[str]
            ID of generators to join.

        """
        with ThreadPoolExecutor(
            thread_name_prefix='generators-joining:',
        ) as executor:
            for id in generator_ids:
                if id in self._generators:
                    generator = self._generators[id]
                    executor.submit(
                        generator.join,
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
        try:
            return self._generators[generator_id]
        except KeyError as e:
            msg = f'No such generator `{e}`'
            raise ManagingError(msg) from None

    @property
    def generator_ids(self) -> list[str]:
        """List of generator ids."""
        return list(self._generators.keys())

    def iter_generators(self) -> Iterator[Generator]:
        """Iterate over all generators that are added to manager.

        Yields
        ------
        Generator
            Generator instance.

        """
        yield from self._generators.values()
