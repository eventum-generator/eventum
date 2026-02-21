"""Generator parameters."""

from pathlib import Path
from typing import Any, Self
from zoneinfo import available_timezones

from pydantic import BaseModel, Field, field_validator, model_validator


class BatchParameters(BaseModel, extra='forbid', frozen=True):
    """Batcher parameters.

    Attributes
    ----------
    size : int | None, default=10000
        Batch size for generating events.

    delay : float | None, default=1.0
        Batch delay (in seconds) for generating events.

    Notes
    -----
    At least one parameter must be not `None`.

    """

    size: int | None = Field(default=None, ge=1)
    delay: float | None = Field(default=None, ge=0.1)

    @model_validator(mode='before')
    @classmethod
    def apply_defaults_if_missing(cls, values: dict) -> dict:  # noqa: D102
        size_missing = 'size' not in values
        delay_missing = 'delay' not in values

        if size_missing and delay_missing:
            values['size'] = 10_000
            values['delay'] = 1.0

        return values

    @model_validator(mode='after')
    def validate_batch_params(self) -> Self:  # noqa: D102
        if self.size is None and self.delay is None:
            msg = 'Batch size or timeout must be provided'
            raise ValueError(msg)

        return self


class QueueParameters(BaseModel, extra='forbid', frozen=True):
    """Parameters of input plugins queue.

    Attributes
    ----------
    max_timestamp_batches : int, default=10
        Maximum number of batches in timestamps queue.

    max_event_batches : int, default=10
        Maximum number of batches in events queue.

    """

    max_timestamp_batches: int = Field(default=10, ge=1)
    max_event_batches: int = Field(default=10, ge=1)


class GenerationParameters(BaseModel, extra='forbid', frozen=True):
    """Generation parameters that are common for all generators and can
    be overridden from generator parameters level.

    Attributes
    ----------
    timezone : str, default='UTC'
        Time zone for generating timestamps.

    batch : BatchParameters, default=BatchParameters(...)
        Batch parameters.

    queue : QueueParameters, default=QueueParameters(...)
        Queue parameters.

    keep_order : bool, default=False
        Whether to keep chronological order of events using their
        timestamps by disabling output plugins concurrency.

    max_concurrency : int, default=100
        Maximum number of write operations performed by output plugins
        concurrently.

    write_timeout : int, default=10
        Timeout (in seconds) before canceling single write task.

    """

    timezone: str = Field(default='UTC', min_length=3)
    batch: BatchParameters = Field(default_factory=BatchParameters)
    queue: QueueParameters = Field(default_factory=QueueParameters)
    keep_order: bool = Field(default=False)
    max_concurrency: int = Field(default=100, ge=1)
    write_timeout: int = Field(default=10, ge=1)

    @field_validator('timezone')
    @classmethod
    def validate_timezone(cls, v: str) -> str:  # noqa: D102
        if v in available_timezones():
            return v

        msg = f'Unknown time zone `{v}`'
        raise ValueError(msg)


class GeneratorParameters(GenerationParameters, frozen=True):
    """Parameters for single generator.

    Attributes
    ----------
    id : str
        Generator unique identified.

    path : Path
        Path to configuration.

    live_mode : bool, default=True
        Whether to use live mode and generate events at moments defined
        by timestamp values or sample mode to generate all events at a
        time.

    skip_past : bool, default=True
        Whether to skip past timestamps when starting generation in
        live mode.

    params: dict[str, Any], default={}
        Parameters that can be used in generator configuration file.

    """

    id: str = Field(min_length=1)
    path: Path
    live_mode: bool = True
    skip_past: bool = Field(default=True)
    params: dict[str, Any] = Field(default_factory=dict)

    def as_absolute(self, base_dir: Path) -> Self:
        """Get instance with absolute path to generator.

        Parameters
        ----------
        base_dir : Path
            Base directory.

        Returns
        -------
        Self
            Same instance if path is already absolute or new instance
            with absolute path.

        """
        if self.path.is_absolute():
            return self

        kwargs = {attr: getattr(self, attr) for attr in self.model_fields_set}
        kwargs.update(path=base_dir / self.path)

        return self.__class__(**kwargs)

    def as_relative(self, base_dir: Path) -> Self:
        """Get instance with relative path to generator.

        Parameters
        ----------
        base_dir : Path
            Base directory.

        Returns
        -------
        Self
            Same instance if path is already relative or new instance
            with relative path.

        Raises
        ------
        ValueError
            If base_dir is not a parent of the path.

        """
        if not self.path.is_absolute():
            return self

        kwargs = {attr: getattr(self, attr) for attr in self.model_fields_set}
        kwargs.update(path=self.path.relative_to(base_dir))

        return self.__class__(**kwargs)
