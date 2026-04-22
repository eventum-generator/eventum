"""Tests for App."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from eventum.app.hooks import InstanceHooks
from eventum.app.main import App
from eventum.app.models.parameters.log import LogParameters
from eventum.app.models.parameters.path import PathParameters
from eventum.app.models.parameters.server import ServerParameters
from eventum.app.models.settings import Settings
from eventum.core.parameters import GenerationParameters


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """Build a minimal valid Settings for tests."""
    return Settings(
        server=ServerParameters(),
        generation=GenerationParameters(),
        log=LogParameters(),
        path=PathParameters(
            logs=tmp_path / 'logs',
            startup=tmp_path / 'startup.yml',
            generators_dir=tmp_path / 'generators',
            keyring_cryptfile=tmp_path / 'keyring.cfg',
        ),
    )


@pytest.fixture
def instance_hooks(settings: Settings) -> InstanceHooks:
    """Build a no-op InstanceHooks for tests."""
    return InstanceHooks(
        get_settings_file_path=lambda: settings.path.startup,
        terminate=lambda: None,
        restart=lambda: None,
    )


@pytest.fixture
def app(settings: Settings, instance_hooks: InstanceHooks) -> App:
    """Build an App instance for tests."""
    return App(settings=settings, instance_hooks=instance_hooks)


def test_stop_server_noop_when_server_not_started(app: App) -> None:
    """Stopping before the server is started is a no-op."""
    app._stop_server()  # noqa: SLF001


def test_stop_server_graceful_when_thread_exits_in_time(app: App) -> None:
    """When the server thread joins within the timeout, force_exit
    must remain unset.
    """
    server = MagicMock()
    server.should_exit = False
    server.force_exit = False

    thread = MagicMock()
    # After should_exit is set, thread exits immediately.
    thread.is_alive.side_effect = [True, False]

    app._server = server  # noqa: SLF001
    app._server_thread = thread  # noqa: SLF001

    app._stop_server()  # noqa: SLF001

    assert server.should_exit is True  # noqa: S101
    assert server.force_exit is False  # noqa: S101
    thread.join.assert_called_once_with(timeout=App.SERVER_SHUTDOWN_TIMEOUT)


def test_stop_server_forces_exit_when_thread_hangs(app: App) -> None:
    """When the server thread is still alive after the timeout,
    force_exit must be set and join called again without timeout.
    """
    server = MagicMock()
    server.should_exit = False
    server.force_exit = False

    thread = MagicMock()
    # Still alive after timed join -> must trigger force_exit path.
    thread.is_alive.side_effect = [True, True]

    app._server = server  # noqa: SLF001
    app._server_thread = thread  # noqa: SLF001

    app._stop_server()  # noqa: SLF001

    assert server.should_exit is True  # noqa: S101
    assert server.force_exit is True  # noqa: S101
    assert thread.join.call_count == 2  # noqa: S101, PLR2004
    thread.join.assert_any_call(timeout=App.SERVER_SHUTDOWN_TIMEOUT)
    thread.join.assert_any_call()


def test_server_shutdown_timeout_is_positive_int() -> None:
    """The shutdown timeout must be a positive int (uvicorn type)."""
    assert isinstance(App.SERVER_SHUTDOWN_TIMEOUT, int)  # noqa: S101
    assert App.SERVER_SHUTDOWN_TIMEOUT >= 1  # noqa: S101
