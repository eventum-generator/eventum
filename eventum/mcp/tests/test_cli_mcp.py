"""Tests for the 'eventum mcp' CLI command registration."""

from click.testing import CliRunner

from eventum.cli.commands.eventum import cli


def test_mcp_command_registered() -> None:
    """Verify 'mcp' is registered and --read-only appears in help."""
    runner = CliRunner()
    result = runner.invoke(cli, ['mcp', '--help'])
    assert result.exit_code == 0
    assert 'read-only' in result.output.lower()
