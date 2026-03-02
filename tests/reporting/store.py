"""Session-scoped store for collecting test results and metrics.

Used by the root ``conftest.py`` to accumulate per-test performance
data which is later rendered into an HTML report by ``html.py``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from tests.metrics import (
    MetricsCollector,
    PerformanceReport,
    PerformanceSnapshot,
)
from tests.performance._helpers import PerfResult


def _report_from_perf_result(pr: PerfResult) -> PerformanceReport:
    """Create a minimal ``PerformanceReport`` from a ``PerfResult``."""
    eps = (
        pr.total_events / pr.duration_seconds
        if pr.duration_seconds > 0
        else 0.0
    )
    return PerformanceReport(
        duration_seconds=pr.duration_seconds,
        total_events=pr.total_events,
        eps_mean=eps,
        eps_stddev=0.0,
        eps_p50=eps,
        eps_p95=eps,
        eps_p99=eps,
        eps_min=eps,
        eps_max=eps,
        rss_start_bytes=0,
        rss_end_bytes=0,
        rss_peak_bytes=0,
        rss_growth_bytes=0,
        fd_start=0,
        fd_end=0,
        fd_peak=0,
        thread_start=0,
        thread_end=0,
        thread_peak=0,
        gc_collections=(0, 0, 0),
    )


@dataclass
class TestResult:
    """Captured result of a single test run."""

    node_id: str
    outcome: str  # 'passed' / 'failed' / 'skipped'
    duration: float
    report: PerformanceReport | None = None
    snapshots: list[PerformanceSnapshot] = field(
        default_factory=list,
    )


class ReportStore:
    """Accumulate test results across a pytest session.

    Instantiated once per session in ``pytest_configure`` and
    accessed via ``config._report_store``.
    """

    def __init__(self) -> None:
        """Initialize with an empty results list."""
        self.results: list[TestResult] = []

    def add_test_result(
        self,
        node_id: str,
        pytest_report: object,
        metrics_collector: MetricsCollector | None = None,
        perf_result: PerfResult | None = None,
    ) -> None:
        """Record a test result, extracting metrics."""
        outcome = getattr(pytest_report, 'outcome', 'unknown')
        duration = getattr(pytest_report, 'duration', 0.0)

        perf_report: PerformanceReport | None = None
        snapshots: list[PerformanceSnapshot] = []

        if metrics_collector is not None:
            perf_report = metrics_collector.last_report
            snapshots = metrics_collector.snapshots
        elif perf_result is not None and perf_result.duration_seconds > 0:
            perf_report = _report_from_perf_result(perf_result)

        self.results.append(
            TestResult(
                node_id=node_id,
                outcome=outcome,
                duration=duration,
                report=perf_report,
                snapshots=snapshots,
            )
        )
