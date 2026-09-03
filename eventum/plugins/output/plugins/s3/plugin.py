"""Definition of s3 output plugin."""

import asyncio
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, override

if TYPE_CHECKING:
    import pyarrow as pa
    from obstore.store import (
        ClientConfig,
        RetryConfig,
        S3Config,
        S3Store,
    )

from eventum.plugins.output.base.plugin import OutputPlugin, OutputPluginParams
from eventum.plugins.output.exceptions import PluginOpenError, PluginWriteError
from eventum.plugins.output.plugins.s3.config import (
    ParquetEncoderConfig,
    S3OutputPluginConfig,
)
from eventum.plugins.output.plugins.s3.encoding import (
    EncodingError,
    content_type_of,
    encode,
    extension_of,
    read_schema,
)
from eventum.plugins.output.plugins.s3.keys import render_key
from eventum.utils.net_accounting import record_sent


class S3OutputPlugin(
    OutputPlugin[S3OutputPluginConfig, OutputPluginParams],
):
    """Output plugin for writing events to S3 compatible storage.

    Notes
    -----
    Every batch of events becomes one object, since an object cannot be
    appended to once it is created. The size of objects therefore
    follows the batch parameters of the generator.

    """

    @override
    def __init__(
        self,
        config: S3OutputPluginConfig,
        params: OutputPluginParams,
    ) -> None:
        super().__init__(config, params)

        self._store: S3Store

        self._schema: pa.Schema | None = None
        self._sequence = 0

        self._extension = extension_of(config.encoder)
        self._content_type = config.content_type or content_type_of(
            config.encoder,
        )

        self._endpoint = (
            None
            if config.endpoint_url is None
            else str(config.endpoint_url).rstrip('/')
        )

        self._ca_cert_path = (
            None
            if config.ca_cert is None
            else self.resolve_path(config.ca_cert)
        )

        encoder = config.encoder
        self._schema_path: Path | None = None

        if (
            isinstance(encoder, ParquetEncoderConfig)
            and encoder.schema_path is not None
        ):
            self._schema_path = self.resolve_path(encoder.schema_path)

    def _build_client_config(self) -> ClientConfig:
        """Build config of the HTTP client of the store.

        Returns
        -------
        ClientConfig
            Client config.

        Raises
        ------
        OSError
            If CA certificate cannot be read.

        """
        config: ClientConfig = {
            'connect_timeout': timedelta(seconds=self._config.connect_timeout),
            'timeout': timedelta(seconds=self._config.request_timeout),
            # a custom endpoint is commonly plain http on a local
            # network, and the client refuses it unless allowed
            'allow_http': self._endpoint is not None
            and self._endpoint.startswith('http://'),
            'allow_invalid_certificates': not self._config.verify,
        }

        if self._ca_cert_path is not None:
            config['root_certificate'] = self._ca_cert_path.read_bytes()

        if self._config.proxy_url is not None:
            config['proxy_url'] = str(self._config.proxy_url)

        return config

    def _build_store_config(self) -> S3Config:
        """Build config of the store.

        Returns
        -------
        S3Config
            Store config.

        Notes
        -----
        Credentials are left out when they are not configured, so the
        store resolves them from the environment on its own.

        """
        config: S3Config = {
            'bucket': self._config.bucket,
            'region': self._config.region,
        }

        if self._endpoint is not None:
            config['endpoint'] = self._endpoint

        match self._config.addressing_style:
            case 'auto':
                # a custom endpoint rarely resolves a per bucket host
                config['virtual_hosted_style_request'] = self._endpoint is None
            case 'path':
                config['virtual_hosted_style_request'] = False
            case 'virtual':
                config['virtual_hosted_style_request'] = True

        if self._config.access_key_id is not None:
            config['access_key_id'] = self._config.access_key_id

        if self._config.secret_access_key is not None:
            config['secret_access_key'] = self._config.secret_access_key

        if self._config.session_token is not None:
            config['session_token'] = self._config.session_token

        return config

    @override
    async def _open(self) -> None:
        # the storage client and the columnar encoder are heavy, so they
        # are loaded when a generator opens this plugin instead of when
        # the plugin module is imported to build the config types
        from obstore.exceptions import BaseError as ObjectStoreError
        from obstore.store import S3Store

        if self._schema_path is not None:
            try:
                self._schema = await asyncio.to_thread(
                    read_schema,
                    self._schema_path,
                )
            except OSError as e:
                msg = 'Failed to read schema of objects'
                raise PluginOpenError(
                    msg,
                    context={
                        'reason': str(e),
                        'file_path': str(self._schema_path),
                    },
                ) from e
            except EncodingError as e:
                msg = 'Failed to infer schema of objects'
                raise PluginOpenError(
                    msg,
                    context={
                        'reason': str(e),
                        'file_path': str(self._schema_path),
                    },
                ) from None

        try:
            client_config = self._build_client_config()
        except OSError as e:
            msg = 'Failed to read CA certificate'
            raise PluginOpenError(
                msg,
                context={
                    'reason': str(e),
                    'file_path': str(self._ca_cert_path),
                },
            ) from e

        retry_config: RetryConfig = {'max_retries': self._config.max_retries}

        try:
            self._store = S3Store(
                config=self._build_store_config(),
                client_options=client_config,
                retry_config=retry_config,
            )
        except (ObjectStoreError, ValueError) as e:
            msg = 'Failed to initialize object storage client'
            raise PluginOpenError(
                msg,
                context={
                    'reason': str(e),
                    'bucket': self._config.bucket,
                },
            ) from None

    @override
    async def _close(self) -> None:
        # nothing is buffered between writes and the store exposes no
        # release of its own, so there is nothing to do here
        return

    @override
    async def _write(self, events: Sequence[str]) -> int:
        import obstore
        from obstore.exceptions import BaseError as ObjectStoreError

        key = render_key(
            self._config.key_template,
            moment=datetime.now(tz=UTC),
            sequence=self._sequence,
            extension=self._extension,
        )
        self._sequence += 1

        try:
            body = await asyncio.to_thread(
                encode,
                events,
                self._config.encoder,
                self._schema,
            )
        except EncodingError as e:
            msg = 'Failed to encode events'
            raise PluginWriteError(
                msg,
                context={
                    'reason': str(e),
                    'bucket': self._config.bucket,
                    'object_key': key,
                },
            ) from None

        try:
            await obstore.put_async(
                self._store,
                key,
                body,
                attributes={'Content-Type': self._content_type},
            )
        # the client maps part of the storage errors onto the builtin
        # OS exceptions - a missing bucket arrives as FileNotFoundError -
        # and rejects a key it cannot parse with a bare ValueError
        except (ObjectStoreError, OSError, ValueError) as e:
            msg = 'Failed to write object'
            raise PluginWriteError(
                msg,
                context={
                    'reason': str(e),
                    'bucket': self._config.bucket,
                    'object_key': key,
                    'size': len(body),
                },
            ) from None

        # the client moves its bytes outside python sockets, so the
        # traffic is reported to the accounting explicitly
        record_sent(len(body))

        # logged without awaiting: a cancellation at this point would
        # count an object that already landed as failed
        self._logger.debug(
            'Object is written',
            bucket=self._config.bucket,
            object_key=key,
            size=len(body),
            count=len(events),
        )

        return len(events)
