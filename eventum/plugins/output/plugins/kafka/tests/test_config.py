"""Tests for kafka output plugin config."""

import pytest
from pydantic import ValidationError

from eventum.plugins.output.plugins.kafka.config import KafkaOutputPluginConfig


def test_minimal_valid():
    config = KafkaOutputPluginConfig(
        bootstrap_servers=['localhost:9092'],
        topic='events',
    )
    assert config.bootstrap_servers == ['localhost:9092']
    assert config.topic == 'events'
    assert config.key is None
    assert config.encoding == 'utf-8'
    assert config.acks == 1
    assert config.compression_type is None
    assert config.security_protocol == 'PLAINTEXT'


def test_missing_bootstrap_servers():
    with pytest.raises(ValidationError):
        KafkaOutputPluginConfig(topic='events')  # type: ignore


def test_missing_topic():
    with pytest.raises(ValidationError):
        KafkaOutputPluginConfig(  # type: ignore
            bootstrap_servers=['localhost:9092'],
        )


def test_empty_bootstrap_servers():
    with pytest.raises(ValidationError):
        KafkaOutputPluginConfig(
            bootstrap_servers=[],
            topic='events',
        )


def test_empty_bootstrap_server_item():
    with pytest.raises(ValidationError):
        KafkaOutputPluginConfig(
            bootstrap_servers=['broker1:9092', ''],
            topic='events',
        )


def test_empty_topic():
    with pytest.raises(ValidationError):
        KafkaOutputPluginConfig(
            bootstrap_servers=['localhost:9092'],
            topic='',
        )


def test_all_fields():
    config = KafkaOutputPluginConfig(
        bootstrap_servers=['broker1:9092', 'broker2:9092'],
        topic='events',
        key='my-key',
        encoding='ascii',
        client_id='eventum-producer',
        metadata_max_age_ms=60000,
        request_timeout_ms=5000,
        connections_max_idle_ms=300000,
        acks=-1,
        compression_type='gzip',
        max_batch_size=32768,
        max_request_size=2097152,
        linger_ms=100,
        retry_backoff_ms=200,
        enable_idempotence=True,
        transactional_id='my-txn',
        transaction_timeout_ms=30000,
        security_protocol='SASL_SSL',
        sasl_mechanism='SCRAM-SHA-256',
        sasl_plain_username='user',
        sasl_plain_password='pass',
        sasl_kerberos_service_name='kafka',
        sasl_kerberos_domain_name='example.com',
        ssl_cafile='ca.pem',  # type: ignore
        ssl_certfile='client.pem',  # type: ignore
        ssl_keyfile='client-key.pem',  # type: ignore
    )
    assert config.key == 'my-key'
    assert config.encoding == 'ascii'
    assert config.acks == -1
    assert config.compression_type == 'gzip'
    assert config.enable_idempotence is True
    assert config.security_protocol == 'SASL_SSL'
    assert config.sasl_mechanism == 'SCRAM-SHA-256'


def test_acks_values():
    for acks in (0, 1, -1):
        config = KafkaOutputPluginConfig(
            bootstrap_servers=['localhost:9092'],
            topic='events',
            acks=acks,
        )
        assert config.acks == acks


def test_invalid_acks():
    with pytest.raises(ValidationError):
        KafkaOutputPluginConfig(
            bootstrap_servers=['localhost:9092'],
            topic='events',
            acks=2,  # type: ignore
        )


def test_ssl_cert_without_key():
    with pytest.raises(ValidationError, match='SSL certificate and key'):
        KafkaOutputPluginConfig(
            bootstrap_servers=['localhost:9092'],
            topic='events',
            ssl_certfile='client.pem',  # type: ignore
        )


def test_ssl_key_without_cert():
    with pytest.raises(ValidationError, match='SSL certificate and key'):
        KafkaOutputPluginConfig(
            bootstrap_servers=['localhost:9092'],
            topic='events',
            ssl_keyfile='client-key.pem',  # type: ignore
        )


def test_ssl_cert_and_key_together():
    config = KafkaOutputPluginConfig(
        bootstrap_servers=['localhost:9092'],
        topic='events',
        ssl_certfile='client.pem',  # type: ignore
        ssl_keyfile='client-key.pem',  # type: ignore
    )
    assert config.ssl_certfile is not None
    assert config.ssl_keyfile is not None


def test_sasl_username_without_password():
    with pytest.raises(
        ValidationError,
        match='SASL username and password',
    ):
        KafkaOutputPluginConfig(
            bootstrap_servers=['localhost:9092'],
            topic='events',
            sasl_plain_username='user',
        )


def test_sasl_password_without_username():
    with pytest.raises(
        ValidationError,
        match='SASL username and password',
    ):
        KafkaOutputPluginConfig(
            bootstrap_servers=['localhost:9092'],
            topic='events',
            sasl_plain_password='pass',
        )


def test_sasl_credentials_together():
    config = KafkaOutputPluginConfig(
        bootstrap_servers=['localhost:9092'],
        topic='events',
        sasl_mechanism='PLAIN',
        sasl_plain_username='user',
        sasl_plain_password='pass',
    )
    assert config.sasl_plain_username == 'user'
    assert config.sasl_plain_password == 'pass'


def test_max_batch_size_boundary():
    config = KafkaOutputPluginConfig(
        bootstrap_servers=['localhost:9092'],
        topic='events',
        max_batch_size=1,
    )
    assert config.max_batch_size == 1

    with pytest.raises(ValidationError):
        KafkaOutputPluginConfig(
            bootstrap_servers=['localhost:9092'],
            topic='events',
            max_batch_size=0,
        )


def test_linger_ms_boundary():
    config = KafkaOutputPluginConfig(
        bootstrap_servers=['localhost:9092'],
        topic='events',
        linger_ms=0,
    )
    assert config.linger_ms == 0

    with pytest.raises(ValidationError):
        KafkaOutputPluginConfig(
            bootstrap_servers=['localhost:9092'],
            topic='events',
            linger_ms=-1,
        )


def test_compression_types():
    for compression in ('gzip', 'snappy', 'lz4', 'zstd'):
        config = KafkaOutputPluginConfig(
            bootstrap_servers=['localhost:9092'],
            topic='events',
            compression_type=compression,
        )
        assert config.compression_type == compression


def test_invalid_compression_type():
    with pytest.raises(ValidationError):
        KafkaOutputPluginConfig(
            bootstrap_servers=['localhost:9092'],
            topic='events',
            compression_type='bzip2',  # type: ignore
        )


def test_empty_encoding():
    with pytest.raises(ValidationError):
        KafkaOutputPluginConfig(
            bootstrap_servers=['localhost:9092'],
            topic='events',
            encoding='',
        )


def test_security_protocols():
    for protocol in (
        'PLAINTEXT',
        'SSL',
        'SASL_PLAINTEXT',
        'SASL_SSL',
    ):
        config = KafkaOutputPluginConfig(
            bootstrap_servers=['localhost:9092'],
            topic='events',
            security_protocol=protocol,
        )
        assert config.security_protocol == protocol


def test_multiple_bootstrap_servers():
    config = KafkaOutputPluginConfig(
        bootstrap_servers=[
            'broker1:9092',
            'broker2:9092',
            'broker3:9092',
        ],
        topic='events',
    )
    assert len(config.bootstrap_servers) == 3
