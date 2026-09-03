"""Definition of http output plugin."""

import asyncio
from collections.abc import Iterator, Mapping, Sequence
from typing import Any, override

import httpx

from eventum.plugins.exceptions import PluginConfigurationError
from eventum.plugins.output.base.plugin import OutputPlugin, OutputPluginParams
from eventum.plugins.output.exceptions import PluginOpenError, PluginWriteError
from eventum.plugins.output.http_auth import (
    AuthenticationError,
    HttpAuthenticator,
    HttpAuthenticatorParams,
    create_authenticator,
)
from eventum.plugins.output.http_client import (
    create_client,
    create_ssl_context,
)
from eventum.plugins.output.plugins.http.config import HttpOutputPluginConfig

_UNAUTHORIZED_STATUS = 401


class _FailedRequests:
    """Failures of the requests performed within a single write.

    Notes
    -----
    Failures are grouped by their message and status code, so the
    number of log lines a write produces is bound by the number of
    distinct failures instead of the number of events it carries.

    """

    def __init__(self) -> None:
        self._groups: dict[tuple[str, int | None], tuple[int, dict]] = {}

    def add(self, message: str, context: dict) -> None:
        """Add failure of a single request.

        Parameters
        ----------
        message : str
            Message of the failure.

        context : dict
            Context of the failure.

        """
        key = (message, context.get('http_status'))
        count, first_context = self._groups.get(key, (0, context))

        self._groups[key] = (count + 1, first_context)

    def groups(self) -> Iterator[tuple[str, int, dict]]:
        """Iterate over grouped failures.

        Yields
        ------
        tuple[str, int, dict]
            Message, number of failures in the group and context of the
            first failure in it.

        """
        for (message, _), (count, context) in self._groups.items():
            yield message, count, context


class HttpOutputPlugin(
    OutputPlugin[HttpOutputPluginConfig, OutputPluginParams],
):
    """Output plugin for sending events using HTTP requests."""

    @override
    def __init__(
        self,
        config: HttpOutputPluginConfig,
        params: OutputPluginParams,
    ) -> None:
        super().__init__(config, params)

        try:
            self._ssl_context = create_ssl_context(
                verify=config.verify,
                ca_cert=(
                    self.resolve_path(config.ca_cert)
                    if config.ca_cert
                    else None
                ),
                client_cert=(
                    self.resolve_path(config.client_cert)
                    if config.client_cert
                    else None
                ),
                client_key=(
                    self.resolve_path(config.client_cert_key)
                    if config.client_cert_key
                    else None
                ),
            )
        except OSError as e:
            msg = 'Failed to create SSL context'
            raise PluginConfigurationError(
                msg,
                context={'reason': str(e)},
            ) from e

        self._client: httpx.AsyncClient
        self._authenticator: HttpAuthenticator[Any] | None = None
        self._semaphore: asyncio.Semaphore

    @override
    async def _open(self) -> None:
        # the configured headers address the endpoint of this plugin,
        # so they travel the requests to it rather than the client the
        # authenticator also reaches its own endpoint through
        self._client = create_client(
            ssl_context=self._ssl_context,
            headers={},
            connect_timeout=self._config.connect_timeout,
            request_timeout=self._config.request_timeout,
            proxy_url=(
                str(self._config.proxy_url) if self._config.proxy_url else None
            ),
            max_connections=self._config.concurrency,
        )

        if self._config.auth is not None:
            # the plugin is not opened, so `_close` never runs and the
            # client would be left behind
            try:
                self._authenticator = create_authenticator(
                    config=self._config.auth,
                    params=HttpAuthenticatorParams(client=self._client),
                )
                await self._authenticator.open()
            except AuthenticationError as e:
                await self._client.aclose()

                msg = 'Failed to authenticate'
                raise PluginOpenError(msg, context=e.context) from None
            except BaseException:
                await self._client.aclose()
                raise

        # the semaphore belongs to the plugin and not to a single write,
        # so the bound holds when writes overlap
        self._semaphore = asyncio.Semaphore(self._config.concurrency)

    @override
    async def _close(self) -> None:
        if self._authenticator is not None:
            await self._authenticator.close()

        await self._client.aclose()

    async def _send_request(
        self,
        data: str,
    ) -> tuple[httpx.Response, Mapping[str, str]]:
        """Send a single request with authentication applied.

        Parameters
        ----------
        data : str
            Data for request.

        Returns
        -------
        tuple[httpx.Response, Mapping[str, str]]
            Response of the server, of any status code, and the
            authentication headers the request carried.

        Raises
        ------
        PluginWriteError
            If credentials cannot be acquired or the request failed.

        """
        credentials: Mapping[str, str] = {}

        if self._authenticator is not None:
            try:
                credentials = await self._authenticator.headers()
            except AuthenticationError as e:
                msg = 'Failed to authenticate'
                raise PluginWriteError(msg, context=e.context) from None

        try:
            response = await self._client.request(
                method=self._config.method,
                url=str(self._config.url),
                content=data,
                headers=dict(self._config.headers) | dict(credentials),
            )
        except httpx.RequestError as e:
            msg = 'Request failed'
            raise PluginWriteError(
                msg,
                context={
                    'reason': str(e),
                    'url': str(self._config.url),
                },
            ) from e

        return response, credentials

    async def _perform_request(self, data: str) -> None:
        """Perform request with provided data.

        Parameters
        ----------
        data : str
            Data for request.

        Raises
        ------
        PluginWriteError
            If request failed or response status code differs from
            expected one.

        """
        response, sent = await self._send_request(data)

        if response.status_code == self._config.success_code:
            return

        # a rejected credential is worth one more attempt, but only
        # once the expected status code is ruled out
        if (
            response.status_code == _UNAUTHORIZED_STATUS
            and self._authenticator is not None
            and await self._authenticator.handle_unauthorized(sent)
        ):
            response, _ = await self._send_request(data)

            if response.status_code == self._config.success_code:
                return

        content = await response.aread()
        text = content.decode()
        msg = 'Server returned not expected status code'
        raise PluginWriteError(
            msg,
            context={
                'http_status': response.status_code,
                'reason': text,
                'url': str(self._config.url),
            },
        )

    async def _perform_requests(
        self,
        events: Iterator[str],
        failures: _FailedRequests,
    ) -> int:
        """Perform requests for events until they are exhausted.

        Parameters
        ----------
        events : Iterator[str]
            Iterator of events, shared with the other concurrent
            callers.

        failures : _FailedRequests
            Collector of the failed requests.

        Returns
        -------
        int
            Number of events sent successfully.

        """
        sent = 0

        for event in events:
            try:
                async with self._semaphore:
                    await self._perform_request(event)
            except PluginWriteError as e:
                failures.add(str(e), e.context)
            except Exception as e:  # noqa: BLE001
                failures.add(
                    'Failed to perform request',
                    {'reason': str(e), 'url': str(self._config.url)},
                )
            else:
                sent += 1

        return sent

    async def _report_failures(self, failures: _FailedRequests) -> None:
        """Report grouped failures of the requests.

        Parameters
        ----------
        failures : _FailedRequests
            Collected failures of the requests.

        """
        await asyncio.gather(
            *[
                self._logger.aerror(message, count=count, **context)
                for message, count, context in failures.groups()
            ],
        )

    @override
    async def _write(self, events: Sequence[str]) -> int:
        failures = _FailedRequests()

        # events are pulled from a single iterator by a bound number of
        # tasks, so a batch of any size costs the same number of tasks
        # and requests in flight
        remaining_events = iter(events)
        senders_count = min(self._config.concurrency, len(events))

        async with asyncio.TaskGroup() as group:
            senders = [
                group.create_task(
                    self._perform_requests(remaining_events, failures),
                )
                for _ in range(senders_count)
            ]

        await self._report_failures(failures)

        return sum(sender.result() for sender in senders)
