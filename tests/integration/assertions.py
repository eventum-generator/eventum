"""Statistical assertion helpers for performance tests.

Each function raises ``AssertionError`` with a detailed message
including the actual measured values when a threshold is exceeded.
"""

from __future__ import annotations

from tests.integration.metrics import PerformanceReport


def assert_no_throughput_degradation(
    report: PerformanceReport,
    max_slope_pct: float = -5.0,
) -> None:
    """Assert that EPS is not declining over time.

    Parameters
    ----------
    report:
        The finalized performance report.
    max_slope_pct:
        Maximum acceptable EPS slope expressed as **percent per minute**.
        A value of ``-5.0`` means up to 5 % decline per minute is
        tolerated.  Must be negative or zero.

    Raises
    ------
    AssertionError
        If the EPS trend slope is more negative than *max_slope_pct*.
    """
    if report.eps_slope is None or report.eps_mean == 0:
        # Not enough data points for regression — nothing to assert
        return

    # Convert slope (events/sec per second) to percent-per-minute
    # slope is in eps/sec, so per minute is slope * 60
    # relative to mean: (slope * 60) / mean * 100
    slope_pct_per_min = (report.eps_slope * 60.0 / report.eps_mean) * 100.0

    assert slope_pct_per_min >= max_slope_pct, (
        f"Throughput degradation detected: "
        f"EPS slope = {slope_pct_per_min:+.2f}%/min "
        f"(threshold: {max_slope_pct:+.2f}%/min). "
        f"EPS mean = {report.eps_mean:.1f}, "
        f"EPS slope (raw) = {report.eps_slope:.4f} eps/sec^2, "
        f"R² = {report.eps_r_squared:.4f}, "
        f"duration = {report.duration_seconds:.1f}s."
    )


def assert_no_memory_leak(
    report: PerformanceReport,
    max_growth_mb: float = 50.0,
    max_slope_mb_per_min: float = 1.0,
) -> None:
    """Assert that RSS memory growth is bounded.

    Parameters
    ----------
    report:
        The finalized performance report.
    max_growth_mb:
        Maximum acceptable total RSS growth in megabytes.
    max_slope_mb_per_min:
        Maximum acceptable RSS growth rate in MB/min from linear
        regression.

    Raises
    ------
    AssertionError
        If RSS growth exceeds either threshold.
    """
    growth_mb = report.rss_growth_bytes / (1024 * 1024)

    assert growth_mb <= max_growth_mb, (
        f"Memory growth exceeded threshold: "
        f"RSS grew by {growth_mb:.2f} MB "
        f"(threshold: {max_growth_mb:.2f} MB). "
        f"RSS start = {report.rss_start_bytes / (1024 * 1024):.1f} MB, "
        f"RSS end = {report.rss_end_bytes / (1024 * 1024):.1f} MB, "
        f"RSS peak = {report.rss_peak_bytes / (1024 * 1024):.1f} MB, "
        f"duration = {report.duration_seconds:.1f}s."
    )

    if report.rss_slope is not None:
        # rss_slope is in bytes/sec; convert to MB/min
        slope_mb_per_min = report.rss_slope * 60.0 / (1024 * 1024)

        assert slope_mb_per_min <= max_slope_mb_per_min, (
            f"Memory leak trend detected: "
            f"RSS slope = {slope_mb_per_min:.4f} MB/min "
            f"(threshold: {max_slope_mb_per_min:.4f} MB/min). "
            f"RSS growth = {growth_mb:.2f} MB, "
            f"RSS start = {report.rss_start_bytes / (1024 * 1024):.1f} MB, "
            f"RSS end = {report.rss_end_bytes / (1024 * 1024):.1f} MB, "
            f"duration = {report.duration_seconds:.1f}s."
        )


def assert_no_fd_leak(
    report: PerformanceReport,
    max_growth: int = 10,
) -> None:
    """Assert that file descriptor count did not grow excessively.

    Parameters
    ----------
    report:
        The finalized performance report.
    max_growth:
        Maximum acceptable FD count increase (end minus start).

    Raises
    ------
    AssertionError
        If FD growth exceeds *max_growth*.
    """
    fd_growth = report.fd_end - report.fd_start

    assert fd_growth <= max_growth, (
        f"File descriptor leak detected: "
        f"FD count grew by {fd_growth} "
        f"(threshold: {max_growth}). "
        f"FD start = {report.fd_start}, "
        f"FD end = {report.fd_end}, "
        f"FD peak = {report.fd_peak}, "
        f"duration = {report.duration_seconds:.1f}s."
    )


def assert_threads_stable(
    report: PerformanceReport,
    max_growth: int = 5,
) -> None:
    """Assert that thread count did not grow excessively.

    Parameters
    ----------
    report:
        The finalized performance report.
    max_growth:
        Maximum acceptable thread count increase (end minus start).

    Raises
    ------
    AssertionError
        If thread growth exceeds *max_growth*.
    """
    thread_growth = report.thread_end - report.thread_start

    assert thread_growth <= max_growth, (
        f"Thread leak detected: "
        f"thread count grew by {thread_growth} "
        f"(threshold: {max_growth}). "
        f"threads start = {report.thread_start}, "
        f"threads end = {report.thread_end}, "
        f"threads peak = {report.thread_peak}, "
        f"duration = {report.duration_seconds:.1f}s."
    )
