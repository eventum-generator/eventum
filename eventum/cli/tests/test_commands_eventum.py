"""Tests for eventum CLI app startup commands."""

import signal
import subprocess
import sys
import textwrap
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import NoReturn
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

import eventum.cli.commands.eventum as commands
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

FLAT_TOGGLE_SECTION = 'server:\n  ui_enabled: false\n'


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


def test_start_app_instance_rejects_flat_toggle(
    tmp_path: Path,
    capsys: pytest.CaptureFixture,
) -> None:
    """The removed flat `ui_enabled` key exits with a validation error."""
    config_path = _write_config(
        tmp_path,
        FLAT_TOGGLE_SECTION,
        'flat_toggle.yml',
    )

    with pytest.raises(SystemExit) as exc:
        _start_app(config_path)

    assert exc.value.code == 1
    captured = capsys.readouterr()
    assert 'Failed to validate settings' in captured.err
    assert 'server.ui_enabled' in captured.err


def test_exit_bounded_ends_process_despite_thread_left_running(
    tmp_path: Path,
) -> None:
    """A thread plugin code left running does not hold the exit.

    Regression for #308: a worker of the output stage stuck in a call
    that never returns is joined by the interpreter as it shuts down,
    so a stopped instance never exited.
    """
    script = tmp_path / 'exit.py'
    script.write_text(
        textwrap.dedent(
            """
            import threading

            import eventum.cli.commands.eventum as commands

            EXIT_CODE = 3

            commands.EXIT_TIMEOUT = 0.5

            # the way a pool worker is left behind: not daemon
            threading.Thread(target=threading.Event().wait).start()

            commands._exit_bounded(EXIT_CODE)
            """,
        ),
    )

    result = subprocess.run(  # noqa: S603
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert result.returncode == 3, result.stderr  # noqa: PLR2004


class _BoundedExitError(Exception):
    """Stands in for the process exit the handlers end with."""


@pytest.fixture
def restored_signal_handlers() -> Iterator[None]:
    """Put back the handlers a command installs in this process."""
    handled = (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)
    saved = {sig: signal.getsignal(sig) for sig in handled}
    yield
    for sig, handler in saved.items():
        signal.signal(sig, handler)


def _record_exit(codes: list[int]) -> Callable[[int], NoReturn]:
    def exit_bounded(code: int) -> NoReturn:
        codes.append(code)
        raise _BoundedExitError

    return exit_bounded


@pytest.mark.usefixtures('restored_signal_handlers')
def test_run_terminates_through_bounded_exit(tmp_path: Path) -> None:
    """SIGTERM ends `run` through the exit that a thread left running
    by a generator that did not stop cannot hold.
    """
    config = tmp_path / 'eventum.yml'
    config.write_text('{}')
    app = MagicMock()
    codes: list[int] = []

    with (
        patch.object(commands, '_start_app_instance', return_value=app),
        patch.object(commands, '_exit_bounded', _record_exit(codes)),
        patch.object(
            commands.signal,
            'pause',
            lambda: signal.raise_signal(signal.SIGTERM),
        ),
    ):
        result = CliRunner().invoke(commands.cli, ['run', '-c', str(config)])

    assert isinstance(result.exception, _BoundedExitError)
    app.stop.assert_called_once()
    assert codes == [1]


@pytest.mark.usefixtures('restored_signal_handlers')
def test_generate_terminates_through_bounded_exit(tmp_path: Path) -> None:
    """SIGTERM ends `generate` through the bounded exit as well."""
    generator = MagicMock()
    generator.start.return_value = True
    generator.join.side_effect = lambda: signal.raise_signal(signal.SIGTERM)
    codes: list[int] = []

    # the command configures logging for the whole process
    with (
        patch.object(commands, 'logconf'),
        patch.object(commands, 'Generator', return_value=generator),
        patch.object(commands, '_exit_bounded', _record_exit(codes)),
    ):
        result = CliRunner().invoke(
            commands.cli,
            ['generate', '--id', 'g', '--path', str(tmp_path / 'g.yml')],
        )

    assert isinstance(result.exception, _BoundedExitError)
    generator.stop.assert_called_once()
    assert codes == [128 + signal.SIGTERM]
