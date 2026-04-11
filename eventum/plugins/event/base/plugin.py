"""Definition of base event plugin."""

from abc import abstractmethod
from datetime import datetime
from typing import TypedDict, TypeVar, override

from pydantic import RootModel

from eventum.plugins.base.plugin import Plugin, PluginParams
from eventum.plugins.event.base.config import EventPluginConfig
from eventum.plugins.event.exceptions import (
    PluginEventDroppedError,
    PluginProduceSignal,
)


class ProduceParams(TypedDict):
    """Params for `produce` method of `EventPlugin`.

    Attributes
    ----------
    timestamp : str
        Timestamp of event.

    tags : tuple[str, ...]
        Tags from input plugin that generated timestamp.

    """

    timestamp: datetime
    tags: tuple[str, ...]


class EventPluginParams(PluginParams):
    """Parameters for event plugin."""


ConfigT = TypeVar(
    'ConfigT',
    bound=(EventPluginConfig | RootModel[EventPluginConfig]),
)
ParamsT = TypeVar('ParamsT', bound=EventPluginParams)


class EventPlugin(Plugin[ConfigT, ParamsT], register=False):
    """Base class for all event plugins."""

    @override
    def __init__(self, config: ConfigT, params: ParamsT) -> None:
        super().__init__(config, params)

        self._produced = 0
        self._produce_failed = 0
        self._dropped = 0

    def produce(self, params: ProduceParams) -> list[str]:
        """Produce events with provided parameters.

        Parameters
        ----------
        params : ProduceParams
            Parameters for events producing.

        Returns
        -------
        list[str]
           Produced events.

        Raises
        ------
        PluginProduceError
            If any error occurs during producing events.

        PluginExhaustedError
            If no more events can be produced by event plugin.

        Notes
        -----
        If ``_produce()`` raises ``PluginEventDroppedError``, the
        error is silently caught, the ``dropped`` counter is
        incremented, and an empty list is returned.

        """
        try:
            result = self._produce(params=params)
        except PluginEventDroppedError:
            self._dropped += 1
            return []
        except PluginProduceSignal:
            raise
        except:
            self._produce_failed += 1
            raise

        self._produced += len(result)
        return result

    @abstractmethod
    def _produce(self, params: ProduceParams) -> list[str]:
        """Produce events with provided parameters.

        Notes
        -----
        See `produce` method for more info.

        """
        ...

    @property
    def produced(self) -> int:
        """Number of produced events."""
        return self._produced

    @property
    def produce_failed(self) -> int:
        """Number of unsuccessfully produced events."""
        return self._produce_failed

    @property
    def dropped(self) -> int:
        """Number of dropped events."""
        return self._dropped
