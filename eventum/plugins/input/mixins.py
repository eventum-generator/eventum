"""Mixins for configuration models."""

from typing import Self
from zoneinfo import ZoneInfo

from pydantic import model_validator

from eventum.plugins.input.normalizers import normalize_versatile_daterange


class DaterangeValidatorMixin:
    """Mixin for validation date range in plugin configuration models
    with `start` and `end` fields.
    """

    @model_validator(mode='after')
    def validate_interval(self) -> Self:  # noqa: D102
        # raises ValueError if start > end
        try:
            # test for both earliest and latest timezones
            normalize_versatile_daterange(
                start=self.start,  # type: ignore[attr-defined]
                end=self.end,  # type: ignore[attr-defined]
                timezone=ZoneInfo('Etc/GMT-14'),
                none_start='min',
                none_end='max',
            )
            normalize_versatile_daterange(
                start=self.start,  # type: ignore[attr-defined]
                end=self.end,  # type: ignore[attr-defined]
                timezone=ZoneInfo('Etc/GMT+12'),
                none_start='min',
                none_end='max',
            )
        except OverflowError:
            msg = 'Unable to validate date range due to datetime overflow'
            raise ValueError(msg) from None

        return self
