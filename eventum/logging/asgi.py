"""Log attribution of served requests.

A request runs in a context of its own that does not inherit the one
bound on the serving thread, so whatever attributes the records of a
served request is bound per request.
"""

from typing import TYPE_CHECKING

from eventum.logging.channels import LogContext, bind_log_context

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Receive, Scope, Send


class LogContextMiddleware:
    """Middleware that binds log context to the requests of an app."""

    def __init__(self, app: ASGIApp, context: LogContext) -> None:
        """Wrap ``app``, attributing its records to ``context``.

        Parameters
        ----------
        app : ASGIApp
            Application to wrap.

        context : LogContext
            Context to bind, either declared for the app (a component)
            or captured from whoever runs it.

        """
        self._app = app
        self._context = context

    async def __call__(
        self, scope: Scope, receive: Receive, send: Send
    ) -> None:
        """Bind the context and pass the request through.

        The address of the client is bound along with it, so every
        record of a request names the caller that caused it.
        """
        bind_log_context(self._context)

        client = scope.get('client')
        if client is not None:
            bind_log_context({'client_host': client[0]})

        await self._app(scope, receive, send)
