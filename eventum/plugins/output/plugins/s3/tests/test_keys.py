import uuid
from datetime import UTC, datetime

import pytest

from eventum.plugins.output.plugins.s3.keys import (
    KEY_TEMPLATE_FIELDS,
    render_key,
    validate_key_template,
)

MOMENT = datetime(2026, 3, 4, 5, 6, 7, tzinfo=UTC)


def render(template: str, sequence: int = 0, extension: str = '.jsonl') -> str:
    return render_key(
        template,
        moment=MOMENT,
        sequence=sequence,
        extension=extension,
    )


class TestRendering:
    def test_time_fields_are_zero_padded(self):
        key = render('{year}/{month}/{day}/{hour}/{minute}/{second}')

        assert key == '2026/03/04/05/06/07'

    def test_timestamp_field(self):
        assert render('{timestamp}') == '20260304T050607'

    def test_sequence_field(self):
        assert render('{seq}', sequence=7) == '7'

    def test_sequence_takes_numeric_format_spec(self):
        assert render('{seq:06d}', sequence=7) == '000007'

    def test_extension_field(self):
        assert render('data{ext}', extension='.parquet') == 'data.parquet'

    def test_uuid_field_differs_between_renders(self):
        assert render('{uuid}') != render('{uuid}')

    def test_uuid_field_is_hex_of_expected_length(self):
        key = render('{uuid}')

        assert len(key) == len(uuid.uuid4().hex)
        assert bytes.fromhex(key)

    def test_literal_template_is_kept_as_is(self):
        assert render('events/data.jsonl') == 'events/data.jsonl'

    def test_default_template_fields_are_all_known(self):
        assert {
            'year',
            'month',
            'day',
            'hour',
            'timestamp',
            'uuid',
            'ext',
        } <= KEY_TEMPLATE_FIELDS


class TestValidation:
    def test_valid_template_is_returned_as_is(self):
        template = 'year={year}/{timestamp}-{uuid}{ext}'

        assert validate_key_template(template) == template

    def test_unknown_field_is_rejected(self):
        with pytest.raises(ValueError, match='Unknown fields'):
            validate_key_template('{yaer}/{uuid}')

    def test_unknown_field_message_lists_available_fields(self):
        with pytest.raises(ValueError, match='timestamp'):
            validate_key_template('{yaer}')

    def test_generator_id_is_not_a_field(self):
        with pytest.raises(ValueError, match='Unknown fields'):
            validate_key_template('{generator_id}/{uuid}')

    def test_unclosed_brace_is_rejected(self):
        with pytest.raises(ValueError, match='Malformed key template'):
            validate_key_template('{year/{uuid}')

    def test_numeric_format_spec_on_text_field_is_rejected(self):
        with pytest.raises(ValueError, match='cannot be rendered'):
            validate_key_template('{month:02d}')

    def test_attribute_access_is_rejected(self):
        with pytest.raises(ValueError, match='Unknown fields'):
            validate_key_template('{seq.real}')

    def test_index_access_is_rejected(self):
        with pytest.raises(ValueError, match='Unknown fields'):
            validate_key_template('{uuid[0]}')

    def test_auto_numbered_placeholder_is_rejected(self):
        with pytest.raises(ValueError, match='Unknown fields'):
            validate_key_template('{}')

    def test_auto_numbered_placeholder_among_fields_is_rejected(self):
        with pytest.raises(ValueError, match='Unknown fields'):
            validate_key_template('a{}{ext}')

    def test_conversion_of_an_auto_numbered_field_is_rejected(self):
        with pytest.raises(ValueError, match='Unknown fields'):
            validate_key_template('{!r}')

    def test_key_with_a_space_is_rejected(self):
        with pytest.raises(ValueError, match='whitespace'):
            validate_key_template('data dir/{uuid}')

    def test_key_with_a_line_break_is_rejected(self):
        with pytest.raises(ValueError, match='whitespace'):
            validate_key_template('data\n/{uuid}')

    def test_key_with_a_tab_is_rejected(self):
        with pytest.raises(ValueError, match='whitespace'):
            validate_key_template('data\t{uuid}')

    def test_template_that_never_varies_is_rejected(self):
        with pytest.raises(ValueError, match='same key for every'):
            validate_key_template('events.jsonl')

    def test_template_of_only_an_extension_is_rejected(self):
        with pytest.raises(ValueError, match='same key for every'):
            validate_key_template('data{ext}')

    def test_template_varying_by_sequence_is_accepted(self):
        assert validate_key_template('{seq}{ext}')

    def test_template_varying_by_time_is_accepted(self):
        assert validate_key_template('{timestamp}{ext}')

    def test_template_varying_by_uuid_is_accepted(self):
        assert validate_key_template('{uuid}{ext}')

    def test_leading_slash_is_rejected(self):
        with pytest.raises(ValueError, match='starting with'):
            validate_key_template('/{uuid}{ext}')

    def test_trailing_slash_is_rejected(self):
        with pytest.raises(ValueError, match='ending with'):
            validate_key_template('{year}/')

    def test_empty_segment_is_rejected(self):
        with pytest.raises(ValueError, match='empty segments'):
            validate_key_template('{year}//{uuid}')

    def test_relative_segment_is_rejected(self):
        with pytest.raises(ValueError, match='relative segments'):
            validate_key_template('{year}/../{uuid}')

    def test_current_directory_segment_is_rejected(self):
        with pytest.raises(ValueError, match='relative segments'):
            validate_key_template('./{uuid}')

    def test_template_rendering_to_empty_key_is_rejected(self):
        with pytest.raises(ValueError, match='empty key'):
            validate_key_template('{empty}'.replace('{empty}', ''))
