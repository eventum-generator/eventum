import threading
from unittest.mock import MagicMock, patch

import pytest

from eventum.app.manager import GeneratorManager, ManagingError


@pytest.fixture
def manager():
    return GeneratorManager()


class FakeParams:
    def __init__(self, id) -> None:
        self.id = id


@pytest.fixture
def fake_params():
    return FakeParams('gen1')


@patch('eventum.app.manager.Generator')
def test_add_generator(mock_generator_class, manager, fake_params):
    mock_generator_class.return_value = MagicMock()

    manager.add(fake_params)
    assert 'gen1' in manager.generator_ids
    mock_generator_class.assert_called_once_with(fake_params)

    # Adding same generator again raises error
    with pytest.raises(ManagingError):
        manager.add(fake_params)


@patch('eventum.app.manager.Generator')
def test_remove_generator(_, manager, fake_params):
    manager.add(fake_params)
    manager.remove('gen1')

    assert 'gen1' not in manager.generator_ids

    with pytest.raises(ManagingError):
        manager.remove('gen1')


@patch('eventum.app.manager.Generator')
def test_bulk(_, manager):
    for i in range(3):
        manager.add(FakeParams(f'g{i}'))

    manager.bulk_remove(['g0', 'g1', 'nonexistent'])

    assert 'g0' not in manager.generator_ids
    assert 'g1' not in manager.generator_ids
    assert 'g2' in manager.generator_ids


@patch('eventum.app.manager.Generator')
def test_start_stop(mock_generator_class, manager, fake_params):
    mock_instance = MagicMock()
    mock_instance.start.return_value = True
    mock_generator_class.return_value = mock_instance

    manager.add(fake_params)
    started = manager.start('gen1')
    assert started

    mock_instance.start.assert_called_once()

    manager.stop('gen1')
    mock_instance.stop.assert_called_once()

    # Start/stop non-existent generator raises
    with pytest.raises(ManagingError):
        manager.start('nonexistent')

    with pytest.raises(ManagingError):
        manager.stop('nonexistent')


@patch('eventum.app.manager.Generator')
def test_bulk_start_stop_join(mock_generator_class, manager):
    # Prepare multiple fake generators
    ids = ['g0', 'g1', 'g2']
    mock_instances = [MagicMock() for _ in ids]
    mock_generator_class.side_effect = mock_instances

    for id in ids:
        manager.add(FakeParams(id))

    # bulk_start: some return True, some False
    mock_instances[0].start.return_value = True
    mock_instances[1].start.return_value = False
    mock_instances[2].start.return_value = True

    running, non_running = manager.bulk_start(ids + ['nonexistent'])
    assert set(running) == {'g0', 'g2'}
    assert set(non_running) == {'g1', 'nonexistent'}

    # bulk_stop calls stop on all existing
    manager.bulk_stop(ids + ['nonexistent'])
    for inst in mock_instances:
        inst.stop.assert_called()

    # bulk_join calls join on all existing
    manager.bulk_join(ids + ['nonexistent'])
    for inst in mock_instances:
        inst.join.assert_called()


def test_get_generator_property(manager, fake_params):
    # Before adding, get_generator raises
    with pytest.raises(ManagingError):
        manager.get_generator('gen1')

    # Add and test generator_ids property
    with patch('eventum.app.manager.Generator'):
        manager.add(fake_params)

    assert manager.generator_ids == ['gen1']


@patch('eventum.app.manager.Generator')
def test_concurrent_add_same_id_adds_once(_):
    manager = GeneratorManager()
    params = FakeParams('dup')
    errors: list[Exception] = []
    lock = threading.Lock()
    barrier = threading.Barrier(2)

    def worker():
        barrier.wait()
        try:
            manager.add(params)
        except ManagingError as e:
            with lock:
                errors.append(e)

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert manager.generator_ids == ['dup']
    assert len(errors) == 1


@patch('eventum.app.manager.Generator')
def test_concurrent_remove_same_id_removes_once(_):
    manager = GeneratorManager()
    manager.add(FakeParams('dup'))
    errors: list[Exception] = []
    lock = threading.Lock()
    barrier = threading.Barrier(2)

    def worker():
        barrier.wait()
        try:
            manager.remove('dup')
        except ManagingError as e:
            with lock:
                errors.append(e)

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert manager.generator_ids == []
    assert len(errors) == 1


def test_get_generator_missing_raises():
    manager = GeneratorManager()
    with pytest.raises(ManagingError):
        manager.get_generator('absent')
