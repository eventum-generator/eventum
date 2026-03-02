"""Fixtures for performance tests."""

import pytest

from tests.performance._helpers import PerfResult


@pytest.fixture
def perf_result():
    """Provide a mutable container for performance results.

    Tests write ``duration_seconds``, ``total_events``, and ``metadata``
    into this object for human-readable CI output.
    """
    return PerfResult()
