"""Tests for eventum.mcp.observability."""

from typing import Any

import structlog
import structlog.testing

from eventum.mcp.errors import ToolFailure
from eventum.mcp.observability import observe_failure


def test_observe_failure_passes_through_success() -> None:
    """Non-failure values are returned unchanged without logging."""
    value: dict[str, Any] = {'ok': True}
    assert observe_failure(value, mcp_tool='t', mcp_transport='stdio') is value


def test_observe_failure_logs_failure() -> None:
    """ToolFailure is returned unchanged and a warning is emitted."""
    failure = ToolFailure(error='boom', details={})

    with structlog.testing.capture_logs() as logs:
        result = observe_failure(
            failure,
            mcp_tool='read_generator_file',
            mcp_transport='http',
        )

    assert result is failure
    assert len(logs) == 1
    entry = logs[0]
    assert entry['log_level'] == 'warning'
    assert entry['mcp_tool'] == 'read_generator_file'
    assert entry['mcp_transport'] == 'http'
    assert entry['reason'] == 'boom'
