"""Helper functions for http based output plugins."""

import ssl
from typing import Any

import httpx

from eventum.plugins.output.ssl import create_ssl_context

__all__ = ['create_client', 'create_ssl_context']


def create_client(  # noqa: PLR0913
    ssl_context: ssl.SSLContext | None = None,
    username: str | None = None,
    password: str | None = None,
    headers: dict[str, Any] | None = None,
    connect_timeout: int = 10,
    request_timeout: int = 300,
    proxy_url: str | None = None,
) -> httpx.AsyncClient:
    """Create HTTP client with initialized parameters.

    Parameters
    ----------
    ssl_context : ssl.SSLContext | None, default=None
        SSL context for session.

    username : str | None, default=None
        Username used in basic auth.

    password : str | None, default=None
        Password for user used in basic auth, can be `None` with
        provided `username` (in this case empty string will be used).

    headers : dict[str, Any] | None, default=None
        Headers to set in session.

    connect_timeout : int, default=10
        Timeout of connection to host.

    request_timeout : int, default=300
        Timeout of requests.

    proxy_url : str | None, default=None
        Proxy url.

    Returns
    -------
    httpx.AsyncClient
        Initialized HTTP client.

    """
    ssl_context = ssl_context or ssl.create_default_context()

    if username is None:
        auth: httpx.BasicAuth | None = None
    else:
        auth = httpx.BasicAuth(username, password or '')

    if proxy_url is None:
        proxy: httpx.Proxy | None = None
    else:
        proxy = httpx.Proxy(proxy_url)

    return httpx.AsyncClient(
        auth=auth,
        headers=headers,
        verify=ssl_context,
        timeout=httpx.Timeout(request_timeout, connect=connect_timeout),
        proxy=proxy,
    )
