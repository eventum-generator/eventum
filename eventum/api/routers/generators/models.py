"""Models."""

from abc import ABC
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field, computed_field


class GeneratorStatus(BaseModel, frozen=True, extra='forbid'):
    """Status of generator."""

    is_initializing: bool = Field(
        description='Whether the generator is initializing',
    )
    is_running: bool = Field(description='Whether the generator is running')
    is_ended_up: bool = Field(
        description=(
            'Whether the generator has ended execution with or without errors'
        ),
    )
    is_ended_up_successfully: bool = Field(
        description='Whether the generator has ended execution successfully',
    )
    is_stopping: bool = Field(
        description='Whether the generator is stopping',
    )


class GeneratorInfo(BaseModel, frozen=True, extra='forbid'):
    """Info about generator."""

    id: str = Field(min_length=1, description='ID of the generator')
    path: Path = Field(description='Path to the generator project')
    status: GeneratorStatus = Field(
        description='Execution status of the generator',
    )
    start_time: datetime | None = Field(
        description='Start time of the generator',
    )


class PluginStats(BaseModel, ABC, frozen=True, extra='forbid'):
    """Plugin statistics."""

    plugin_name: str = Field(min_length=1, description='Name of the plugin')
    plugin_id: int = Field(ge=0, description='ID of the plugin')


class InputPluginStats(PluginStats, frozen=True, extra='forbid'):
    """Input plugin statistics."""

    generated: int = Field(ge=0, description='Number of generated timestamps')


class EventPluginStats(PluginStats, frozen=True, extra='forbid'):
    """Event plugin statistics."""

    produced: int = Field(ge=0, description='Number of produced events')
    produce_failed: int = Field(
        ge=0,
        description='Number of unsuccessfully produced events',
    )
    dropped: int = Field(
        ge=0,
        description='Number of intentionally dropped events',
    )


class OutputPluginStats(PluginStats, frozen=True, extra='forbid'):
    """Output plugin statistics."""

    written: int = Field(ge=0, description='Number of written events')
    write_failed: int = Field(
        ge=0,
        description='Number of unsuccessfully written events',
    )
    format_failed: int = Field(
        ge=0,
        description='Number of unsuccessfully formatted events',
    )


class QueueStats(BaseModel, frozen=True, extra='forbid'):
    """Fill level of a queue between two pipeline stages."""

    size: int = Field(
        ge=0,
        description='Number of batches waiting in the queue',
    )
    maxsize: int = Field(
        ge=1,
        description='Maximum number of batches the queue holds',
    )


class QueuesStats(BaseModel, frozen=True, extra='forbid'):
    """Fill levels of the queues between the pipeline stages."""

    timestamps: QueueStats = Field(
        description='Queue between the input and the event stage',
    )
    events: QueueStats = Field(
        description='Queue between the event and the output stage',
    )


class ResourcesStats(BaseModel, frozen=True, extra='forbid'):
    """Runtime resources occupied by a generator.

    Memory is absent by nature: generators share the process heap, so
    the share of it belonging to one generator is not observable. Queue
    fill levels stand in for it, since the queues hold the bulk of what
    a generator keeps in flight.
    """

    thread_count: int = Field(
        ge=0,
        description='Number of threads the generator runs',
    )
    cpu_seconds: float = Field(
        ge=0,
        description=(
            'CPU time consumed by those threads since the generator '
            'started, growing over the lifetime of the generator'
        ),
    )
    run_delay_seconds: float = Field(
        ge=0,
        description=(
            'Time those threads spent ready to run while waiting for a '
            'processor since the generator started, growing over the '
            'lifetime of the generator; reported on Linux only'
        ),
    )
    disk_read_bytes: int = Field(
        ge=0,
        description=(
            'Number of bytes those threads read through the file '
            'system since the generator started; reported on Linux only'
        ),
    )
    disk_written_bytes: int = Field(
        ge=0,
        description=(
            'Number of bytes those threads wrote through the file '
            'system since the generator started; reported on Linux only'
        ),
    )
    network_sent_bytes: int = Field(
        ge=0,
        description=(
            'Number of bytes those threads sent over the network since '
            'the generator started'
        ),
    )
    network_received_bytes: int = Field(
        ge=0,
        description=(
            'Number of bytes those threads received over the network '
            'since the generator started'
        ),
    )
    queues: QueuesStats = Field(
        description='Fill levels of the queues between the pipeline stages',
    )


class GeneratorStats(BaseModel, frozen=True, extra='forbid'):
    """Stats of generator."""

    id: str = Field(min_length=1, description='Generator id')
    start_time: datetime = Field(description='Start time of the generator')
    resources: ResourcesStats = Field(
        description='Runtime resources occupied by the generator',
    )
    input: list[InputPluginStats] = Field(
        description='Input plugins statistics',
    )
    event: EventPluginStats = Field(description='Event plugin statistics')
    output: list[OutputPluginStats] = Field(
        description='Output plugins statistics',
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_generated(self) -> int:
        """Total number of timestamps generated across all input plugins."""
        total = 0
        for plugin in self.input:
            total += plugin.generated

        return total

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_written(self) -> int:
        """Total number of written event across all output plugins."""
        total = 0
        for plugin in self.output:
            total += plugin.written

        return total

    @computed_field  # type: ignore[prop-decorator]
    @property
    def uptime(self) -> float:
        """Number of seconds since generator start time."""
        now = datetime.now().astimezone(tz=ZoneInfo('UTC'))
        delta_start = now - self.start_time

        return delta_start.total_seconds()

    @computed_field  # type: ignore[prop-decorator]
    @property
    def input_eps(self) -> float:
        """Average number of events per second for total number
        of generated timestamps since generator start time.
        """
        return self.total_generated / self.uptime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def output_eps(self) -> float:
        """Average number of events per second for total number
        of written events since generator start time.
        """
        return self.total_written / self.uptime


class BulkStartResponse(BaseModel, extra='forbid', frozen=True):
    """Response model that contains info about running and non running
    generator ids after bulk start operation.

    Attributes
    ----------
    running_generator_ids : list[str]
        List of ids of running generators.

    non_running_generator_ids : list[str]
        List of ids of non running generators.

    """

    running_generator_ids: list[str]
    non_running_generator_ids: list[str]


class RenameGeneratorRequest(BaseModel, extra='forbid', frozen=True):
    """New id for an existing generator."""

    new_id: str = Field(min_length=1, description='New generator id')
