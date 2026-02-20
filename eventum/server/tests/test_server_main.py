"""Tests for server application builder."""

from unittest.mock import MagicMock, patch

from fastapi import FastAPI

from eventum.server.main import build_server_app


def _make_deps():
    manager = MagicMock()
    settings = MagicMock()
    hooks = {
        'get_settings_file_path': MagicMock(),
        'terminate': MagicMock(),
        'restart': MagicMock(),
    }
    return manager, settings, hooks


@patch(
    'eventum.server.main.inject_ui_service',
    new_callable=lambda: MagicMock,
    create=True,
)
@patch(
    'eventum.server.main.inject_api_service',
    new_callable=lambda: MagicMock,
    create=True,
)
def test_build_no_services(mock_api, mock_ui):
    manager, settings, hooks = _make_deps()
    app = build_server_app(
        enabled_services={},
        generator_manager=manager,
        settings=settings,
        instance_hooks=hooks,
    )
    assert isinstance(app, FastAPI)


def test_build_api_only():
    manager, settings, hooks = _make_deps()
    with patch(
        'eventum.server.services.api.injector.inject_service',
    ) as mock_inject:
        app = build_server_app(
            enabled_services={'api': True},
            generator_manager=manager,
            settings=settings,
            instance_hooks=hooks,
        )
        mock_inject.assert_called_once()
    assert isinstance(app, FastAPI)


def test_build_ui_only():
    manager, settings, hooks = _make_deps()
    with patch(
        'eventum.server.services.ui.injector.inject_service',
    ) as mock_inject:
        app = build_server_app(
            enabled_services={'ui': True},
            generator_manager=manager,
            settings=settings,
            instance_hooks=hooks,
        )
        mock_inject.assert_called_once()
    assert isinstance(app, FastAPI)


def test_build_both_services():
    manager, settings, hooks = _make_deps()
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
            instance_hooks=hooks,
        )
        mock_api.assert_called_once()
        mock_ui.assert_called_once()
    assert isinstance(app, FastAPI)
