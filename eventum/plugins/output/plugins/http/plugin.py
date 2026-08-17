"""Definition of http output plugin."""

import asyncio
from collections.abc import Iterator, Sequence
from typing import override

import httpx

from eventum.plugins.exceptions import PluginConfigurationError
from eventum.plugins.output.base.plugin import OutputPlugin, OutputPluginParams
from eventum.plugins.output.exceptions import PluginWriteError
from eventum.plugins.output.http_client import (
    create_client,
    create_ssl_context,
)
from eventum.plugins.output.plugins.http.config import HttpOutputPluginConfig


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
        self._semaphore: asyncio.Semaphore

    @override
    async def _open(self) -> None:
        self._client = create_client(
            ssl_context=self._ssl_context,
            username=self._config.username,
            password=self._config.password,
            headers=self._config.headers,
            connect_timeout=self._config.connect_timeout,
            request_timeout=self._config.request_timeout,
            proxy_url=(
                str(self._config.proxy_url) if self._config.proxy_url else None
            ),
            max_connections=self._config.concurrency,
        )

        # the semaphore belongs to the plugin and not to a single write,
        # so the bound holds when writes overlap
        self._semaphore = asyncio.Semaphore(self._config.concurrency)

    @override
    async def _close(self) -> None:
        await self._client.aclose()

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
        try:
            response = await self._client.request(
                method=self._config.method,
                url=str(self._config.url),
                content=data,
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

        if response.status_code != self._config.success_code:
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
