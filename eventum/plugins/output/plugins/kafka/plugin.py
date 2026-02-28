"""Definition of kafka output plugin."""

import asyncio
import ssl
from collections.abc import Sequence
from typing import override

from aiokafka import AIOKafkaProducer

from eventum.plugins.exceptions import PluginConfigurationError
from eventum.plugins.output.base.plugin import OutputPlugin, OutputPluginParams
from eventum.plugins.output.exceptions import PluginOpenError
from eventum.plugins.output.plugins.kafka.config import KafkaOutputPluginConfig
from eventum.plugins.output.ssl import create_ssl_context


class KafkaOutputPlugin(
    OutputPlugin[KafkaOutputPluginConfig, OutputPluginParams],
):
    """Output plugin for producing events to Apache Kafka topics."""

    @override
    def __init__(
        self,
        config: KafkaOutputPluginConfig,
        params: OutputPluginParams,
    ) -> None:
        super().__init__(config, params)

        self._key_bytes: bytes | None = (
            config.key.encode(config.encoding) if config.key else None
        )
        self._acks: int | str = 'all' if config.acks == -1 else config.acks

        self._ssl_context: ssl.SSLContext | None = None

        if config.security_protocol in ('SSL', 'SASL_SSL'):
            try:
                self._ssl_context = create_ssl_context(
                    verify=True,
                    ca_cert=(
                        self.resolve_path(config.ssl_cafile)
                        if config.ssl_cafile
                        else None
                    ),
                    client_cert=(
                        self.resolve_path(config.ssl_certfile)
                        if config.ssl_certfile
                        else None
                    ),
                    client_key=(
                        self.resolve_path(config.ssl_keyfile)
                        if config.ssl_keyfile
                        else None
                    ),
                )
            except OSError as e:
                msg = 'Failed to create SSL context'
                raise PluginConfigurationError(
                    msg,
                    context={'reason': str(e)},
                ) from e

        self._producer: AIOKafkaProducer

    @override
    async def _open(self) -> None:
        try:
            self._producer = AIOKafkaProducer(
                bootstrap_servers=self._config.bootstrap_servers,  # type: ignore[arg-type]
                client_id=self._config.client_id,
                metadata_max_age_ms=self._config.metadata_max_age_ms,
                request_timeout_ms=self._config.request_timeout_ms,
                connections_max_idle_ms=(self._config.connections_max_idle_ms),
                acks=self._acks,
                compression_type=self._config.compression_type,
                max_batch_size=self._config.max_batch_size,
                max_request_size=self._config.max_request_size,
                linger_ms=self._config.linger_ms,
                retry_backoff_ms=self._config.retry_backoff_ms,
                enable_idempotence=self._config.enable_idempotence,
                transactional_id=self._config.transactional_id,
                transaction_timeout_ms=(self._config.transaction_timeout_ms),
                security_protocol=self._config.security_protocol,
                ssl_context=self._ssl_context,
                sasl_mechanism=(self._config.sasl_mechanism or 'PLAIN'),
                sasl_plain_username=self._config.sasl_plain_username,
                sasl_plain_password=self._config.sasl_plain_password,
                sasl_kerberos_service_name=(
                    self._config.sasl_kerberos_service_name
                ),
                sasl_kerberos_domain_name=(
                    self._config.sasl_kerberos_domain_name
                ),
            )
            await self._producer.start()
        except Exception as e:
            msg = 'Failed to start Kafka producer'
            raise PluginOpenError(
                msg,
                context={'reason': str(e)},
            ) from e

        await self._logger.ainfo('Kafka producer is started')

    @override
    async def _close(self) -> None:
        await self._producer.stop()

    @override
    async def _write(self, events: Sequence[str]) -> int:
        topic = self._config.topic
        encoding = self._config.encoding

        # Buffer events in producer accumulator;
        # each send() returns a future resolved on broker ack
        buffer_results = await asyncio.gather(
            *[
                self._producer.send(
                    topic,
                    value=event.encode(encoding),
                    key=self._key_bytes,
                )
                for event in events
            ],
            return_exceptions=True,
        )

        errors: list[BaseException] = []
        pending_confirmations = []

        for result in buffer_results:
            if isinstance(result, BaseException):
                errors.append(result)
            else:
                pending_confirmations.append(result)

        # Await delivery confirmation from broker
        if pending_confirmations:
            delivery_results = await asyncio.gather(
                *pending_confirmations,
                return_exceptions=True,
            )
            errors.extend(
                res
                for res in delivery_results
                if isinstance(res, BaseException)
            )

        for error in errors:
            await self._logger.aerror(
                'Failed to produce message to Kafka',
                reason=str(error),
                topic=topic,
            )

        return len(events) - len(errors)
