"""Tests for the MCP dependency contexts."""

from pathlib import Path
from unittest.mock import MagicMock

from eventum.mcp.context import (
    AuthoringContext,
    FileAuthoringContext,
    LiveContext,
    ServerLiveContext,
)


def test_file_authoring_context_satisfies_protocol(tmp_path: Path) -> None:
    """FileAuthoringContext structurally satisfies AuthoringContext."""
    ctx = FileAuthoringContext(generators_dir=tmp_path, read_only=False)
    assert isinstance(ctx, AuthoringContext)
    assert ctx.generators_dir == tmp_path
    assert ctx.read_only is False


def test_file_authoring_context_is_not_live(tmp_path: Path) -> None:
    """The stdio context has no manager, so it is not a LiveContext."""
    ctx = FileAuthoringContext(generators_dir=tmp_path, read_only=True)
    assert not isinstance(ctx, LiveContext)


def test_server_live_context_is_both_protocols(tmp_path: Path) -> None:
    """ServerLiveContext satisfies both authoring and live protocols."""
    ctx = ServerLiveContext(
        generators_dir=tmp_path,
        read_only=False,
        manager=MagicMock(),
        startup=MagicMock(),
        generation=MagicMock(),
        logs_dir=tmp_path,
        log_format='plain',
    )
    assert isinstance(ctx, AuthoringContext)
    assert isinstance(ctx, LiveContext)
    assert ctx.read_only is False


def test_file_authoring_context_is_never_live_managed(tmp_path: Path) -> None:
    """The stdio context has no live runtime, so nothing is managed."""
    ctx = FileAuthoringContext(generators_dir=tmp_path, read_only=False)
    assert ctx.is_live_managed('anything') is False


def test_server_live_context_reports_managed_ids(tmp_path: Path) -> None:
    """The live context reports ids its manager currently holds."""
    manager = MagicMock()
    manager.generator_ids = ['live-one']
    ctx = ServerLiveContext(
        generators_dir=tmp_path,
        read_only=False,
        manager=manager,
        startup=MagicMock(),
        generation=MagicMock(),
        logs_dir=tmp_path,
        log_format='plain',
    )
    assert ctx.is_live_managed('live-one') is True
    assert ctx.is_live_managed('other') is False
