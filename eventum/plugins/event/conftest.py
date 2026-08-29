"""Fixtures shared by the tests of event plugins."""

from collections.abc import Callable, Iterator
from threading import Event, Thread

import pytest

from eventum.plugins.event.state import GLOBAL_STATE


@pytest.fixture
def global_state_is_free() -> Callable[[], bool]:
    """Get check of whether the global state lock is held by no one.

    Returns
    -------
    Callable[[], bool]
        Check that tries to acquire the global state lock in a separate
        thread and reports whether it succeeded.

    """

    def check() -> bool:
        acquired = Event()

        def acquire() -> None:
            GLOBAL_STATE.acquire()
            acquired.set()
            GLOBAL_STATE.release()

        thread = Thread(target=acquire, daemon=True)
        thread.start()
        thread.join(timeout=5)

        return acquired.is_set()

    return check


@pytest.fixture
def clean_global_state() -> Iterator[None]:
    """Keep the process wide global state empty around the test."""
    GLOBAL_STATE.clear()

    yield

    GLOBAL_STATE.clear()


@pytest.fixture(autouse=True)
def _fail_on_leaked_global_lock() -> Iterator[None]:
    """Fail the test that leaves the global state lock acquired.

    The lock is process wide, so a hold left on the test thread blocks
    every later test that reaches the state from another thread - the
    run hangs instead of reporting the test that broke the guarantee.

    """
    yield

    holds = GLOBAL_STATE.release_if_held()

    if holds:
        pytest.fail(f'Test left {holds} hold(s) on the global state lock')
