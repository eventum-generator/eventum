"""Tests for eventum CLI app startup commands."""

from pathlib import Path
from unittest.mock import patch

import pytest

from eventum.app.models.parameters.server import MCPParameters
from eventum.app.models.settings import Settings

DOTTED_SERVER_SECTION = (
    'server:\n'
    '  mcp.enabled: true\n'
    '  mcp.allow_write: true\n'
    "  mcp.path: '/mcp'\n"
)

NESTED_SERVER_SECTION = (
    'server:\n'
    '  mcp:\n'
    '    enabled: true\n'
    '    allow_write: true\n'
    "    path: '/mcp'\n"
)

CONFLICTING_SERVER_SECTION = (
    'server:\n  mcp.enabled: true\n  mcp:\n    enabled: false\n'
)


def _write_config(
    tmp_path: Path,
    server_section: str,
    name: str,
) -> Path:
    """Write a minimal eventum.yml with the given server section."""
    config_path = tmp_path / name
    config_path.write_text(
        server_section + 'generation: {}\n'
        'log: {}\n'
        'path:\n'
        f'  logs: {tmp_path / "logs"}\n'
        f'  startup: {tmp_path / "startup.yml"}\n'
        f'  generators_dir: {tmp_path / "generators"}\n'
        f'  keyring_cryptfile: {tmp_path / "keyring.dat"}\n',
    )
    return config_path


def _start_app(config_path: Path) -> Settings:
    """Run _start_app_instance with app and logging mocked."""
    from eventum.cli.commands.eventum import _start_app_instance

    with (
        patch('eventum.cli.commands.eventum.App') as mock_app,
        patch('eventum.cli.commands.eventum.logconf'),
    ):
        _start_app_instance(str(config_path))

    return mock_app.call_args.kwargs['settings']


def test_start_app_instance_expands_dotted_keys(tmp_path: Path) -> None:
    """Dotted server.mcp spelling loads same as the nested form."""
    dotted = _write_config(tmp_path, DOTTED_SERVER_SECTION, 'dotted.yml')
    nested = _write_config(tmp_path, NESTED_SERVER_SECTION, 'nested.yml')

    dotted_settings = _start_app(dotted)
    nested_settings = _start_app(nested)

    assert dotted_settings.server.mcp == MCPParameters(
        enabled=True,
        allow_write=True,
        path='/mcp',
    )
    assert dotted_settings == nested_settings


def test_start_app_instance_conflicting_dotted_keys(
    tmp_path: Path,
    capsys: pytest.CaptureFixture,
) -> None:
    """Conflicting spellings exit with an error naming the path."""
    config_path = _write_config(
        tmp_path,
        CONFLICTING_SERVER_SECTION,
        'conflicting.yml',
    )

    with pytest.raises(SystemExit) as exc:
        _start_app(config_path)

    assert exc.value.code == 1
    captured = capsys.readouterr()
    assert 'Failed to parse configuration YAML content' in captured.err
    assert 'server.mcp.enabled' in captured.err
