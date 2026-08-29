"""Tests for the MCP instance-control tools."""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import yaml

from eventum.app.models.parameters.log import LogParameters
from eventum.app.models.parameters.path import PathParameters
from eventum.app.models.parameters.server import ServerParameters
from eventum.app.models.settings import Settings
from eventum.core.parameters import GenerationParameters
from eventum.mcp.context import ServerLiveContext
from eventum.mcp.errors import ToolFailure
from eventum.mcp.tools.instance import (
    get_instance_logs,
    restart_instance,
    stop_instance,
    update_settings,
)

_NEW_PORT = 8080


def _settings(tmp_path: Path) -> Settings:
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


def _ctx(
    tmp_path: Path,
    *,
    read_only: bool = False,
    hooks: Any = None,
    settings: Settings | None = None,
) -> ServerLiveContext:
    return ServerLiveContext(
        generators_dir=tmp_path / 'generators',
        read_only=read_only,
        manager=MagicMock(),
        startup=MagicMock(),
        generation=GenerationParameters(),
        logs_dir=tmp_path,
        log_format='plain',
        settings=settings if settings is not None else _settings(tmp_path),
        hooks=hooks if hooks is not None else MagicMock(),
        repositories=MagicMock(),
    )


# --- update_settings ---


async def test_update_settings_writes_patch(tmp_path: Path) -> None:
    """A valid patch is merged and written to the settings file."""
    path = tmp_path / 'eventum.yml'
    hooks = {'get_settings_file_path': lambda: path}
    ctx = _ctx(tmp_path, hooks=hooks)

    result = await update_settings(ctx, {'server': {'port': _NEW_PORT}})

    assert result == {'updated': True}
    written = yaml.safe_load(path.read_text())
    assert written['server']['port'] == _NEW_PORT


async def test_update_settings_read_only_blocked(tmp_path: Path) -> None:
    """A read-only server refuses to update settings."""
    ctx = _ctx(tmp_path, read_only=True)

    result = await update_settings(ctx, {'server': {'port': 8080}})

    assert isinstance(result, ToolFailure)


async def test_update_settings_rejects_auth_change(tmp_path: Path) -> None:
    """A patch touching server.auth is refused, file untouched."""
    path = tmp_path / 'eventum.yml'
    ctx = _ctx(tmp_path, hooks={'get_settings_file_path': lambda: path})

    result = await update_settings(
        ctx, {'server': {'auth': {'password': 'new'}}}
    )

    assert isinstance(result, ToolFailure)
    assert 'credentials' in result.error
    assert not path.exists()


async def test_update_settings_invalid_is_failure(tmp_path: Path) -> None:
    """A patch that fails validation returns a structured failure."""
    path = tmp_path / 'eventum.yml'
    ctx = _ctx(tmp_path, hooks={'get_settings_file_path': lambda: path})

    result = await update_settings(ctx, {'server': {'port': 0}})

    assert isinstance(result, ToolFailure)
    assert result.error == 'Invalid settings'
    assert not path.exists()


async def test_update_settings_path_resolution_failure(
    tmp_path: Path,
) -> None:
    """A failing path hook yields a structured failure."""

    def _raise() -> Path:
        msg = 'no path'
        raise RuntimeError(msg)

    ctx = _ctx(tmp_path, hooks={'get_settings_file_path': _raise})

    result = await update_settings(ctx, {'server': {'port': 8080}})

    assert isinstance(result, ToolFailure)


async def test_update_settings_write_failure(tmp_path: Path) -> None:
    """An unwritable destination yields a structured failure."""
    path = tmp_path / 'missing' / 'eventum.yml'  # parent does not exist
    ctx = _ctx(tmp_path, hooks={'get_settings_file_path': lambda: path})

    result = await update_settings(ctx, {'server': {'port': 8080}})

    assert isinstance(result, ToolFailure)


# --- stop_instance / restart_instance ---


async def test_stop_instance_calls_hook(tmp_path: Path) -> None:
    """Stopping invokes the terminate hook."""
    terminate = MagicMock()
    ctx = _ctx(tmp_path, hooks={'terminate': terminate})

    result = await stop_instance(ctx)

    assert result == {'stopping': True}
    terminate.assert_called_once()


async def test_stop_instance_read_only_blocked(tmp_path: Path) -> None:
    """A read-only server refuses to stop the instance."""
    terminate = MagicMock()
    ctx = _ctx(tmp_path, read_only=True, hooks={'terminate': terminate})

    result = await stop_instance(ctx)

    assert isinstance(result, ToolFailure)
    terminate.assert_not_called()


async def test_stop_instance_hook_failure(tmp_path: Path) -> None:
    """A failing terminate hook yields a structured failure."""

    def _raise() -> None:
        msg = 'boom'
        raise RuntimeError(msg)

    ctx = _ctx(tmp_path, hooks={'terminate': _raise})

    result = await stop_instance(ctx)

    assert isinstance(result, ToolFailure)


async def test_restart_instance_calls_hook(tmp_path: Path) -> None:
    """Restarting invokes the restart hook."""
    restart = MagicMock()
    ctx = _ctx(tmp_path, hooks={'restart': restart})

    result = await restart_instance(ctx)

    assert result == {'restarting': True}
    restart.assert_called_once()


async def test_restart_instance_read_only_blocked(tmp_path: Path) -> None:
    """A read-only server refuses to restart the instance."""
    restart = MagicMock()
    ctx = _ctx(tmp_path, read_only=True, hooks={'restart': restart})

    result = await restart_instance(ctx)

    assert isinstance(result, ToolFailure)
    restart.assert_not_called()


# --- get_instance_logs ---


async def test_get_instance_logs_reads_the_channel(tmp_path: Path) -> None:
    """Each channel is read from the file of its own."""
    (tmp_path / 'main.log').write_text('Started\n', encoding='utf-8')
    (tmp_path / 'server_access.log').write_text(
        '127.0.0.1:5316 - "GET /api/instance/info HTTP/1.1" 200\n',
        encoding='utf-8',
    )
    ctx = _ctx(tmp_path)

    assert await get_instance_logs(ctx) == {
        'channel': 'main',
        'lines': ['Started'],
    }
    assert await get_instance_logs(ctx, 'server_access') == {
        'channel': 'server_access',
        'lines': ['127.0.0.1:5316 - "GET /api/instance/info HTTP/1.1" 200'],
    }


async def test_get_instance_logs_of_silent_channel(tmp_path: Path) -> None:
    """A channel that has logged nothing reads as empty."""
    ctx = _ctx(tmp_path)

    assert await get_instance_logs(ctx, 'mcp') == {
        'channel': 'mcp',
        'lines': [],
    }


async def test_get_instance_logs_keeps_the_requested_tail(
    tmp_path: Path,
) -> None:
    """Only the requested number of trailing lines is returned."""
    (tmp_path / 'main.log').write_text(
        ''.join(f'line {i}\n' for i in range(10)),
        encoding='utf-8',
    )
    ctx = _ctx(tmp_path)

    result = await get_instance_logs(ctx, 'main', 2)

    assert result == {'channel': 'main', 'lines': ['line 8', 'line 9']}


async def test_get_instance_logs_scrubs_paths_and_password(
    tmp_path: Path,
) -> None:
    """Paths and the server password never reach the agent."""
    settings = _settings(tmp_path)
    (tmp_path / 'main.log').write_text(
        f'Loaded {tmp_path / "generators" / "demo" / "generator.yml"} '
        f'with {settings.server.auth.password}\n',
        encoding='utf-8',
    )
    ctx = _ctx(tmp_path, settings=settings)

    result = await get_instance_logs(ctx)

    assert isinstance(result, dict)
    line = result['lines'][0]
    assert str(tmp_path) not in line
    assert settings.server.auth.password not in line
    assert 'demo/generator.yml' in line
