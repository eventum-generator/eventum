"""Tests for server shutdown helpers."""

from collections.abc import Iterator

import pytest
from sse_starlette.sse import AppStatus

from eventum.server.shutdown import request_sse_drain, reset_sse_drain


@pytest.fixture(autouse=True)
def _restore_sse_flag() -> Iterator[None]:
    """Restore the process-global SSE flag around each test."""
    original = AppStatus.should_exit
    try:
        yield
    finally:
        AppStatus.should_exit = original


def test_request_sse_drain_sets_flag() -> None:
    """Requesting drain flips the sse_starlette shutdown flag on."""
    AppStatus.should_exit = False
    request_sse_drain()
    assert AppStatus.should_exit is True


def test_reset_sse_drain_clears_flag() -> None:
    """Resetting clears the flag so a restart keeps streaming."""
    AppStatus.should_exit = True
    reset_sse_drain()
    assert AppStatus.should_exit is False
