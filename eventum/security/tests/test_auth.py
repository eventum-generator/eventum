"""Tests for shared Basic-auth credential verification."""

import base64

from eventum.security.auth import verify_basic_credentials


def _encode(user: str, password: str) -> str:
    return base64.b64encode(f'{user}:{password}'.encode()).decode()


def test_returns_username_on_match() -> None:
    """Matching credentials return the username."""
    assert verify_basic_credentials(_encode('u', 'p'), 'u', 'p') == 'u'


def test_wrong_password_returns_none() -> None:
    """A wrong password yields None."""
    assert verify_basic_credentials(_encode('u', 'x'), 'u', 'p') is None


def test_wrong_user_returns_none() -> None:
    """A wrong username yields None."""
    assert verify_basic_credentials(_encode('x', 'p'), 'u', 'p') is None


def test_invalid_base64_returns_none() -> None:
    """An invalid base64 token yields None, not an error."""
    assert verify_basic_credentials('a', 'u', 'p') is None


def test_undecodable_token_returns_none() -> None:
    """A token that is not valid UTF-8 yields None, not an error."""
    token = base64.b64encode(b'\xff:\xff').decode()
    assert verify_basic_credentials(token, 'u', 'p') is None


def test_non_ascii_credentials_return_none() -> None:
    """Non-ASCII credentials are rejected without crashing."""
    assert verify_basic_credentials(_encode('us\xe9r', 'p'), 'u', 'p') is None


def test_no_colon_token_returns_none() -> None:
    """A token without a colon parses as an empty password."""
    token = base64.b64encode(b'admin').decode()
    assert verify_basic_credentials(token, 'admin', 'p') is None


def test_empty_credentials_return_none() -> None:
    """Empty credentials do not match non-empty expected ones."""
    assert verify_basic_credentials(_encode('', ''), 'u', 'p') is None


def test_empty_token_returns_none() -> None:
    """An empty token yields None."""
    assert verify_basic_credentials('', 'u', 'p') is None
