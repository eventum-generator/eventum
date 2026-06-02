"""Definition of clickhouse output plugin."""

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, override

from clickhouse_connect import get_async_client
from clickhouse_connect.driver.binding import quote_identifier as quote
from clickhouse_connect.driver.httputil import get_pool_manager

from eventum.plugins.output.base.plugin import OutputPlugin, OutputPluginParams
from eventum.plugins.output.exceptions import PluginOpenError, PluginWriteError
from eventum.plugins.output.plugins.clickhouse.config import (
    ClickhouseOutputPluginConfig,
)

if TYPE_CHECKING:
    from clickhouse_connect.driver.asyncclient import AsyncClient
    from urllib3.poolmanager import PoolManager


class ClickhouseOutputPlugin(
    OutputPlugin[ClickhouseOutputPluginConfig, OutputPluginParams],
):
    """Output plugin for indexing events to ClickHouse."""

    @override
    def __init__(
        self,
        config: ClickhouseOutputPluginConfig,
        params: OutputPluginParams,
    ) -> None:
        super().__init__(config, params)

        self._fq_table_name = '.'.join(
            [quote(config.database), quote(config.table)],
        )
        self._client: AsyncClient
        self._pool_mgr: PoolManager

    def _create_pool_manager(self) -> PoolManager:
        """Create urllib3 pool manager sized for concurrent writes.

        Notes
        -----
        `clickhouse_connect.get_async_client` builds its own pool
        manager with `maxsize=8` by default, which becomes a bottleneck
        under Eventum's concurrent output writes. When a custom
        `pool_mgr` is passed, TLS and proxy options must be configured
        on the pool itself - the client skips applying them otherwise.

        """
        options: dict[str, Any] = {
            'maxsize': self._config.pool_maxsize,
            'verify': self._config.verify,
        }
        if self._config.ca_cert is not None:
            options['ca_cert'] = str(self.resolve_path(self._config.ca_cert))
        if self._config.client_cert is not None:
            options['client_cert'] = str(
                self.resolve_path(self._config.client_cert),
            )
        if self._config.client_cert_key is not None:
            options['client_cert_key'] = str(
                self.resolve_path(self._config.client_cert_key),
            )
        if self._config.server_host_name is not None:
            if self._config.verify:
                options['assert_hostname'] = self._config.server_host_name
            options['server_hostname'] = self._config.server_host_name
        if self._config.proxy_url is not None:
            proxy_url = str(self._config.proxy_url)
            if self._config.protocol == 'https':
                options['https_proxy'] = proxy_url
            else:
                options['http_proxy'] = proxy_url

        return get_pool_manager(**options)

    @override
    async def _open(self) -> None:
        try:
            self._pool_mgr = self._create_pool_manager()
            self._client = await get_async_client(
                host=self._config.host,
                port=self._config.port,
                interface=self._config.protocol,
                database=self._config.database,
                username=self._config.username,
                password=self._config.password,
                dsn=str(self._config.dsn) if self._config.dsn else None,
                connect_timeout=self._config.connect_timeout,
                send_receive_timeout=self._config.request_timeout,
                client_name=self._config.client_name,
                verify=self._config.verify,
                client_cert=(
                    self.resolve_path(self._config.client_cert)
                    if self._config.client_cert
                    else None
                ),
                client_cert_key=(
                    self.resolve_path(self._config.client_cert_key)
                    if self._config.client_cert_key
                    else None
                ),
                tls_mode=self._config.tls_mode,
                pool_mgr=self._pool_mgr,
            )
        except Exception as e:
            msg = 'Cannot initialize ClickHouse client'
            raise PluginOpenError(
                msg,
                context={'reason': str(e)},
            ) from e

        await self._logger.ainfo('ClickHouse client is initialized')

    @override
    async def _close(self) -> None:
        await self._client.close()
        self._pool_mgr.clear()

    @override
    async def _write(self, events: Sequence[str]) -> int:
        try:
            result = await self._client.raw_insert(
                table=self._fq_table_name,
                insert_block=(
                    self._config.header
                    + self._config.separator.join(events)
                    + self._config.footer
                ),
                fmt=self._config.input_format,
            )
        except Exception as e:
            msg = 'Failed to insert events to ClickHouse'
            raise PluginWriteError(
                msg,
                context={
                    'reason': str(e),
                    'host': self._config.host,
                },
            ) from e
        else:
            return result.written_rows
