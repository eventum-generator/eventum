import logging
import logging.config
import logging.handlers
from collections.abc import Hashable

import pytest

from eventum.logging.handlers import RoutingHandler


class AppendingHandler(logging.Handler):
    def __init__(
        self,
        target: dict[str, list],
        name: str = 'default',
        level: int | str = 0,
    ) -> None:
        super().__init__(level)
        self._target = target
        self._name = name

    def emit(self, record: logging.LogRecord) -> None:
        if self._name not in self._target:
            self._target[self._name] = []

        self._target[self._name].append(record.getMessage())


@pytest.fixture(autouse=True)
def clear_handlers():
    logger = logging.getLogger()
    logger.handlers.clear()
    yield
    logger.handlers.clear()


def test_routing_handler():
    records = {}

    def handler_factory(attribute: Hashable) -> logging.Handler:
        assert isinstance(attribute, str)
        return AppendingHandler(target=records, name=attribute)

    logger = logging.getLogger()
    logger.setLevel(0)
    logger.addHandler(
        RoutingHandler(
            attribute='my_attr',
            handler_factory=handler_factory,
            default_handler=AppendingHandler(target=records),
        )
    )

    logger.info('Test 1', extra={'my_attr': 'context_a'})
    logger.info('Test 2', extra={'my_attr': 'context_b'})
    logger.info('Test 3', extra={'my_attr': 'context_a'})
    logger.info('Test 4', extra={'my_attr': 'context_a'})
    logger.info('Test 5', extra={'my_attr': 'context_b'})

    assert records['context_a'] == ['Test 1', 'Test 3', 'Test 4']
    assert records['context_b'] == ['Test 2', 'Test 5']
    assert 'default' not in records

    logger.info('Test 6', extra={'my_attr': []})
    logger.info('Test 7', extra={'other_attr': 'context_c'})

    assert records['default'] == ['Test 6', 'Test 7']


def test_routing_handler_exception_in_factory():
    records = {}

    def handler_factory(attribute: Hashable) -> logging.Handler:
        raise RuntimeError

    logger = logging.getLogger()
    logger.setLevel(0)
    logger.addHandler(
        RoutingHandler(
            attribute='my_attr',
            handler_factory=handler_factory,
            default_handler=AppendingHandler(target=records),
        )
    )

    logger.info('Test 1', extra={'my_attr': 'context_a'})
    logger.info('Test 2', extra={'my_attr': 'context_b'})
    logger.info('Test 3', extra={'my_attr': 'context_a'})
    logger.info('Test 4', extra={'my_attr': 'context_a'})
    logger.info('Test 5', extra={'my_attr': 'context_b'})

    assert records['default'] == [
        'Test 1',
        'Test 2',
        'Test 3',
        'Test 4',
        'Test 5',
    ]
    assert 'context_a' not in records
    assert 'context_b' not in records


def test_routing_handler_default_value():
    records = {}
    created: list[Hashable] = []

    def handler_factory(attribute: Hashable) -> logging.Handler:
        created.append(attribute)
        assert isinstance(attribute, str)
        return AppendingHandler(target=records, name=attribute)

    logger = logging.getLogger()
    logger.setLevel(0)
    logger.addHandler(
        RoutingHandler(
            attribute='my_attr',
            handler_factory=handler_factory,
            default_handler=AppendingHandler(target=records),
            default_value='context_a',
        )
    )

    logger.info('Test 1', extra={'my_attr': 'context_a'})
    logger.info('Test 2', extra={'my_attr': 'context_b'})

    assert records['default'] == ['Test 1']
    assert records['context_b'] == ['Test 2']
    assert created == ['context_b']
