from collections.abc import Callable
from datetime import datetime
from threading import Event, Thread
from typing import override

import pytest
import structlog

from eventum.plugins.event.base.config import EventPluginConfig
from eventum.plugins.event.base.plugin import (
    EventPlugin,
    EventPluginParams,
    ProduceParams,
)
from eventum.plugins.event.exceptions import (
    PluginEventDroppedError,
    PluginEventsExhaustedError,
    PluginProduceError,
)
from eventum.plugins.event.state import GLOBAL_STATE


class DummyEventPluginConfig(EventPluginConfig, frozen=True):
    """Config of dummy event plugin."""


class DummyEventPlugin(
    EventPlugin[DummyEventPluginConfig, EventPluginParams],
    register=False,
):
    """Event plugin that produces a single event per timestamp.

    Parameters
    ----------
    holds : int, default=0
        Number of holds to take on the global state lock and leave
        acquired after producing.

    error : Exception | None, default=None
        Error to raise instead of producing events.

    """

    @override
    def __init__(
        self,
        config: DummyEventPluginConfig,
        params: EventPluginParams,
        holds: int = 0,
        error: Exception | None = None,
    ) -> None:
        super().__init__(config, params)

        self._holds = holds
        self._error = error

    @override
    def _produce(self, params: ProduceParams) -> list[str]:
        for _ in range(self._holds):
            self._global_state.acquire()

        if self._error is not None:
            raise self._error

        return ['event']


def create_plugin(
    holds: int = 0,
    error: Exception | None = None,
) -> DummyEventPlugin:
    return DummyEventPlugin(
        config=DummyEventPluginConfig(),
        params={'id': 1},
        holds=holds,
        error=error,
    )


def produce_params() -> ProduceParams:
    return {'timestamp': datetime.now().astimezone(), 'tags': tuple()}


def test_global_state_is_the_same_for_every_plugin():
    plugin = create_plugin()
    other_plugin = create_plugin()

    assert plugin.global_state is GLOBAL_STATE
    assert other_plugin.global_state is GLOBAL_STATE


def test_leaked_global_lock_is_released_after_producing(
    global_state_is_free: Callable[[], bool],
):
    plugin = create_plugin(holds=1)

    assert plugin.produce(params=produce_params()) == ['event']
    assert global_state_is_free()


def test_leaked_global_lock_is_released_after_produce_error(
    global_state_is_free: Callable[[], bool],
):
    plugin = create_plugin(
        holds=1,
        error=PluginProduceError('Failed', context={}),
    )

    with pytest.raises(PluginProduceError):
        plugin.produce(params=produce_params())

    assert plugin.produce_failed == 1
    assert global_state_is_free()


def test_leaked_global_lock_is_released_after_dropped_event(
    global_state_is_free: Callable[[], bool],
):
    plugin = create_plugin(holds=1, error=PluginEventDroppedError())

    assert plugin.produce(params=produce_params()) == []
    assert plugin.dropped == 1
    assert plugin.produce_failed == 0
    assert global_state_is_free()


def test_leaked_global_lock_is_released_after_exhaustion(
    global_state_is_free: Callable[[], bool],
):
    plugin = create_plugin(holds=1, error=PluginEventsExhaustedError())

    with pytest.raises(PluginEventsExhaustedError):
        plugin.produce(params=produce_params())

    assert plugin.produce_failed == 0
    assert global_state_is_free()


def test_every_leaked_hold_of_global_lock_is_released(
    global_state_is_free: Callable[[], bool],
):
    plugin = create_plugin(holds=3)

    with structlog.testing.capture_logs() as logs:
        plugin.produce(params=produce_params())

    warnings = [entry for entry in logs if entry['log_level'] == 'warning']

    assert len(warnings) == 1
    assert warnings[0]['count'] == 3
    assert global_state_is_free()


def test_warning_about_leaked_global_lock_is_throttled(
    global_state_is_free: Callable[[], bool],
):
    plugin = create_plugin(holds=1)

    with structlog.testing.capture_logs() as logs:
        plugin.produce(params=produce_params())
        plugin.produce(params=produce_params())

    warnings = [entry for entry in logs if entry['log_level'] == 'warning']

    assert len(warnings) == 1
    assert warnings[0]['event'] == (
        'Released global state lock left acquired by event plugin'
    )
    assert global_state_is_free()


def test_no_warning_when_global_lock_is_not_left_acquired():
    plugin = create_plugin()

    with structlog.testing.capture_logs() as logs:
        plugin.produce(params=produce_params())

    assert not [entry for entry in logs if entry['log_level'] == 'warning']


def test_global_lock_held_by_other_thread_is_not_released(
    global_state_is_free: Callable[[], bool],
):
    plugin = create_plugin()
    acquired = Event()
    release = Event()
    failures: list[RuntimeError] = []

    def hold() -> None:
        GLOBAL_STATE.acquire()
        acquired.set()
        release.wait(timeout=30)

        try:
            GLOBAL_STATE.release()
        except RuntimeError as e:
            failures.append(e)

    thread = Thread(target=hold, daemon=True)
    thread.start()

    try:
        assert acquired.wait(timeout=5)

        with structlog.testing.capture_logs() as logs:
            plugin.produce(params=produce_params())
    finally:
        release.set()
        thread.join(timeout=5)

    assert not failures
    assert not [entry for entry in logs if entry['log_level'] == 'warning']
    assert global_state_is_free()
