"""Unit tests for authentication dependencies."""

import pytest
from fastapi import HTTPException

from eventum.api.dependencies.authentication import (
    check_auth,
    clear_all_sessions,
    clear_session,
    get_session_user,
    set_session,
)
from eventum.app.models.parameters.server import (
    AuthParameters,
    ServerParameters,
)


class _FakeContext:
    """Minimal fake for Request/WebSocket with headers and cookies."""

    def __init__(self, headers=None, cookies=None):
        self.headers = headers or {}
        self.cookies = cookies or {}


def _make_settings():
    from unittest.mock import MagicMock

    settings = MagicMock()
    settings.server = ServerParameters(
        auth=AuthParameters(user='admin', password='secret'),
    )
    return settings


# --- Session management ---


def test_set_and_get_session():
    set_session('sess1', 'alice')
    assert get_session_user('sess1') == 'alice'
    clear_session('sess1')


def test_get_session_user_missing():
    assert get_session_user('nonexistent') is None


def test_clear_session():
    set_session('sess2', 'bob')
    clear_session('sess2')
    assert get_session_user('sess2') is None


def test_clear_all_sessions():
    set_session('s1', 'u1')
    set_session('s2', 'u2')
    clear_all_sessions()
    assert get_session_user('s1') is None
    assert get_session_user('s2') is None


# --- check_auth ---


def test_check_auth_basic_valid():
    import base64

    creds = base64.b64encode(b'admin:secret').decode()
    ctx = _FakeContext(headers={'Authorization': f'Basic {creds}'})
    settings = _make_settings()
    result = check_auth(ctx, settings)
    assert result == 'admin'


def test_check_auth_basic_wrong_creds():
    import base64

    creds = base64.b64encode(b'admin:wrong').decode()
    ctx = _FakeContext(headers={'Authorization': f'Basic {creds}'})
    settings = _make_settings()
    with pytest.raises(HTTPException) as exc_info:
        check_auth(ctx, settings)
    assert exc_info.value.status_code == 401
    assert 'Incorrect' in exc_info.value.detail


def test_check_auth_unsupported_scheme():
    ctx = _FakeContext(headers={'Authorization': 'Bearer sometoken'})
    settings = _make_settings()
    with pytest.raises(HTTPException) as exc_info:
        check_auth(ctx, settings)
    assert exc_info.value.status_code == 401
    assert 'not supported' in exc_info.value.detail


def test_check_auth_session_cookie():
    set_session('valid_session', 'alice')
    ctx = _FakeContext(cookies={'session_id': 'valid_session'})
    settings = _make_settings()
    result = check_auth(ctx, settings)
    assert result == 'alice'
    clear_session('valid_session')


def test_check_auth_expired_session():
    ctx = _FakeContext(cookies={'session_id': 'expired_id'})
    settings = _make_settings()
    with pytest.raises(HTTPException) as exc_info:
        check_auth(ctx, settings)
    assert exc_info.value.status_code == 401


def test_check_auth_no_auth():
    ctx = _FakeContext()
    settings = _make_settings()
    with pytest.raises(HTTPException) as exc_info:
        check_auth(ctx, settings)
    assert exc_info.value.status_code == 401
