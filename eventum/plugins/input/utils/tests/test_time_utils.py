from datetime import datetime, timedelta

import pytest
from zoneinfo import ZoneInfo
from numpy import datetime64, timedelta64

from eventum.plugins.input.utils.time_utils import (
    now64,
    skip_periods,
    timedelta64_to_seconds,
    to_naive,
)


def test_now64():
    tz = ZoneInfo('Europe/Moscow')
    now = datetime.now().astimezone(tz).replace(tzinfo=None)

    expected = datetime64(now.isoformat(), 'us')
    result = now64(timezone=tz)

    assert 0 <= ((result - expected) / timedelta64(1000000, 'us')) < 0.5


def test_timedelta64_to_seconds():
    assert timedelta64_to_seconds(timedelta64(125, 'ms')) == 0.125


def test_to_naive():
    timestamp = datetime(2024, 1, 1, 0, 0, 0, tzinfo=ZoneInfo('UTC'))
    result = to_naive(timestamp, timezone=ZoneInfo('Europe/Moscow'))

    assert result == datetime64(
        timestamp.astimezone(ZoneInfo('Europe/Moscow')).replace(
            tzinfo=None
        )
    )


def test_skip_periods():
    timestamp = skip_periods(
        start=datetime(2024, 1, 1, 0, 0, 0),
        moment=datetime(2024, 1, 1, 12, 30, 0),
        duration=timedelta(hours=1),
        ret_timestamp='last_past',
    )

    assert timestamp == datetime(2024, 1, 1, 12, 0, 0)

    timestamp = skip_periods(
        start=datetime(2024, 1, 1, 0, 0, 0),
        moment=datetime(2024, 1, 1, 12, 30, 0),
        duration=timedelta(hours=1),
        ret_timestamp='first_future',
    )

    assert timestamp == datetime(2024, 1, 1, 13, 0, 0)

    with pytest.raises(ValueError):
        timestamp = skip_periods(
            start=datetime(2024, 1, 1, 0, 0, 0),
            moment=datetime(2024, 1, 1, 12, 30, 0),
            duration=timedelta(hours=-1),
            ret_timestamp='first_future',
        )
