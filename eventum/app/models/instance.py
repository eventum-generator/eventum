"""Model describing the running application instance and its host."""

import platform
import socket
from datetime import datetime

import psutil
from pydantic import BaseModel, Field, computed_field

import eventum
from eventum.utils.net_accounting import bytes_received, bytes_sent

_PROCESS = psutil.Process()


class InstanceInfo(BaseModel, extra='forbid', frozen=True):
    """Information about the running app instance and its host.

    Built by reading host metrics through syscalls, so constructing it
    can block - call it from a worker thread on the event loop.
    """

    # App
    app_version: str = Field(
        default=eventum.__version__,
        description='Application version',
    )
    python_version: str = Field(
        default_factory=platform.python_version,
        description='Python version',
    )
    python_implementation: str = Field(
        default_factory=platform.python_implementation,
        description='Python implementation',
    )
    python_compiler: str = Field(
        default_factory=platform.python_compiler,
        description='Python compiler',
    )

    # Platform
    platform: str = Field(
        default_factory=platform.platform,
        description='Host platform',
    )

    # Host info
    host_name: str = Field(
        default_factory=socket.gethostname,
        description='Host name',
    )
    host_ip_v4: str = Field(
        default_factory=lambda: socket.gethostbyname(socket.gethostname()),
        description='Host IPv4',
    )

    # CPU
    @computed_field  # type: ignore[prop-decorator]
    @property
    def cpu_count(self) -> int | None:
        """Number of logical CPUs on host."""
        return psutil.cpu_count()

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cpu_frequency_mhz(self) -> float:
        """Current CPU frequency in MHz."""
        return psutil.cpu_freq().current

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cpu_percent(self) -> float:
        """Current CPU usage in percents."""
        return psutil.cpu_percent()

    # Memory
    @computed_field  # type: ignore[prop-decorator]
    @property
    def memory_total_bytes(self) -> int:
        """Total RAM memory in bytes on host."""
        return psutil.virtual_memory().total

    @computed_field  # type: ignore[prop-decorator]
    @property
    def memory_used_bytes(self) -> int:
        """Used RAM in bytes."""
        return psutil.virtual_memory().used

    @computed_field  # type: ignore[prop-decorator]
    @property
    def memory_available_bytes(self) -> int:
        """Available RAM in bytes."""
        return psutil.virtual_memory().available

    @computed_field  # type: ignore[prop-decorator]
    @property
    def process_memory_bytes(self) -> int:
        """Resident memory of this application in bytes."""
        try:
            return _PROCESS.memory_info().rss
        except psutil.Error, OSError:
            return 0

    # File descriptors. Reported for the application alone: the
    # descriptor table belongs to the process and is shared by every
    # thread in it, so a generator has no figure of its own.
    @computed_field  # type: ignore[prop-decorator]
    @property
    def process_open_fds(self) -> int:
        """Number of file descriptors this application holds open."""
        try:
            return _PROCESS.num_fds()
        except psutil.Error, OSError, AttributeError:
            return 0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def process_max_fds(self) -> int:
        """Maximum number of file descriptors this application may open."""
        try:
            soft_limit, _ = _PROCESS.rlimit(psutil.RLIMIT_NOFILE)
        except psutil.Error, OSError, AttributeError:
            return 0

        return soft_limit

    # Network
    @computed_field  # type: ignore[prop-decorator]
    @property
    def network_sent_bytes(self) -> int:
        """Number of bytes sent over network by this application."""
        return bytes_sent()

    @computed_field  # type: ignore[prop-decorator]
    @property
    def network_received_bytes(self) -> int:
        """Number of bytes received over network by this application."""
        return bytes_received()

    # Disk IO
    @computed_field  # type: ignore[prop-decorator]
    @property
    def disk_written_bytes(self) -> int:
        """Number of bytes written to disk by this application."""
        return self._disk_bytes('write')

    @computed_field  # type: ignore[prop-decorator]
    @property
    def disk_read_bytes(self) -> int:
        """Number of bytes read from disk by this application."""
        return self._disk_bytes('read')

    @staticmethod
    def _disk_bytes(direction: str) -> int:
        """Get bytes the application passed through the file system.

        Counts the bytes handed to the system calls rather than the ones
        that reached the block device, which is the counter a generator
        is accounted by, so the two views stay comparable. Outside Linux
        only the block device counter exists and is reported instead.
        """
        try:
            counters = _PROCESS.io_counters()
        except psutil.Error, OSError:
            return 0

        return getattr(
            counters,
            f'{direction}_chars',
            getattr(counters, f'{direction}_bytes', 0),
        )

    # Time
    boot_timestamp: float = Field(
        default_factory=psutil.boot_time,
        description='Timestamp of host boot up',
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def uptime(self) -> float:
        """Number of seconds since host boot up."""
        current_time = datetime.now().timestamp()  # noqa: DTZ005
        return current_time - self.boot_timestamp
