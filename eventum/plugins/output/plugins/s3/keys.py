"""Object keys rendering for s3 output plugin."""

import re
import uuid
from datetime import datetime
from string import Formatter

KEY_TEMPLATE_FIELDS = frozenset(
    {
        'year',
        'month',
        'day',
        'hour',
        'minute',
        'second',
        'timestamp',
        'seq',
        'uuid',
        'ext',
    },
)
"""Names of the fields a key template can substitute."""

_SAMPLE_MOMENT = datetime(2026, 1, 2, 3, 4, 5)  # noqa: DTZ001

_FORMATTER = Formatter()

_DISALLOWED_IN_KEY = re.compile(r'[\s\x00-\x1f\x7f]')


def validate_key_template(template: str) -> str:
    """Validate key template.

    Parameters
    ----------
    template : str
        Key template to validate.

    Returns
    -------
    str
        Provided key template.

    Raises
    ------
    ValueError
        If template is malformed, substitutes an unknown field or
        renders to a key S3 cannot address.

    Notes
    -----
    Validation renders the template with sample values, so a format
    specification the field type cannot take is rejected here instead
    of failing on the first write.

    """
    try:
        fields = [
            field
            for _, field, _, _ in _FORMATTER.parse(template)
            if field is not None
        ]
    except ValueError as e:
        msg = f'Malformed key template: {e}'
        raise ValueError(msg) from None

    # an empty field name is an automatically numbered placeholder, and
    # the fields are substituted by name alone
    unknown = sorted({field or '{}' for field in fields} - KEY_TEMPLATE_FIELDS)
    if unknown:
        known = ', '.join(sorted(KEY_TEMPLATE_FIELDS))
        msg = (
            f'Unknown fields in key template: {", ".join(unknown)}; '
            f'available fields are {known}'
        )
        raise ValueError(msg)

    try:
        key = render_key(
            template,
            moment=_SAMPLE_MOMENT,
            sequence=0,
            extension='.sample',
        )
    except (ValueError, TypeError, IndexError, KeyError) as e:
        msg = f'Key template cannot be rendered: {e}'
        raise ValueError(msg) from None

    _validate_rendered_key(key)

    return template


def _validate_rendered_key(key: str) -> None:
    """Check that a rendered key addresses an object.

    Parameters
    ----------
    key : str
        Rendered key.

    Raises
    ------
    ValueError
        If the key cannot address an object.

    """
    if not key:
        msg = 'Key template renders to an empty key'
        raise ValueError(msg)

    if key.startswith('/'):
        msg = 'Key template must not render to a key starting with `/`'
        raise ValueError(msg)

    if key.endswith('/'):
        msg = 'Key template must not render to a key ending with `/`'
        raise ValueError(msg)

    if '//' in key:
        msg = 'Key template must not render to a key with empty segments'
        raise ValueError(msg)

    segments = key.split('/')
    if '.' in segments or '..' in segments:
        msg = 'Key template must not render to a key with relative segments'
        raise ValueError(msg)

    # whitespace and control characters make the storage client reject
    # the key
    if _DISALLOWED_IN_KEY.search(key):
        msg = 'Key template must not render to a key with whitespace'
        raise ValueError(msg)


def render_key(
    template: str,
    *,
    moment: datetime,
    sequence: int,
    extension: str,
) -> str:
    """Render key of an object.

    Parameters
    ----------
    template : str
        Key template to render.

    moment : datetime
        Time the object is written at, in UTC, the time partitioning
        fields are taken from it.

    sequence : int
        Number of objects the plugin wrote or attempted before this one.

    extension : str
        Extension of the object, including the leading dot.

    Returns
    -------
    str
        Rendered key.

    Raises
    ------
    ValueError
        If a format specification does not apply to the field it is
        used with.

    KeyError
        If the template substitutes an unknown field.

    """
    return template.format(
        year=f'{moment.year:04d}',
        month=f'{moment.month:02d}',
        day=f'{moment.day:02d}',
        hour=f'{moment.hour:02d}',
        minute=f'{moment.minute:02d}',
        second=f'{moment.second:02d}',
        timestamp=moment.strftime('%Y%m%dT%H%M%S'),
        seq=sequence,
        uuid=uuid.uuid4().hex,
        ext=extension,
    )
