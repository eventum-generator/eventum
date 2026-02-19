"""Authorization dependencies."""

import base64
import secrets
from typing import Annotated

from fastapi import Depends, HTTPException, Request, WebSocket, status
from fastapi.security import HTTPBasic
from fastapi.security.utils import get_authorization_scheme_param

from eventum.api.dependencies.app import SettingsDep
from eventum.api.utils.response_description import set_responses
from eventum.app.models.settings import Settings

security = HTTPBasic()

type _SessionID = str
type _Username = str

_sessions: dict[_SessionID, _Username] = {}


def set_session(session_id: str, user: str) -> None:
    """Set session for authenticated user.

    Parameters
    ----------
    session_id : str
        Session ID.

    user : str
        Authenticated user.

    """
    _sessions[session_id] = user


def clear_session(session_id: str) -> None:
    """Clear specified session.

    Parameters
    ----------
    session_id : str
        Session ID to clear.

    """
    _sessions.pop(session_id, None)


def get_session_user(session_id: str) -> str | None:
    """Get user of session.

    Parameters
    ----------
    session_id : str
        Session ID.

    Returns
    -------
    str | None
        User name or `None` if session is missing.

    """
    return _sessions.get(session_id)


def clear_all_sessions() -> None:
    """Clear all set sessions."""
    _sessions.clear()


def check_auth(
    context: Request | WebSocket,
    settings: Settings,
) -> str:
    """Check authentication.

    Parameters
    ----------
    context : Request | WebSocket
        Request or WebSocket context.

    settings : Settings
        App settings with correct user and password.

    Returns
    -------
    str
        Authenticated username.

    Raises
    ------
    HTTPException
        If authentication fails.

    """
    # Check basic auth first
    auth_header = context.headers.get('Authorization')

    if auth_header is not None:
        scheme, param = get_authorization_scheme_param(auth_header)

        if scheme != 'Basic':
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f'{scheme} authorization is not supported',
            )

        decoded = base64.b64decode(param).decode()
        username, _, password = decoded.partition(':')

        is_correct_username = secrets.compare_digest(
            username.encode(),
            settings.server.auth.user.encode(),
        )

        is_correct_password = secrets.compare_digest(
            password.encode(),
            settings.server.auth.password.encode(),
        )

        if not (is_correct_username and is_correct_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Incorrect username or password',
            )

        return username

    # Check session cookie then
    session_cookie = context.cookies.get('session_id')

    if session_cookie is not None:
        session_username = get_session_user(session_cookie)

        if session_username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Session is missing or expired',
            )

        return session_username

    # Unauthorized fallback
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail='Authorization header or session cookie must be provided',
    )


@set_responses({401: {'description': 'Authentication fails'}})
async def check_http_auth(request: Request, settings: SettingsDep) -> str:
    """Check authentication with HTTP request context.

    Parameters
    ----------
    request : Request
        HTTP Request.

    settings : SettingsDep
        Settings dependency with correct user and password.

    Returns
    -------
    str
        Authenticated username.

    Raises
    ------
    HTTPException
        If authentication fails.

    """
    return check_auth(context=request, settings=settings)


HttpAuthDepends = Depends(check_http_auth)
HttpAuthDep = Annotated[str, HttpAuthDepends]


async def check_websocket_auth(
    websocket: WebSocket,
    settings: SettingsDep,
) -> str:
    """Check authentication with WebSocket request context.

    Parameters
    ----------
    websocket : WebSocket
        WebSocket.

    settings : SettingsDep
        Settings dependency with correct user and password.

    Returns
    -------
    str
        Authenticated username.

    Raises
    ------
    HTTPException
        If authentication fails.

    """
    return check_auth(context=websocket, settings=settings)


WebsocketAuthDepends = Depends(check_websocket_auth)
WebsocketAuthDep = Annotated[str, WebsocketAuthDepends]
