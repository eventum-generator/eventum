from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from eventum.plugins.input.normalizers import (
    normalize_versatile_daterange,
    normalize_versatile_datetime,
)


def test_normalize_versatile_datetime_for_none_with_now():
    result = normalize_versatile_datetime(
        value=None, timezone=ZoneInfo('UTC'), none_point='now'
    )
    now = datetime.now(tz=ZoneInfo('UTC'))

    assert 0 <= (now - result).total_seconds() < 0.5


def test_normalize_versatile_datetime_for_none_with_min():
    result = normalize_versatile_datetime(
        value=None, timezone=ZoneInfo('UTC'), none_point='min'
    )

    assert result < datetime(1900, 1, 1, 0, 0, 0, tzinfo=ZoneInfo('UTC'))


def test_normalize_versatile_datetime_for_none_with_max():
    result = normalize_versatile_datetime(
        value=None, timezone=ZoneInfo('UTC'), none_point='max'
    )

    assert result > datetime(2100, 1, 1, 0, 0, 0, tzinfo=ZoneInfo('UTC'))


def test_normalize_versatile_datetime_for_datetime():
    value = datetime(2024, 1, 1, 0, 0, 0, tzinfo=ZoneInfo('UTC'))
    result = normalize_versatile_datetime(
        value=value, timezone=ZoneInfo('Europe/Moscow')
    )

    assert result == datetime(
        2024, 1, 1, 0, 0, 0, tzinfo=ZoneInfo('UTC')
    ).astimezone(ZoneInfo('Europe/Moscow'))


def test_normalize_versatile_datetime_for_keyword_now():
    result = normalize_versatile_datetime(
        value='now', timezone=ZoneInfo('UTC')
    )
    now = datetime.now(tz=ZoneInfo('UTC'))

    assert 0 <= (now - result).total_seconds() < 0.5


def test_normalize_versatile_datetime_for_keyword_never():
    result = normalize_versatile_datetime(
        value='never', timezone=ZoneInfo('UTC')
    )

    assert result > datetime(2100, 1, 1, 0, 0, 0, tzinfo=ZoneInfo('UTC'))


def test_normalize_versatile_datetime_for_relative_time():
    result = normalize_versatile_datetime(
        value='+1h', timezone=ZoneInfo('UTC')
    )
    approx = datetime.now(tz=ZoneInfo('UTC')) + timedelta(hours=1)

    assert 0 <= (approx - result).total_seconds() < 0.5


def test_normalize_versatile_datetime_for_negative_relative_time():
    result = normalize_versatile_datetime(
        value='-1h', timezone=ZoneInfo('UTC')
    )
    approx = datetime.now(tz=ZoneInfo('UTC')) - timedelta(hours=1)

    assert 0 <= (approx - result).total_seconds() < 0.5


def test_normalize_versatile_datetime_for_relative_time_with_relative_base():
    base = datetime(2024, 1, 1, 0, 0, 0, tzinfo=ZoneInfo('UTC'))
    result = normalize_versatile_datetime(
        value='+1h', relative_base=base, timezone=ZoneInfo('UTC')
    )
    expected = datetime(2024, 1, 1, 1, 0, 0, tzinfo=ZoneInfo('UTC'))

    assert result == expected


def test_normalize_versatile_datetime_for_now_with_relative_base():
    base = datetime(2024, 1, 1, 0, 0, 0, tzinfo=ZoneInfo('UTC'))
    result = normalize_versatile_datetime(
        value='now', relative_base=base, timezone=ZoneInfo('UTC')
    )
    now = datetime.now(tz=ZoneInfo('UTC'))

    assert 0 <= (now - result).total_seconds() < 0.5


@pytest.mark.filterwarnings('ignore:Parsing dates')
def test_normalize_versatile_datetime_for_human_readable():
    result = normalize_versatile_datetime(
        value='1st August 2024', timezone=ZoneInfo('UTC')
    )
    expected = datetime(2024, 8, 1, 0, 0, 0, tzinfo=ZoneInfo('UTC'))

    assert result == expected


@pytest.mark.filterwarnings('ignore:Parsing dates')
def test_normalize_versatile_datetime_for_human_readable_and_other_tz():
    tz = ZoneInfo('Europe/Moscow')
    result = normalize_versatile_datetime(value='1st August 2024', timezone=tz)
    expected = datetime(2024, 8, 1, 0, 0, 0).replace(tzinfo=tz)

    assert result == expected


def test_normalize_versatile_datetime_for_human_readable_with_relative_base():
    base = datetime(2024, 1, 1, 0, 0, 0, tzinfo=ZoneInfo('UTC'))
    result = normalize_versatile_datetime(
        value='after one day', relative_base=base, timezone=ZoneInfo('UTC')
    )
    expected = datetime(2024, 1, 2, 0, 0, 0, tzinfo=ZoneInfo('UTC'))

    assert result == expected


def test_normalize_versatile_datetime_for_human_readable_with_rb_and_tz():
    tz = ZoneInfo('Europe/Moscow')
    base = datetime(2024, 1, 1, 0, 0, 0).astimezone(tz)
    result = normalize_versatile_datetime(
        value='after one day', relative_base=base, timezone=tz
    )
    expected = datetime(2024, 1, 2, 0, 0, 0).astimezone(tz)

    assert result == expected


@pytest.mark.filterwarnings('ignore:Parsing dates')
def test_normalize_versatile_datetime_relative_base_no_affect():
    base = datetime(2024, 1, 1, 0, 0, 0, tzinfo=ZoneInfo('UTC'))
    result = normalize_versatile_datetime(
        value='August 2024', relative_base=base, timezone=ZoneInfo('UTC')
    )
    expected = datetime(2024, 8, 1, 0, 0, 0, tzinfo=ZoneInfo('UTC'))

    assert result == expected


def test_normalize_versatile_datetime_unparsable_expression():
    with pytest.raises(ValueError):
        normalize_versatile_datetime(
            value='Ovuvuevuevue Enyetuenwuevue Ugbemugbem Osas',
            timezone=ZoneInfo('Africa/Lagos'),
        )


@pytest.mark.filterwarnings('ignore:Parsing dates')
def test_normalize_versatile_daterange():
    expected_start = datetime.fromisoformat('2024-01-01T00:00:00.000Z')
    expected_end = datetime(2077, 1, 1, 0, 0, tzinfo=ZoneInfo('UTC'))

    start, end = normalize_versatile_daterange(
        start=expected_start,
        end='1st Jan of 2077 year',
        timezone=ZoneInfo('UTC'),
    )

    assert start == expected_start
    assert end == expected_end


def test_normalize_versatile_daterange_time_keyword():
    approx_expected_start = datetime.now(tz=ZoneInfo('UTC'))
    enough_for_me = datetime(2100, 1, 1, 0, 0, tzinfo=ZoneInfo('UTC'))

    start, end = normalize_versatile_daterange(
        start='now',
        end='never',
        timezone=ZoneInfo('UTC'),
    )

    assert 0 < (start - approx_expected_start).total_seconds() < 1
    assert end > enough_for_me


def test_normalize_versatile_daterange_human_relative_end():
    expected_start = datetime.fromisoformat('2024-01-01T00:00:00.000Z')
    expected_end = expected_start + timedelta(hours=12, minutes=5)

    start, end = normalize_versatile_daterange(
        start=expected_start,
        end='after 12 hours and five minute',
        timezone=ZoneInfo('UTC'),
    )

    assert start == expected_start
    assert end == expected_end


def test_normalize_versatile_daterange_none_values_now_start():
    approx_expected_start = datetime.now(tz=ZoneInfo('UTC'))
    enough_for_me = datetime(2100, 1, 1, 0, 0, tzinfo=ZoneInfo('UTC'))

    start, end = normalize_versatile_daterange(
        start=None, end=None, timezone=ZoneInfo('UTC'), none_start='now'
    )

    assert 0 < (start - approx_expected_start).total_seconds() < 1
    assert end > enough_for_me


def test_normalize_versatile_daterange_none_values_min_start():
    enough_early_for_me = datetime(1900, 1, 1, 0, 0, tzinfo=ZoneInfo('UTC'))
    enough_late_for_me = datetime(2100, 1, 1, 0, 0, tzinfo=ZoneInfo('UTC'))

    start, end = normalize_versatile_daterange(
        start=None, end=None, timezone=ZoneInfo('UTC'), none_start='min'
    )

    assert start < enough_early_for_me
    assert end > enough_late_for_me


def test_normalize_versatile_daterange_invalid():
    with pytest.raises(ValueError):
        normalize_versatile_daterange(
            start=datetime(2024, 1, 1, 0, 0, tzinfo=ZoneInfo('UTC')),
            end=datetime(2014, 1, 1, 0, 0, tzinfo=ZoneInfo('UTC')),
            timezone=ZoneInfo('UTC'),
        )

    with pytest.raises(ValueError):
        normalize_versatile_daterange(
            start='never',
            end=None,
            timezone=ZoneInfo('UTC'),
        )

    with pytest.raises(ValueError):
        normalize_versatile_daterange(
            start='qwerty',
            end=None,
            timezone=ZoneInfo('UTC'),
        )
