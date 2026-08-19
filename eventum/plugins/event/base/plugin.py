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
from eventum.plugins.event.state import GLOBAL_STATE, MultiThreadState
from eventum.utils.throttler import Throttler


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
    """Base class for all event plugins.

    Notes
    -----
    Every event plugin is connected to the process wide global state
    available as `global_state` attribute.

    """

    @override
    def __init__(self, config: ConfigT, params: ParamsT) -> None:
        super().__init__(config, params)

        self._produced = 0
        self._produce_failed = 0
        self._dropped = 0

        self._global_state = GLOBAL_STATE
        self._leaked_lock_throttler = Throttler(limit=1, period=10)

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

        PluginEventsExhaustedError
            If no more events can be produced by event plugin.

        Notes
        -----
        If ``_produce()`` raises ``PluginEventDroppedError``, the
        error is silently caught, the ``dropped`` counter is
        incremented, and an empty list is returned.

        A hold on the global state lock left by ``_produce()`` is
        dropped before returning, whatever the outcome.

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
        finally:
            self._release_leaked_global_lock()

        self._produced += len(result)
        return result

    def _release_leaked_global_lock(self) -> None:
        """Release the global state lock if the plugin left it held.

        A plugin that acquires the global state and does not release it
        - directly, or because producing failed in between - would
        block every other generator and every reader of the global
        state in the process. The lock is not meant to be held across
        events, so holds left after producing are dropped here.
        """
        holds = self._global_state.release_if_held()

        if holds:
            self._leaked_lock_throttler(
                self._logger.warning,
                'Released global state lock left acquired by event plugin',
                count=holds,
            )

    @abstractmethod
    def _produce(self, params: ProduceParams) -> list[str]:
        """Produce events with provided parameters.

        Notes
        -----
        See `produce` method for more info.

        """
        ...

    @property
    def global_state(self) -> MultiThreadState:
        """Global state shared across all generators in the process."""
        return self._global_state

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
