from concurrent.futures import ThreadPoolExecutor
from threading import Event, RLock, Thread

import pytest

from eventum.plugins.event.plugins.template.state import (
    MultiThreadState,
    SingleThreadState,
)


@pytest.fixture
def single_thread_state():
    return SingleThreadState()


@pytest.fixture
def multi_thread_state():
    return MultiThreadState(lock=RLock())


def test_single_thread_state_set_get(single_thread_state: SingleThreadState):
    key = 'test_key'
    value = 'test_value'
    single_thread_state.set(key, value)
    assert single_thread_state.get(key) == value


def test_single_thread_state_update(single_thread_state: SingleThreadState):
    data = {'test_key1': 1, 'test_key2': 2}
    single_thread_state.update(data)
    assert single_thread_state.get('test_key1') == 1
    assert single_thread_state.get('test_key2') == 2


def test_single_thread_state_get_default(
    single_thread_state: SingleThreadState,
):
    key = 'test_key'
    default = 'default_value'
    assert single_thread_state.get(key, default) == default


def test_single_thread_state_clear(single_thread_state: SingleThreadState):
    key = 'test_key'
    value = 'test_value'
    single_thread_state.set(key, value)
    assert single_thread_state.get(key) == value
    single_thread_state.clear()
    assert single_thread_state.get(key, default=None) is None


def test_single_thread_state_as_dict(single_thread_state: SingleThreadState):
    key = 'test_key'
    value = 'test_value'
    single_thread_state.set(key, value)
    assert single_thread_state.as_dict() == {key: value}


def test_multi_thread_state_set_get(multi_thread_state: MultiThreadState):
    key = 'test_key'
    value = 'test_value'
    multi_thread_state.set(key, value)
    assert multi_thread_state.get(key) == value


def test_multi_thread_state_update(multi_thread_state: MultiThreadState):
    data = {'test_key1': 1, 'test_key2': 2}
    multi_thread_state.update(data)
    assert multi_thread_state.get('test_key1') == 1
    assert multi_thread_state.get('test_key2') == 2


def test_multi_thread_state_get_default(multi_thread_state: MultiThreadState):
    key = 'test_key'
    default = 'default_value'
    assert multi_thread_state.get(key, default) == default


def test_multi_thread_state_clear(multi_thread_state: MultiThreadState):
    key = 'test_key'
    value = 'test_value'
    multi_thread_state.set(key, value)
    assert multi_thread_state.get(key) == value
    multi_thread_state.clear()
    assert multi_thread_state.get(key, default=None) is None


def test_multi_thread_state_as_dict(multi_thread_state: MultiThreadState):
    key = 'test_key'
    value = 'test_value'
    multi_thread_state.set(key, value)
    assert multi_thread_state.as_dict() == {key: value}


def test_multi_thread_state_concurrent_increment(
    multi_thread_state: MultiThreadState,
):
    def increment():
        for _ in range(1000):
            multi_thread_state.acquire()
            value = multi_thread_state.get('i', 0)
            multi_thread_state.set('i', value + 1)
            multi_thread_state.release()

    with ThreadPoolExecutor() as executor:
        for _ in range(10):
            executor.submit(increment)

    assert multi_thread_state.get('i') == 10_000


def test_multi_thread_state_release_without_acquire(
    multi_thread_state: MultiThreadState,
):
    with pytest.raises(RuntimeError):
        multi_thread_state.release()


def test_multi_thread_state_release_if_held_without_holds(
    multi_thread_state: MultiThreadState,
):
    assert multi_thread_state.release_if_held() == 0


def test_multi_thread_state_release_if_held_releases_all_holds(
    multi_thread_state: MultiThreadState,
):
    multi_thread_state.acquire()
    multi_thread_state.acquire()

    assert multi_thread_state.release_if_held() == 2
    assert multi_thread_state.release_if_held() == 0


def test_multi_thread_state_release_if_held_frees_lock_for_other_threads(
    multi_thread_state: MultiThreadState,
):
    multi_thread_state.acquire()
    multi_thread_state.release_if_held()

    acquired = Event()

    def acquire():
        multi_thread_state.acquire()
        acquired.set()
        multi_thread_state.release()

    thread = Thread(target=acquire, daemon=True)
    thread.start()
    thread.join(timeout=5)

    assert acquired.is_set()


def test_multi_thread_state_release_if_held_ignores_holds_of_other_threads(
    multi_thread_state: MultiThreadState,
):
    held = Event()
    release_requested = Event()

    def hold():
        multi_thread_state.acquire()
        held.set()
        release_requested.wait(timeout=5)
        multi_thread_state.release()

    thread = Thread(target=hold, daemon=True)
    thread.start()

    assert held.wait(timeout=5)
    assert multi_thread_state.release_if_held() == 0

    release_requested.set()
    thread.join(timeout=5)

    assert not thread.is_alive()
