import pytest
from pydantic import ValidationError

from eventum.plugins.output.fields import Format
from eventum.plugins.output.plugins.s3.config import (
    DEFAULT_KEY_TEMPLATE,
    Encoding,
    JsonLinesEncoderConfig,
    ParquetEncoderConfig,
    S3OutputPluginConfig,
)


def config(**kwargs) -> S3OutputPluginConfig:
    return S3OutputPluginConfig.model_validate({'bucket': 'lake', **kwargs})


class TestDefaults:
    def test_bucket_is_required(self):
        with pytest.raises(ValidationError):
            S3OutputPluginConfig.model_validate({})

    def test_key_template_defaults_to_time_partitioned_layout(self):
        assert config().key_template == DEFAULT_KEY_TEMPLATE

    def test_default_key_template_partitions_by_hour(self):
        assert 'year={year}' in DEFAULT_KEY_TEMPLATE
        assert 'hour={hour}' in DEFAULT_KEY_TEMPLATE

    def test_default_key_template_is_unique_per_object(self):
        assert '{uuid}' in DEFAULT_KEY_TEMPLATE

    def test_encoder_defaults_to_json_lines(self):
        assert config().encoder == JsonLinesEncoderConfig(
            encoding=Encoding.JSON_LINES,
        )

    def test_formatter_defaults_to_single_line_json(self):
        formatter = config().formatter

        assert formatter.format == Format.JSON
        assert formatter.indent == 0

    def test_credentials_default_to_environment(self):
        assert config().access_key_id is None
        assert config().secret_access_key is None

    def test_verify_is_on_by_default(self):
        assert config().verify is True

    def test_extra_fields_are_forbidden(self):
        with pytest.raises(ValidationError):
            config(unknown='x')

    def test_config_is_frozen(self):
        with pytest.raises(ValidationError):
            config().bucket = 'other'


class TestKeyTemplate:
    def test_unknown_field_is_rejected(self):
        with pytest.raises(ValidationError, match='Unknown fields'):
            config(key_template='{yaer}/{uuid}')

    def test_empty_template_is_rejected(self):
        with pytest.raises(ValidationError):
            config(key_template='')

    def test_valid_template_is_accepted(self):
        assert config(key_template='data/{uuid}.jsonl').key_template == (
            'data/{uuid}.jsonl'
        )


class TestCredentials:
    def test_key_id_without_secret_is_rejected(self):
        with pytest.raises(ValidationError, match='must be provided together'):
            config(access_key_id='k')

    def test_secret_without_key_id_is_rejected(self):
        with pytest.raises(ValidationError, match='must be provided together'):
            config(secret_access_key='s')

    def test_both_together_are_accepted(self):
        cfg = config(access_key_id='k', secret_access_key='s')

        assert cfg.access_key_id == 'k'
        assert cfg.secret_access_key == 's'

    def test_session_token_without_credentials_is_rejected(self):
        with pytest.raises(ValidationError, match='Session token requires'):
            config(session_token='t')

    def test_session_token_with_credentials_is_accepted(self):
        cfg = config(
            access_key_id='k',
            secret_access_key='s',
            session_token='t',
        )

        assert cfg.session_token == 't'


class TestHeaderValues:
    def test_access_key_with_a_line_break_is_rejected(self):
        with pytest.raises(ValidationError):
            config(access_key_id='key\n', secret_access_key='s')  # noqa: S106

    def test_secret_with_a_line_break_is_rejected(self):
        with pytest.raises(ValidationError):
            config(access_key_id='k', secret_access_key='secret\n')  # noqa: S106

    def test_session_token_with_a_line_break_is_rejected(self):
        with pytest.raises(ValidationError):
            config(
                access_key_id='k',
                secret_access_key='s',  # noqa: S106
                session_token='token\n',  # noqa: S106
            )

    def test_content_type_with_a_line_break_is_rejected(self):
        with pytest.raises(ValidationError):
            config(content_type='application/json\n')

    def test_content_type_with_a_tab_is_rejected(self):
        with pytest.raises(ValidationError):
            config(content_type='application/json\t')

    def test_plain_values_are_accepted(self):
        cfg = config(
            access_key_id='k',
            secret_access_key='s',  # noqa: S106
            content_type='application/json',
        )

        assert cfg.content_type == 'application/json'


class TestEncoderCompression:
    def test_gzip_level_above_maximum_is_rejected(self):
        with pytest.raises(ValidationError, match='at most 9'):
            config(
                encoder={
                    'encoding': 'jsonl',
                    'compression': 'gzip',
                    'compression_level': 10,
                },
            )

    def test_gzip_maximum_level_is_accepted(self):
        cfg = config(
            encoder={
                'encoding': 'jsonl',
                'compression': 'gzip',
                'compression_level': 9,
            },
        )

        assert cfg.encoder.compression_level == 9

    def test_zstd_level_above_maximum_is_rejected(self):
        with pytest.raises(ValidationError):
            config(
                encoder={
                    'encoding': 'jsonl',
                    'compression': 'zstd',
                    'compression_level': 23,
                },
            )

    def test_zstd_high_level_is_accepted(self):
        cfg = config(
            encoder={
                'encoding': 'jsonl',
                'compression': 'zstd',
                'compression_level': 22,
            },
        )

        assert cfg.encoder.compression_level == 22

    def test_level_without_compression_is_rejected(self):
        with pytest.raises(ValidationError, match='requires a compression'):
            config(
                encoder={'encoding': 'jsonl', 'compression_level': 5},
            )

    def test_unknown_compression_is_rejected(self):
        with pytest.raises(ValidationError):
            config(encoder={'encoding': 'jsonl', 'compression': 'lzma'})


class TestEncoderDiscrimination:
    def test_parquet_encoder_is_selected_by_encoding(self):
        cfg = config(encoder={'encoding': 'parquet'})

        assert isinstance(cfg.encoder, ParquetEncoderConfig)

    def test_parquet_field_under_json_lines_is_rejected(self):
        with pytest.raises(ValidationError):
            config(encoder={'encoding': 'jsonl', 'row_group_size': 10})

    def test_json_lines_field_under_parquet_is_rejected(self):
        with pytest.raises(ValidationError):
            config(encoder={'encoding': 'parquet', 'separator': '\n'})

    def test_parquet_compression_is_its_own_vocabulary(self):
        cfg = config(encoder={'encoding': 'parquet', 'compression': 'snappy'})

        assert cfg.encoder.compression == 'snappy'

    def test_json_lines_rejects_parquet_compression(self):
        with pytest.raises(ValidationError):
            config(encoder={'encoding': 'jsonl', 'compression': 'snappy'})

    def test_unknown_encoding_is_rejected(self):
        with pytest.raises(ValidationError):
            config(encoder={'encoding': 'avro'})

    def test_row_group_size_must_be_positive(self):
        with pytest.raises(ValidationError):
            config(encoder={'encoding': 'parquet', 'row_group_size': 0})


class TestFormatterCompatibility:
    def test_parquet_takes_json(self):
        cfg = config(
            encoder={'encoding': 'parquet'},
            formatter={'format': 'json', 'indent': 0},
        )

        assert cfg.formatter.format == Format.JSON

    def test_parquet_rejects_plain(self):
        with pytest.raises(ValidationError, match='takes events of'):
            config(
                encoder={'encoding': 'parquet'},
                formatter={'format': 'plain'},
            )

    def test_parquet_rejects_json_batch(self):
        with pytest.raises(ValidationError, match='takes events of'):
            config(
                encoder={'encoding': 'parquet'},
                formatter={'format': 'json-batch'},
            )

    def test_parquet_rejects_template(self):
        with pytest.raises(ValidationError, match='takes events of'):
            config(
                encoder={'encoding': 'parquet'},
                formatter={'format': 'template', 'template': '{{ event }}'},
            )

    def test_json_lines_takes_plain(self):
        cfg = config(formatter={'format': 'plain'})

        assert cfg.formatter.format == Format.PLAIN

    def test_json_lines_takes_template(self):
        cfg = config(
            formatter={'format': 'template', 'template': '{{ event }}'},
        )

        assert cfg.formatter.format == Format.TEMPLATE

    def test_json_lines_rejects_json_batch(self):
        with pytest.raises(ValidationError, match='takes events of'):
            config(formatter={'format': 'json-batch'})

    def test_json_lines_rejects_template_batch(self):
        with pytest.raises(ValidationError, match='takes events of'):
            config(
                formatter={
                    'format': 'template-batch',
                    'template': '{{ events }}',
                },
            )

    def test_json_lines_rejects_eventum_http_input(self):
        with pytest.raises(ValidationError, match='takes events of'):
            config(formatter={'format': 'eventum-http-input'})


class TestSingleLineRequirement:
    def test_json_lines_rejects_indented_json(self):
        with pytest.raises(ValidationError, match='single lines'):
            config(formatter={'format': 'json', 'indent': 4})

    def test_json_lines_accepts_json_without_indent(self):
        assert config(formatter={'format': 'json', 'indent': 0}).formatter

    def test_parquet_accepts_indented_json(self):
        cfg = config(
            encoder={'encoding': 'parquet'},
            formatter={'format': 'json', 'indent': 4},
        )

        assert cfg.formatter.indent == 4
