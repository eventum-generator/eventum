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
