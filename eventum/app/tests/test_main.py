"""Tests for App."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from eventum.app.hooks import InstanceHooks
from eventum.app.main import App
from eventum.app.models.parameters.log import LogParameters
from eventum.app.models.parameters.path import PathParameters
from eventum.app.models.parameters.server import (
    MCPParameters,
    ServerParameters,
)
from eventum.app.models.settings import Settings
from eventum.core.parameters import GenerationParameters


def _make_settings(tmp_path: Path, server: ServerParameters) -> Settings:
    """Build a minimal valid Settings rooted under tmp_path."""
    return Settings(
        server=server,
        generation=GenerationParameters(),
        log=LogParameters(),
        path=PathParameters(
            logs=tmp_path / 'logs',
            startup=tmp_path / 'startup.yml',
            generators_dir=tmp_path / 'generators',
            keyring_cryptfile=tmp_path / 'keyring.cfg',
        ),
    )


def _make_hooks(settings: Settings) -> InstanceHooks:
    """Build a no-op InstanceHooks for tests."""
    return InstanceHooks(
        get_settings_file_path=lambda: settings.path.startup,
        terminate=lambda: None,
        restart=lambda: None,
    )


def _make_mcp_only_app(tmp_path: Path) -> App:
    """Build an App with only the MCP service enabled."""
    (tmp_path / 'startup.yml').write_text('[]')
    settings = _make_settings(
        tmp_path,
        ServerParameters(
            api_enabled=False,
            ui_enabled=False,
            mcp=MCPParameters(enabled=True),
        ),
    )
    return App(settings=settings, instance_hooks=_make_hooks(settings))


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """Build a minimal valid Settings for tests."""
    return _make_settings(tmp_path, ServerParameters())


@pytest.fixture
def instance_hooks(settings: Settings) -> InstanceHooks:
    """Build a no-op InstanceHooks for tests."""
    return _make_hooks(settings)


@pytest.fixture
def app(settings: Settings, instance_hooks: InstanceHooks) -> App:
    """Build an App instance for tests."""
    return App(settings=settings, instance_hooks=instance_hooks)


def test_start_starts_server_when_only_mcp_enabled(tmp_path: Path) -> None:
    """The server must start when MCP is the only enabled service."""
    app = _make_mcp_only_app(tmp_path)

    with (
        patch('eventum.server.main.build_server_app') as mock_build,
        patch('eventum.app.main.uvicorn') as mock_uvicorn,
    ):
        app.start()
        try:
            mock_build.assert_called_once()
            enabled = mock_build.call_args.kwargs['enabled_services']
            assert enabled == {'api': False, 'ui': False, 'mcp': True}
            mock_uvicorn.Server.assert_called_once()
        finally:
            app.stop()


def test_stop_stops_server_when_only_mcp_enabled(tmp_path: Path) -> None:
    """stop() must stop the server when only MCP is enabled."""
    app = _make_mcp_only_app(tmp_path)

    with patch.object(App, '_stop_server') as mock_stop:
        app.stop()

    mock_stop.assert_called_once()


def test_start_skips_server_when_no_service_enabled(
    tmp_path: Path,
) -> None:
    """No server starts when api, ui, and mcp are all disabled."""
    (tmp_path / 'startup.yml').write_text('[]')
    settings = _make_settings(
        tmp_path,
        ServerParameters(api_enabled=False, ui_enabled=False),
    )
    app = App(settings=settings, instance_hooks=_make_hooks(settings))

    with patch.object(App, '_start_server') as mock_start:
        app.start()

    mock_start.assert_not_called()


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

    assert server.should_exit is True
    assert server.force_exit is False
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

    assert server.should_exit is True
    assert server.force_exit is True
    assert thread.join.call_count == 2  # noqa: PLR2004
    thread.join.assert_any_call(timeout=App.SERVER_SHUTDOWN_TIMEOUT)
    thread.join.assert_any_call()


def test_server_shutdown_timeout_is_positive_int() -> None:
    """The shutdown timeout must be a positive int (uvicorn type)."""
    assert isinstance(App.SERVER_SHUTDOWN_TIMEOUT, int)
    assert App.SERVER_SHUTDOWN_TIMEOUT >= 1
