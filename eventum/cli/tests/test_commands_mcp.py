"""Tests for the 'eventum mcp' CLI command registration."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner

from eventum.cli.commands.eventum import cli
from eventum.mcp.context import FileAuthoringContext


@pytest.mark.parametrize(
    'needle',
    ['read-only', 'keyring-cryptfile', 'config-filename'],
)
def test_mcp_help_advertises_option(needle: str) -> None:
    """The 'mcp --help' output advertises the given option."""
    runner = CliRunner()
    result = runner.invoke(cli, ['mcp', '--help'])
    assert result.exit_code == 0
    assert needle in result.output.lower()


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


@pytest.mark.parametrize('read_only', [False, True])
def test_flags_propagate_into_context(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    read_only: bool,
) -> None:
    """--generators-dir and --read-only reach the authoring context."""
    captured: dict[str, object] = {}

    def fake_build_server(context: object, **_: object) -> MagicMock:
        captured['context'] = context
        return MagicMock()

    monkeypatch.setattr('eventum.logging.config.use_stderr', lambda **_: None)
    monkeypatch.setattr('eventum.mcp.server.build_server', fake_build_server)

    args = ['mcp', '--generators-dir', str(tmp_path)]
    if read_only:
        args.append('--read-only')

    runner = CliRunner()
    result = runner.invoke(cli, args)

    assert result.exit_code == 0
    context = captured['context']
    assert isinstance(context, FileAuthoringContext)
    assert context.generators_dir == tmp_path.resolve()
    assert context.read_only is read_only


@pytest.mark.parametrize(
    ('args', 'expected'),
    [
        ([], 'generator.yml'),
        (['--config-filename', 'custom.yml'], 'custom.yml'),
    ],
)
def test_config_filename_propagates_into_context(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    args: list[str],
    expected: str,
) -> None:
    """--config-filename (or its default) reaches the context."""
    captured: dict[str, object] = {}

    def fake_build_server(context: object, **_: object) -> MagicMock:
        captured['context'] = context
        return MagicMock()

    monkeypatch.setattr('eventum.logging.config.use_stderr', lambda **_: None)
    monkeypatch.setattr('eventum.mcp.server.build_server', fake_build_server)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ['mcp', '--generators-dir', str(tmp_path), *args],
    )

    assert result.exit_code == 0
    context = captured['context']
    assert isinstance(context, FileAuthoringContext)
    assert context.config_filename == expected
