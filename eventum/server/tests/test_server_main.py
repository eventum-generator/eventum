"""Tests for server application builder."""

from typing import Any
from unittest.mock import MagicMock, patch

from fastapi import FastAPI

from eventum.server.main import build_server_app


def _make_deps() -> tuple[MagicMock, MagicMock, dict[str, Any], MagicMock]:
    manager = MagicMock()
    settings = MagicMock()
    hooks = {
        'get_settings_file_path': MagicMock(),
        'terminate': MagicMock(),
        'restart': MagicMock(),
    }
    startup = MagicMock()
    return manager, settings, hooks, startup


def test_build_no_services() -> None:
    """No injector is called when no service is enabled."""
    manager, settings, hooks, startup = _make_deps()
    with (
        patch(
            'eventum.server.services.api.injector.inject_service',
        ) as mock_api,
        patch(
            'eventum.server.services.ui.injector.inject_service',
        ) as mock_ui,
        patch(
            'eventum.server.services.mcp.injector.inject_service',
        ) as mock_mcp,
    ):
        app = build_server_app(
            enabled_services={},
            generator_manager=manager,
            settings=settings,
            instance_hooks=hooks,  # type: ignore[arg-type]
            startup=startup,
        )
        mock_api.assert_not_called()
        mock_ui.assert_not_called()
        mock_mcp.assert_not_called()
    assert isinstance(app, FastAPI)


def test_build_api_only() -> None:
    """Only the API injector runs when only the API is enabled."""
    manager, settings, hooks, startup = _make_deps()
    with patch(
        'eventum.server.services.api.injector.inject_service',
    ) as mock_inject:
        app = build_server_app(
            enabled_services={'api': True},
            generator_manager=manager,
            settings=settings,
            instance_hooks=hooks,  # type: ignore[arg-type]
            startup=startup,
        )
        mock_inject.assert_called_once()
    assert isinstance(app, FastAPI)


def test_build_ui_only() -> None:
    """Only the UI injector runs when only the UI is enabled."""
    manager, settings, hooks, startup = _make_deps()
    with patch(
        'eventum.server.services.ui.injector.inject_service',
    ) as mock_inject:
        app = build_server_app(
            enabled_services={'ui': True},
            generator_manager=manager,
            settings=settings,
            instance_hooks=hooks,  # type: ignore[arg-type]
            startup=startup,
        )
        mock_inject.assert_called_once()
    assert isinstance(app, FastAPI)


def test_build_mcp_only() -> None:
    """Only the MCP injector runs when only MCP is enabled."""
    manager, settings, hooks, startup = _make_deps()
    with patch(
        'eventum.server.services.mcp.injector.inject_service',
    ) as mock_inject:
        app = build_server_app(
            enabled_services={'mcp': True},
            generator_manager=manager,
            settings=settings,
            instance_hooks=hooks,  # type: ignore[arg-type]
            startup=startup,
        )
        mock_inject.assert_called_once()
    assert isinstance(app, FastAPI)


def test_build_both_services() -> None:
    """API and UI injectors both run when both are enabled."""
    manager, settings, hooks, startup = _make_deps()
    with (
        patch(
            'eventum.server.services.api.injector.inject_service',
        ) as mock_api,
        patch(
            'eventum.server.services.ui.injector.inject_service',
        ) as mock_ui,
    ):
        app = build_server_app(
            enabled_services={'api': True, 'ui': True},
            generator_manager=manager,
            settings=settings,
            instance_hooks=hooks,  # type: ignore[arg-type]
            startup=startup,
        )
        mock_api.assert_called_once()
        mock_ui.assert_called_once()
    assert isinstance(app, FastAPI)


def test_build_injects_mcp_before_ui() -> None:
    """MCP is injected before the UI SPA catch-all can shadow it."""
    manager, settings, hooks, startup = _make_deps()
    order: list[str] = []
    with (
        patch(
            'eventum.server.services.ui.injector.inject_service',
            side_effect=lambda *_, **__: order.append('ui'),
        ),
        patch(
            'eventum.server.services.mcp.injector.inject_service',
            side_effect=lambda *_, **__: order.append('mcp'),
        ),
    ):
        build_server_app(
            enabled_services={'ui': True, 'mcp': True},
            generator_manager=manager,
            settings=settings,
            instance_hooks=hooks,  # type: ignore[arg-type]
            startup=startup,
        )
    assert order == ['mcp', 'ui']
