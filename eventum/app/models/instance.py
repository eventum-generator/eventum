"""Model describing the running application instance and its host."""

import platform
import socket
from datetime import datetime

import psutil
from pydantic import BaseModel, Field, computed_field

import eventum


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
        default=platform.python_version(),
        description='Python version',
    )
    python_implementation: str = Field(
        default=platform.python_implementation(),
        description='Python implementation',
    )
    python_compiler: str = Field(
        default=platform.python_compiler(),
        description='Python compiler',
    )

    # Platform
    platform: str = Field(
        default=platform.platform(),
        description='Host platform',
    )

    # Host info
    host_name: str = Field(
        default=socket.gethostname(),
        description='Host name',
    )
    host_ip_v4: str = Field(
        default=socket.gethostbyname(socket.gethostname()),
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

    # Network
    @computed_field  # type: ignore[prop-decorator]
    @property
    def network_sent_bytes(self) -> int:
        """Number of sent bytes using network."""
        return psutil.net_io_counters().bytes_sent

    @computed_field  # type: ignore[prop-decorator]
    @property
    def network_received_bytes(self) -> int:
        """Number of received bytes using network."""
        return psutil.net_io_counters().bytes_recv

    # Disk IO
    @computed_field  # type: ignore[prop-decorator]
    @property
    def disk_written_bytes(self) -> int:
        """Number of written bytes."""
        counters = psutil.disk_io_counters()
        if counters is None:
            return 0

        return counters.write_bytes

    @computed_field  # type: ignore[prop-decorator]
    @property
    def disk_read_bytes(self) -> int:
        """Number of read bytes."""
        counters = psutil.disk_io_counters()
        if counters is None:
            return 0

        return counters.read_bytes

    # Time
    boot_timestamp: float = Field(
        default=psutil.boot_time(),
        description='Timestamp of host boot up',
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def uptime(self) -> float:
        """Number of seconds since host boot up."""
        current_time = datetime.now().timestamp()  # noqa: DTZ005
        return current_time - self.boot_timestamp
