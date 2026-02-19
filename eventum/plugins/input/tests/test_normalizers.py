from datetime import datetime, timedelta

import pytest
import pytz
from pytz import timezone

from eventum.plugins.input.normalizers import (
    normalize_versatile_daterange,
    normalize_versatile_datetime,
)


def test_normalize_versatile_datetime_for_none_with_now():
    result = normalize_versatile_datetime(
        value=None, timezone=timezone('UTC'), none_point='now'
    )
    now = datetime.now(tz=timezone('UTC'))

    assert 0 <= (now - result).total_seconds() < 0.5


def test_normalize_versatile_datetime_for_none_with_min():
    result = normalize_versatile_datetime(
        value=None, timezone=timezone('UTC'), none_point='min'
    )

    assert result < datetime(1900, 1, 1, 0, 0, 0, tzinfo=timezone('UTC'))


def test_normalize_versatile_datetime_for_none_with_max():
    result = normalize_versatile_datetime(
        value=None, timezone=timezone('UTC'), none_point='max'
    )

    assert result > datetime(2100, 1, 1, 0, 0, 0, tzinfo=timezone('UTC'))


def test_normalize_versatile_datetime_for_datetime():
    value = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone('UTC'))
    result = normalize_versatile_datetime(
        value=value, timezone=timezone('Europe/Moscow')
    )

    assert result == datetime(
        2024, 1, 1, 0, 0, 0, tzinfo=timezone('UTC')
    ).astimezone(timezone('Europe/Moscow'))


def test_normalize_versatile_datetime_for_keyword_now():
    result = normalize_versatile_datetime(
        value='now', timezone=timezone('UTC')
    )
    now = datetime.now(tz=timezone('UTC'))

    assert 0 <= (now - result).total_seconds() < 0.5


def test_normalize_versatile_datetime_for_keyword_never():
    result = normalize_versatile_datetime(
        value='never', timezone=timezone('UTC')
    )

    assert result > datetime(2100, 1, 1, 0, 0, 0, tzinfo=timezone('UTC'))


def test_normalize_versatile_datetime_for_relative_time():
    result = normalize_versatile_datetime(
        value='+1h', timezone=timezone('UTC')
    )
    approx = datetime.now(tz=timezone('UTC')) + timedelta(hours=1)

    assert 0 <= (approx - result).total_seconds() < 0.5


def test_normalize_versatile_datetime_for_negative_relative_time():
    result = normalize_versatile_datetime(
        value='-1h', timezone=timezone('UTC')
    )
    approx = datetime.now(tz=timezone('UTC')) - timedelta(hours=1)

    assert 0 <= (approx - result).total_seconds() < 0.5


def test_normalize_versatile_datetime_for_relative_time_with_relative_base():
    base = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone('UTC'))
    result = normalize_versatile_datetime(
        value='+1h', relative_base=base, timezone=timezone('UTC')
    )
    expected = datetime(2024, 1, 1, 1, 0, 0, tzinfo=timezone('UTC'))

    assert result == expected


def test_normalize_versatile_datetime_for_now_with_relative_base():
    base = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone('UTC'))
    result = normalize_versatile_datetime(
        value='now', relative_base=base, timezone=timezone('UTC')
    )
    now = datetime.now(tz=timezone('UTC'))

    assert 0 <= (now - result).total_seconds() < 0.5


@pytest.mark.filterwarnings('ignore:Parsing dates')
def test_normalize_versatile_datetime_for_human_readable():
    result = normalize_versatile_datetime(
        value='1st August 2024', timezone=timezone('UTC')
    )
    expected = datetime(2024, 8, 1, 0, 0, 0, tzinfo=timezone('UTC'))

    assert result == expected


@pytest.mark.filterwarnings('ignore:Parsing dates')
def test_normalize_versatile_datetime_for_human_readable_and_other_tz():
    tz = timezone('Europe/Moscow')
    result = normalize_versatile_datetime(value='1st August 2024', timezone=tz)
    expected = tz.localize(datetime(2024, 8, 1, 0, 0, 0))

    assert result == expected


def test_normalize_versatile_datetime_for_human_readable_with_relative_base():
    base = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone('UTC'))
    result = normalize_versatile_datetime(
        value='after one day', relative_base=base, timezone=timezone('UTC')
    )
    expected = datetime(2024, 1, 2, 0, 0, 0, tzinfo=timezone('UTC'))

    assert result == expected


def test_normalize_versatile_datetime_for_human_readable_with_rb_and_tz():
    tz = timezone('Europe/Moscow')
    base = datetime(2024, 1, 1, 0, 0, 0).astimezone(tz)
    result = normalize_versatile_datetime(
        value='after one day', relative_base=base, timezone=tz
    )
    expected = datetime(2024, 1, 2, 0, 0, 0).astimezone(tz)

    assert result == expected


@pytest.mark.filterwarnings('ignore:Parsing dates')
def test_normalize_versatile_datetime_relative_base_no_affect():
    base = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone('UTC'))
    result = normalize_versatile_datetime(
        value='August 2024', relative_base=base, timezone=timezone('UTC')
    )
    expected = datetime(2024, 8, 1, 0, 0, 0, tzinfo=timezone('UTC'))

    assert result == expected


def test_normalize_versatile_datetime_unparsable_expression():
    with pytest.raises(ValueError):
        normalize_versatile_datetime(
            value='Ovuvuevuevue Enyetuenwuevue Ugbemugbem Osas',
            timezone=timezone('Africa/Lagos'),
        )


@pytest.mark.filterwarnings('ignore:Parsing dates')
def test_normalize_versatile_daterange():
    expected_start = datetime.fromisoformat('2024-01-01T00:00:00.000Z')
    expected_end = datetime(2077, 1, 1, 0, 0, tzinfo=pytz.timezone('UTC'))

    start, end = normalize_versatile_daterange(
        start=expected_start,
        end='1st Jan of 2077 year',
        timezone=pytz.timezone('UTC'),
    )

    assert start == expected_start
    assert end == expected_end


def test_normalize_versatile_daterange_time_keyword():
    approx_expected_start = datetime.now(tz=pytz.timezone('UTC'))
    enough_for_me = datetime(2100, 1, 1, 0, 0, tzinfo=pytz.timezone('UTC'))

    start, end = normalize_versatile_daterange(
        start='now',
        end='never',
        timezone=pytz.timezone('UTC'),
    )

    assert 0 < (start - approx_expected_start).total_seconds() < 1
    assert end > enough_for_me


def test_normalize_versatile_daterange_human_relative_end():
    expected_start = datetime.fromisoformat('2024-01-01T00:00:00.000Z')
    expected_end = expected_start + timedelta(hours=12, minutes=5)

    start, end = normalize_versatile_daterange(
        start=expected_start,
        end='after 12 hours and five minute',
        timezone=pytz.timezone('UTC'),
    )

    assert start == expected_start
    assert end == expected_end


def test_normalize_versatile_daterange_none_values_now_start():
    approx_expected_start = datetime.now(tz=pytz.timezone('UTC'))
    enough_for_me = datetime(2100, 1, 1, 0, 0, tzinfo=pytz.timezone('UTC'))

    start, end = normalize_versatile_daterange(
        start=None, end=None, timezone=pytz.timezone('UTC'), none_start='now'
    )

    assert 0 < (start - approx_expected_start).total_seconds() < 1
    assert end > enough_for_me


def test_normalize_versatile_daterange_none_values_min_start():
    enough_early_for_me = datetime(
        1900, 1, 1, 0, 0, tzinfo=pytz.timezone('UTC')
    )
    enough_late_for_me = datetime(
        2100, 1, 1, 0, 0, tzinfo=pytz.timezone('UTC')
    )

    start, end = normalize_versatile_daterange(
        start=None, end=None, timezone=pytz.timezone('UTC'), none_start='min'
    )

    assert start < enough_early_for_me
    assert end > enough_late_for_me


def test_normalize_versatile_daterange_invalid():
    with pytest.raises(ValueError):
        normalize_versatile_daterange(
            start=datetime(2024, 1, 1, 0, 0, tzinfo=pytz.timezone('UTC')),
            end=datetime(2014, 1, 1, 0, 0, tzinfo=pytz.timezone('UTC')),
            timezone=pytz.timezone('UTC'),
        )

    with pytest.raises(ValueError):
        normalize_versatile_daterange(
            start='never',
            end=None,
            timezone=pytz.timezone('UTC'),
        )

    with pytest.raises(ValueError):
        normalize_versatile_daterange(
            start='qwerty',
            end=None,
            timezone=pytz.timezone('UTC'),
        )
