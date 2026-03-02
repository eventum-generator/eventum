"""Root conftest — test report generation via ``--test-report``.

Hooks into pytest's reporting lifecycle to auto-capture performance
metrics from any test that uses a ``metrics_collector`` fixture.
When ``--test-report=<path>`` is passed, an interactive HTML report
with Plotly charts is generated at session end.
"""

from __future__ import annotations

import os
import sysconfig
from collections.abc import Generator

import pytest

# On free-threaded Python, disable aiokafka C extensions to prevent
# the GIL from being re-enabled (extensions haven't declared nogil yet).
if sysconfig.get_config_var('Py_GIL_DISABLED'):
    os.environ.setdefault('AIOKAFKA_NO_EXTENSIONS', '1')

from tests.reporting.store import ReportStore

# ------------------------------------------------------------------
# CLI option
# ------------------------------------------------------------------


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add ``--test-report`` CLI flag."""
    parser.addoption(
        '--test-report',
        default=None,
        metavar='PATH',
        help=('Generate an interactive HTML test report at PATH.'),
    )


# ------------------------------------------------------------------
# Session lifecycle
# ------------------------------------------------------------------


def pytest_configure(config: pytest.Config) -> None:
    """Create a session-scoped ReportStore."""
    config._report_store = ReportStore()  # type: ignore[attr-defined]  # noqa: SLF001


def pytest_sessionfinish(
    session: pytest.Session,
    exitstatus: int,  # noqa: ARG001
) -> None:
    """Generate HTML report if ``--test-report`` was given."""
    config = session.config
    path = config.getoption('--test-report', default=None)
    store: ReportStore = config._report_store  # type: ignore[attr-defined]  # noqa: SLF001

    if path and store.results:
        from tests.reporting.html import generate_html_report

        generate_html_report(store, path)


# ------------------------------------------------------------------
# Per-test hook — auto-capture metrics_collector data
# ------------------------------------------------------------------


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(
    item: pytest.Item,
    call: pytest.CallInfo,  # noqa: ARG001
) -> Generator[None]:
    """Capture test outcome and metrics after ``call`` phase."""
    outcome = yield
    if outcome is None:
        return
    report = outcome.get_result()

    if report.when != 'call':
        return

    store: ReportStore = item.config._report_store  # type: ignore[attr-defined]  # noqa: SLF001
    mc = item.funcargs.get('metrics_collector')  # type: ignore[attr-defined]
    pr = item.funcargs.get('perf_result')  # type: ignore[attr-defined]
    store.add_test_result(item.nodeid, report, mc, pr)

