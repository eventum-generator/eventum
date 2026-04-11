"""Performance metrics collection for integration tests.

Collects periodic snapshots of throughput, memory, file descriptors,
threads, and GC activity.  Produces a ``PerformanceReport`` with
descriptive statistics and linear-regression trend analysis.
"""

from __future__ import annotations

import gc
import math
import os
import resource
import threading
import time
from dataclasses import dataclass, fields


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PerformanceSnapshot:
    """A single point-in-time measurement."""

    timestamp: float  # seconds since collector start
    events_per_second: float
    rss_bytes: int
    fd_count: int
    thread_count: int
    gc_gen0: int
    gc_gen1: int
    gc_gen2: int

    def to_dict(self) -> dict:
        """Serialize to a plain dictionary."""
        return {f.name: getattr(self, f.name) for f in fields(self)}


@dataclass
class PerformanceReport:
    """Aggregated performance statistics computed from snapshots."""

    duration_seconds: float
    total_events: int
    # EPS stats
    eps_mean: float
    eps_stddev: float
    eps_p50: float
    eps_p95: float
    eps_p99: float
    eps_min: float
    eps_max: float
    # Resource stats
    rss_start_bytes: int
    rss_end_bytes: int
    rss_peak_bytes: int
    rss_growth_bytes: int
    fd_start: int
    fd_end: int
    fd_peak: int
    thread_start: int
    thread_end: int
    thread_peak: int
    # GC stats
    gc_collections: tuple[int, int, int]
    # Regression (None when not enough data points)
    eps_slope: float | None = None
    eps_r_squared: float | None = None
    rss_slope: float | None = None

    def to_dict(self) -> dict:
        """Serialize to a plain dictionary."""
        return {f.name: getattr(self, f.name) for f in fields(self)}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _percentile(sorted_values: list[float], pct: float) -> float:
    """Return the *pct*-th percentile from an already-sorted list.

    Uses linear interpolation between surrounding ranks.
    """
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]

    rank = pct / 100.0 * (len(sorted_values) - 1)
    low = int(math.floor(rank))
    high = int(math.ceil(rank))
    if low == high:
        return sorted_values[low]

    fraction = rank - low
    return sorted_values[low] + fraction * (
        sorted_values[high] - sorted_values[low]
    )


def _linear_regression(
    xs: list[float],
    ys: list[float],
) -> tuple[float, float] | None:
    """Ordinary least-squares linear regression.

    Returns ``(slope, r_squared)`` or ``None`` if regression is
    undefined (fewer than 2 points or zero variance in *xs*).
    """
    n = len(xs)
    if n < 2 or n != len(ys):
        return None

    sum_x = sum(xs)
    sum_y = sum(ys)
    sum_xx = sum(x * x for x in xs)
    sum_xy = sum(x * y for x, y in zip(xs, ys))

    denom = n * sum_xx - sum_x * sum_x
    if denom == 0.0:
        return None

    slope = (n * sum_xy - sum_x * sum_y) / denom
    intercept = (sum_y - slope * sum_x) / n

    # R-squared
    y_mean = sum_y / n
    ss_tot = sum((y - y_mean) ** 2 for y in ys)
    if ss_tot == 0.0:
        # All y-values identical — perfect fit with slope 0
        return slope, 1.0

    ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(xs, ys))
    r_squared = 1.0 - ss_res / ss_tot

    return slope, r_squared


# ---------------------------------------------------------------------------
# System probes
# ---------------------------------------------------------------------------


def _read_rss_bytes() -> int:
    """Return current RSS in bytes.

    Prefers ``/proc/{pid}/status`` (Linux). Falls back to
    ``resource.getrusage`` (reports in KiB on Linux, bytes on macOS).
    """
    pid = os.getpid()
    proc_path = f'/proc/{pid}/status'
    try:
        with open(proc_path) as fh:
            for line in fh:
                if line.startswith('VmRSS:'):
                    # Format: "VmRSS:    123456 kB"
                    parts = line.split()
                    return int(parts[1]) * 1024
    except OSError, ValueError, IndexError:
        pass

    # Fallback
    usage = resource.getrusage(resource.RUSAGE_SELF)
    # ru_maxrss is in KiB on Linux, bytes on macOS
    return usage.ru_maxrss * 1024


def _read_fd_count() -> int:
    """Return current open file-descriptor count."""
    pid = os.getpid()
    fd_path = f'/proc/{pid}/fd'
    try:
        return len(os.listdir(fd_path))
    except OSError:
        return -1


def _read_thread_count() -> int:
    """Return current thread count.

    Prefers ``/proc/{pid}/status`` (``Threads:`` line). Falls back to
    ``threading.active_count()``.
    """
    pid = os.getpid()
    proc_path = f'/proc/{pid}/status'
    try:
        with open(proc_path) as fh:
            for line in fh:
                if line.startswith('Threads:'):
                    return int(line.split()[1])
    except OSError, ValueError, IndexError:
        pass

    return threading.active_count()


def _read_gc_collections() -> tuple[int, int, int]:
    """Return cumulative GC collection counts for gen 0, 1, 2."""
    stats = gc.get_stats()
    return (
        stats[0]['collections'],
        stats[1]['collections'],
        stats[2]['collections'],
    )


# ---------------------------------------------------------------------------
# Collector
# ---------------------------------------------------------------------------


class MetricsCollector:
    """Collects periodic performance snapshots during a test run.

    Usage::

        collector = MetricsCollector(warmup_seconds=5.0)
        collector.start()
        for batch in produce_events():
            collector.record_events(len(batch))
        report = collector.finalize()

    Parameters
    ----------
    warmup_seconds:
        Duration (in wall-clock seconds from ``start()``) during which
        snapshots are recorded but **excluded** from statistical
        analysis.  Set to ``0`` to disable warmup.
    snapshot_interval:
        Minimum interval in seconds between automatic snapshots
        triggered by ``record_events()``.
    """

    def __init__(
        self,
        warmup_seconds: float = 5.0,
        snapshot_interval: float = 1.0,
    ) -> None:
        self._warmup_seconds = warmup_seconds
        self._snapshot_interval = snapshot_interval

        self._start_time: float = 0.0
        self._last_snapshot_time: float = 0.0
        self._total_events: int = 0
        self._events_since_snapshot: int = 0

        self._snapshots: list[PerformanceSnapshot] = []
        self._gc_baseline: tuple[int, int, int] = (0, 0, 0)
        self._started: bool = False
        self._last_report: PerformanceReport | None = None

    # - public API ---------------------------------------------------------

    def start(self) -> None:
        """Begin collection.  Triggers a full GC and records baseline."""
        gc.collect()

        self._start_time = time.monotonic()
        self._last_snapshot_time = self._start_time
        self._total_events = 0
        self._events_since_snapshot = 0
        self._snapshots = []
        self._gc_baseline = _read_gc_collections()
        self._started = True

        # Capture the very first (baseline) snapshot at t=0
        self._take_snapshot(eps=0.0)

    def record_events(self, count: int) -> None:
        """Accumulate *count* events and auto-snapshot if the interval elapsed."""
        if not self._started:
            raise RuntimeError('MetricsCollector.start() must be called first')

        self._total_events += count
        self._events_since_snapshot += count

        now = time.monotonic()
        elapsed_since_snapshot = now - self._last_snapshot_time
        if elapsed_since_snapshot >= self._snapshot_interval:
            eps = self._events_since_snapshot / elapsed_since_snapshot
            self._take_snapshot(eps)
            self._events_since_snapshot = 0
            self._last_snapshot_time = now

    @property
    def snapshots(self) -> list[PerformanceSnapshot]:
        """Return collected snapshots (read-only copy)."""
        return list(self._snapshots)

    @property
    def last_report(self) -> PerformanceReport | None:
        """Return the last finalized report, if any."""
        return self._last_report

    def finalize(self) -> PerformanceReport:
        """Stop collection and compute the final ``PerformanceReport``."""
        if not self._started:
            raise RuntimeError('MetricsCollector.start() must be called first')

        end_time = time.monotonic()
        duration = end_time - self._start_time

        # Take a final snapshot if there are un-recorded events
        if self._events_since_snapshot > 0:
            elapsed_since_snapshot = end_time - self._last_snapshot_time
            if elapsed_since_snapshot > 0:
                eps = self._events_since_snapshot / elapsed_since_snapshot
            else:
                eps = 0.0
            self._take_snapshot(eps)

        # Separate warmup vs. analysis snapshots
        analysis_snapshots = [
            s for s in self._snapshots if s.timestamp >= self._warmup_seconds
        ]
        all_snapshots = self._snapshots

        if not analysis_snapshots:
            # If everything is warmup, use all snapshots anyway
            analysis_snapshots = all_snapshots

        # - EPS statistics -------------------------------------------------
        eps_values = sorted(s.events_per_second for s in analysis_snapshots)
        eps_mean = sum(eps_values) / len(eps_values) if eps_values else 0.0
        eps_variance = (
            sum((v - eps_mean) ** 2 for v in eps_values) / len(eps_values)
            if eps_values
            else 0.0
        )
        eps_stddev = math.sqrt(eps_variance)

        eps_p50 = _percentile(eps_values, 50)
        eps_p95 = _percentile(eps_values, 95)
        eps_p99 = _percentile(eps_values, 99)
        eps_min = eps_values[0] if eps_values else 0.0
        eps_max = eps_values[-1] if eps_values else 0.0

        # - Resource statistics --------------------------------------------
        rss_values = [s.rss_bytes for s in all_snapshots]
        fd_values = [s.fd_count for s in all_snapshots]
        thread_values = [s.thread_count for s in all_snapshots]

        # - GC delta -------------------------------------------------------
        gc_now = _read_gc_collections()
        gc_collections = (
            gc_now[0] - self._gc_baseline[0],
            gc_now[1] - self._gc_baseline[1],
            gc_now[2] - self._gc_baseline[2],
        )

        # - Linear regression (on analysis snapshots only) -----------------
        timestamps = [s.timestamp for s in analysis_snapshots]
        eps_series = [s.events_per_second for s in analysis_snapshots]
        rss_series = [float(s.rss_bytes) for s in analysis_snapshots]

        eps_reg = _linear_regression(timestamps, eps_series)
        rss_reg = _linear_regression(timestamps, rss_series)

        self._started = False

        report = PerformanceReport(
            duration_seconds=duration,
            total_events=self._total_events,
            # EPS
            eps_mean=eps_mean,
            eps_stddev=eps_stddev,
            eps_p50=eps_p50,
            eps_p95=eps_p95,
            eps_p99=eps_p99,
            eps_min=eps_min,
            eps_max=eps_max,
            # RSS
            rss_start_bytes=rss_values[0] if rss_values else 0,
            rss_end_bytes=rss_values[-1] if rss_values else 0,
            rss_peak_bytes=max(rss_values) if rss_values else 0,
            rss_growth_bytes=(rss_values[-1] - rss_values[0])
            if rss_values
            else 0,
            # FD
            fd_start=fd_values[0] if fd_values else 0,
            fd_end=fd_values[-1] if fd_values else 0,
            fd_peak=max(fd_values) if fd_values else 0,
            # Threads
            thread_start=thread_values[0] if thread_values else 0,
            thread_end=thread_values[-1] if thread_values else 0,
            thread_peak=max(thread_values) if thread_values else 0,
            # GC
            gc_collections=gc_collections,
            # Regression
            eps_slope=eps_reg[0] if eps_reg else None,
            eps_r_squared=eps_reg[1] if eps_reg else None,
            rss_slope=rss_reg[0] if rss_reg else None,
        )
        self._last_report = report
        return report

    # - internals ----------------------------------------------------------

    def _take_snapshot(self, eps: float) -> None:
        """Record a ``PerformanceSnapshot`` at the current moment."""
        now = time.monotonic()
        gc_counts = _read_gc_collections()

        snapshot = PerformanceSnapshot(
            timestamp=now - self._start_time,
            events_per_second=eps,
            rss_bytes=_read_rss_bytes(),
            fd_count=_read_fd_count(),
            thread_count=_read_thread_count(),
            gc_gen0=gc_counts[0],
            gc_gen1=gc_counts[1],
            gc_gen2=gc_counts[2],
        )
        self._snapshots.append(snapshot)
