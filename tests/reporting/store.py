"""Session-scoped store for collecting test results and metrics.

Used by the root ``conftest.py`` to accumulate per-test performance
data which is later rendered into an HTML report by ``html.py``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from tests.integration.metrics import (
    MetricsCollector,
    PerformanceReport,
    PerformanceSnapshot,
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
    scale_data: dict[int, dict] | None = None


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
    ) -> None:
        """Record a test result, extracting metrics."""
        outcome = getattr(pytest_report, 'outcome', 'unknown')
        duration = getattr(pytest_report, 'duration', 0.0)

        perf_report: PerformanceReport | None = None
        snapshots: list[PerformanceSnapshot] = []

        if metrics_collector is not None:
            perf_report = metrics_collector.last_report
            snapshots = metrics_collector.snapshots

        self.results.append(
            TestResult(
                node_id=node_id,
                outcome=outcome,
                duration=duration,
                report=perf_report,
                snapshots=snapshots,
            )
        )

    def add_scale_result(
        self,
        node_id: str,
        scale_data: dict[int, dict],
    ) -> None:
        """Attach scale ramp-up data to an existing result.

        Finds the matching ``TestResult`` by *node_id* suffix and
        attaches *scale_data*; if not found, creates a new entry.
        """
        for result in self.results:
            if (
                result.node_id.endswith(node_id)
                or node_id in result.node_id
            ):
                result.scale_data = scale_data
                return

        # Fallback: create a minimal entry
        self.results.append(
            TestResult(
                node_id=node_id,
                outcome='passed',
                duration=0.0,
                scale_data=scale_data,
            )
        )
