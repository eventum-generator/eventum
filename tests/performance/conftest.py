"""Fixtures for performance tests."""

import pytest

from tests.integration.conftest import (
    CLICKHOUSE_HOST,
    CLICKHOUSE_PORT,
    KAFKA_BOOTSTRAP,
    OPENSEARCH_URL,
)
from tests.integration.event_factory import EventFactory
from tests.integration.metrics import MetricsCollector


@pytest.fixture()
def event_factory():
    """Create a fresh EventFactory for each test."""
    return EventFactory()


@pytest.fixture()
def metrics_collector():
    """Create a MetricsCollector with 5s warmup."""
    return MetricsCollector(warmup_seconds=5.0)


@pytest.fixture()
def short_metrics_collector():
    """Create a MetricsCollector with no warmup for quick tests."""
    return MetricsCollector(warmup_seconds=0.0)
