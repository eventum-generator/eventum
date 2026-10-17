"""Definition of base input plugin."""

from abc import abstractmethod
from collections.abc import Iterator
from typing import Any, Required, TypeVar, override
from zoneinfo import ZoneInfo

from numpy import datetime64
from numpy.typing import NDArray
from pydantic import RootModel

from eventum.plugins.base.plugin import Plugin, PluginParams
from eventum.plugins.input.base.config import InputPluginConfig
from eventum.plugins.input.buffer import Buffer


class InputPluginParams(PluginParams):
    """Parameters for input plugin.

    Attributes
    ----------
    timezone : ZoneInfo
        Timezone that is used for generated timestamps.

    """

    timezone: Required[ZoneInfo]


ConfigT = TypeVar(
    'ConfigT',
    bound=(InputPluginConfig | RootModel[InputPluginConfig]),
)
ParamsT = TypeVar('ParamsT', bound=InputPluginParams)


class InputPlugin(Plugin[ConfigT, ParamsT], register=False):
    """Base class for all input plugins.

    Other Parameters
    ----------------
    interactive : bool, default=False
        Whether to mark input plugin as interactive. Interactive input
        plugins produce timestamps in response to external events (e.g.
        HTTP requests) rather than on a schedule. They are consumed
        each on its own, never merged with others.

    """

    @override
    def __init__(self, config: ConfigT, params: ParamsT) -> None:
        super().__init__(config, params)

        with self._required_params():
            self._timezone = params['timezone']

        self._buffer = Buffer()

        self._generated = 0

    def __init_subclass__(
        cls,
        *,
        interactive: bool = False,
        **kwargs: Any,
    ) -> None:
        super().__init_subclass__(**kwargs)

        cls._interactive = interactive  # type: ignore[attr-defined]

    def generate(
        self,
        size: int,
        *,
        skip_past: bool = True,
    ) -> Iterator[NDArray[datetime64]]:
        """Generate timestamps.

        Parameters
        ----------
        size : int
            Number of timestamps to generate for each iteration, for
            the last iteration it is allowed to yield array not of
            full size. For interactive plugins it is allowed to yield
            array not of full size for each interaction with the plugin
            but if single interaction produces more than `size`
            timestamps then they must be chunked.

        skip_past : bool, default=True
            Whether to skip past timestamps before starting generation.

        Yields
        ------
        NDArray[datetime64]
            Array of generated timestamps.

        Raises
        ------
        PluginGenerationError
            If any error occurs during timestamps generation.

        Notes
        -----
        Interactive plugin may wait for an interaction for as long as
        none comes, but must end once `stop_interacting` is called.

        """
        self._generated = 0

        for array in self._generate(size=size, skip_past=skip_past):
            self._generated += array.size
            yield array

    @abstractmethod
    def _generate(
        self,
        size: int,
        *,
        skip_past: bool = True,
    ) -> Iterator[NDArray[datetime64]]:
        """Generate timestamps.

        Notes
        -----
        See `generate` method for more info.

        """
        ...

    @property
    def is_interactive(self) -> bool:
        """Whether the plugin is interactive."""
        return self._interactive  # type: ignore[attr-defined]

    def stop_interacting(self) -> None:
        """Stop interacting of interactive plugin. After this method is
        called no new timestamps can be added for yielding. Must be
        idempotent and safe to call from any thread.
        """
        raise NotImplementedError

    @property
    def generated(self) -> int:
        """Number of generated timestamps."""
        return self._generated
