"""Utils for time related operations."""

from datetime import datetime, timedelta
from math import ceil, floor
from typing import Literal, assert_never
from zoneinfo import ZoneInfo

from numpy import datetime64, timedelta64


def now64(timezone: ZoneInfo) -> datetime64:
    """Get current time in specified timezone as `datetime64`.

    Parameters
    ----------
    timezone : ZoneInfo
        Timezone for value of `datetime64` object.

    Returns
    -------
    datetime64
        Numpy `datetime64` object with current time in specified
        `timezone`.

    """
    return datetime64(datetime.now().astimezone(timezone).replace(tzinfo=None))


def timedelta64_to_seconds(timedelta: timedelta64) -> float:
    """Convert numpy `timedelta64` to floating point number that
    represents seconds.

    Parameters
    ----------
    timedelta : timedelta64
        Timedelta to convert.

    Returns
    -------
    float
        Floating point number representing number of seconds in
        `timedelta`.

    """
    return float(timedelta / timedelta64(1000000, 'us'))


def to_naive(timestamp: datetime, timezone: ZoneInfo) -> datetime:
    """Convert datetime to naive format for specified timezone. If
    datetime object is naive then current zone info is used for
    conversion.

    Parameters
    ----------
    timestamp : datetime
        Timestamp to convert.

    timezone: ZoneInfo
        Timezone for localization of datetime value.

    Returns
    -------
    datetime
        Naive datetime object.

    """
    return timestamp.astimezone(timezone).replace(tzinfo=None)


def skip_periods(
    start: datetime,
    moment: datetime,
    duration: timedelta,
    ret_timestamp: Literal['last_past', 'first_future'],
) -> datetime:
    """Get last past or first future timestamp relating to specified
    moment skipping past periods with constant duration.

    Parameters
    ----------
    start : datetime
        Start timestamp for counting periods.

    moment : datetime
        Timestamps of moment until which to skip.

    duration : timedelta
        Duration of one period.

    ret_timestamp : Literal['last_past', 'first_future']
        Which timestamp to return: last past or first future.

    Returns
    -------
    datetime
        Timestamp after skipped past periods.

    Raises
    ------
    ValueError
        If duration is less than zero.

    """
    if duration.total_seconds() <= 0:
        msg = 'Duration must be greater than zero'
        raise ValueError(msg)

    skip_periods = (moment.astimezone() - start.astimezone()) / duration

    if skip_periods <= 0:
        return start

    match ret_timestamp:
        case 'last_past':
            return start + (duration * floor(skip_periods))
        case 'first_future':
            return start + (duration * ceil(skip_periods))
        case v:
            assert_never(v)
