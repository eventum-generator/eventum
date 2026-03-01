"""Fixtures for longevity tests."""

import os

import pytest
import pytest_asyncio

from tests.integration.conftest import (
    CLICKHOUSE_HOST,
    CLICKHOUSE_PORT,
    KAFKA_BOOTSTRAP,
    LONGEVITY_DURATION,
    OPENSEARCH_URL,
)
from tests.integration.event_factory import EventFactory
from tests.integration.metrics import MetricsCollector


@pytest.fixture()
def longevity_duration():
    """Return configured longevity test duration in seconds."""
    return LONGEVITY_DURATION


@pytest.fixture()
def event_factory():
    """Create a fresh EventFactory for each test."""
    return EventFactory()


@pytest.fixture()
def metrics_collector():
    """Create a MetricsCollector with 10s warmup for longevity tests."""
    return MetricsCollector(warmup_seconds=10.0)
