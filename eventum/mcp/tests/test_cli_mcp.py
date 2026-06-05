"""Tests for the 'eventum mcp' CLI command registration."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner

from eventum.cli.commands.eventum import cli


def test_mcp_command_registered() -> None:
    """Verify 'mcp' is registered and --read-only appears in help."""
    runner = CliRunner()
    result = runner.invoke(cli, ['mcp', '--help'])
    assert result.exit_code == 0
    assert 'read-only' in result.output.lower()


def test_keyring_cryptfile_in_help() -> None:
    """The --keyring-cryptfile option is advertised in help."""
    runner = CliRunner()
    result = runner.invoke(cli, ['mcp', '--help'])
    assert result.exit_code == 0
    assert 'keyring-cryptfile' in result.output.lower()


def test_keyring_cryptfile_sets_location(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Passing --keyring-cryptfile sets the keyring location."""
    from eventum.security.manage import SECURITY_SETTINGS

    monkeypatch.setitem(SECURITY_SETTINGS, 'cryptfile_location', None)
    monkeypatch.setattr('eventum.logging.config.use_stderr', lambda **_: None)
    monkeypatch.setattr(
        'eventum.mcp.server.build_server', lambda *_, **__: MagicMock()
    )

    cryptfile = tmp_path / 'crypt.cfg'
    cryptfile.write_text('')

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            'mcp',
            '--generators-dir',
            str(tmp_path),
            '--keyring-cryptfile',
            str(cryptfile),
        ],
    )

    assert result.exit_code == 0
    assert SECURITY_SETTINGS['cryptfile_location'] == cryptfile.resolve()
