from pathlib import Path

from eventum.mcp.context import AuthoringContext, FileAuthoringContext


def test_file_authoring_context_satisfies_protocol(tmp_path: Path):
    ctx = FileAuthoringContext(generators_dir=tmp_path, read_only=False)
    assert isinstance(ctx, AuthoringContext)
    assert ctx.generators_dir == tmp_path
    assert ctx.read_only is False
