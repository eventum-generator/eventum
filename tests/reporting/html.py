"""Self-contained HTML report with interactive Plotly charts.

Produces a single ``.html`` file that can be opened in any browser.
Charts are rendered client-side via the Plotly CDN.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from tests.reporting.store import ReportStore, TestResult

PLOTLY_CDN = 'https://cdn.plot.ly/plotly-3.0.1.min.js'


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _short_name(node_id: str) -> str:
    """Extract a short test name from a pytest node id."""
    if '::' in node_id:
        return node_id.rsplit('::', maxsplit=1)[-1]
    return node_id.rsplit('/', maxsplit=1)[-1]


def _js_plot(div_id: str, traces: list, layout: dict) -> str:
    """Build a ``Plotly.newPlot(...)`` JS call."""
    return (
        f'Plotly.newPlot("{div_id}", '
        f'{json.dumps(traces)}, '
        f'{json.dumps(layout)}, '
        f'{{responsive: true}});'
    )


# ------------------------------------------------------------------
# Chart builders — each returns a JS snippet or empty string
# ------------------------------------------------------------------


def _eps_time_series(results: list[TestResult]) -> str:
    """EPS over time — one line trace per test."""
    traces = []
    for r in results:
        if not r.snapshots:
            continue
        traces.append({
            'x': [s.timestamp for s in r.snapshots],
            'y': [s.events_per_second for s in r.snapshots],
            'mode': 'lines',
            'name': _short_name(r.node_id),
        })
    if not traces:
        return ''
    return _js_plot('eps-chart', traces, {
        'title': 'Events per Second Over Time',
        'xaxis': {'title': 'Time (seconds)'},
        'yaxis': {'title': 'EPS'},
        'hovermode': 'x unified',
    })


def _rss_time_series(results: list[TestResult]) -> str:
    """RSS memory over time in MB."""
    traces = []
    for r in results:
        if not r.snapshots:
            continue
        traces.append({
            'x': [s.timestamp for s in r.snapshots],
            'y': [
                s.rss_bytes / (1024 * 1024)
                for s in r.snapshots
            ],
            'mode': 'lines',
            'name': _short_name(r.node_id),
        })
    if not traces:
        return ''
    return _js_plot('rss-chart', traces, {
        'title': 'RSS Memory Over Time',
        'xaxis': {'title': 'Time (seconds)'},
        'yaxis': {'title': 'RSS (MB)'},
        'hovermode': 'x unified',
    })


def _resource_chart(results: list[TestResult]) -> str:
    """FD count and thread count over time."""
    fd_traces: list[dict] = []
    thread_traces: list[dict] = []
    for r in results:
        if not r.snapshots:
            continue
        xs = [s.timestamp for s in r.snapshots]
        name = _short_name(r.node_id)
        fd_traces.append({
            'x': xs,
            'y': [s.fd_count for s in r.snapshots],
            'mode': 'lines',
            'name': f'{name} (FD)',
            'yaxis': 'y',
        })
        thread_traces.append({
            'x': xs,
            'y': [s.thread_count for s in r.snapshots],
            'mode': 'lines',
            'name': f'{name} (threads)',
            'yaxis': 'y2',
            'line': {'dash': 'dash'},
        })
    if not fd_traces:
        return ''
    return _js_plot(
        'resource-chart',
        fd_traces + thread_traces,
        {
            'title': 'File Descriptors & Threads',
            'xaxis': {'title': 'Time (seconds)'},
            'yaxis': {'title': 'FD Count', 'side': 'left'},
            'yaxis2': {
                'title': 'Thread Count',
                'side': 'right',
                'overlaying': 'y',
            },
            'hovermode': 'x unified',
        },
    )


def _eps_box_plot(results: list[TestResult]) -> str:
    """Box plot of EPS distributions across tests."""
    traces = []
    for r in results:
        if not r.snapshots:
            continue
        eps = [
            s.events_per_second
            for s in r.snapshots
            if s.events_per_second > 0
        ]
        if not eps:
            continue
        traces.append({
            'y': eps,
            'type': 'box',
            'name': _short_name(r.node_id),
            'boxpoints': False,
        })
    if not traces:
        return ''
    return _js_plot('eps-box-chart', traces, {
        'title': 'EPS Distribution by Test',
        'yaxis': {'title': 'Events per Second'},
    })


def _scale_ramp_up(results: list[TestResult]) -> str:
    """Aggregate EPS vs concurrency level per backend."""
    scale = [r for r in results if r.scale_data]
    if not scale:
        return ''
    traces = []
    for r in scale:
        sd = r.scale_data
        if sd is None:
            continue
        levels = sorted(sd.keys())
        traces.append({
            'x': [str(lv) for lv in levels],
            'y': [
                sd[lv]['aggregate_eps']
                for lv in levels
            ],
            'type': 'bar',
            'name': _short_name(r.node_id),
        })
    return _js_plot('scale-chart', traces, {
        'title': 'Scale Ramp-Up: Aggregate EPS',
        'xaxis': {'title': 'Concurrency Level'},
        'yaxis': {'title': 'Aggregate EPS'},
        'barmode': 'group',
    })


def _trend_chart(results: list[TestResult]) -> str:
    """EPS slope and RSS slope per test."""
    with_trends = [
        r for r in results
        if r.report and r.report.eps_slope is not None
    ]
    if not with_trends:
        return ''

    names = [_short_name(r.node_id) for r in with_trends]

    eps_slopes = []
    rss_slopes = []
    for r in with_trends:
        rp = r.report
        if rp is None or rp.eps_slope is None:
            continue
        if rp.eps_mean > 0:
            eps_slopes.append(
                rp.eps_slope * 60.0 / rp.eps_mean * 100.0,
            )
        else:
            eps_slopes.append(0.0)
        if rp.rss_slope is not None:
            rss_slopes.append(
                rp.rss_slope * 60.0 / (1024 * 1024),
            )
        else:
            rss_slopes.append(0.0)

    traces = [
        {
            'x': names,
            'y': eps_slopes,
            'type': 'bar',
            'name': 'EPS slope (%/min)',
            'marker': {'color': 'rgba(55, 128, 191, 0.7)'},
        },
        {
            'x': names,
            'y': rss_slopes,
            'type': 'bar',
            'name': 'RSS slope (MB/min)',
            'yaxis': 'y2',
            'marker': {'color': 'rgba(219, 64, 82, 0.7)'},
        },
    ]
    return _js_plot('trend-chart', traces, {
        'title': 'Trend Analysis: EPS & RSS Slopes',
        'yaxis': {
            'title': 'EPS slope (%/min)',
            'side': 'left',
        },
        'yaxis2': {
            'title': 'RSS slope (MB/min)',
            'side': 'right',
            'overlaying': 'y',
        },
        'barmode': 'group',
    })


# ------------------------------------------------------------------
# HTML sections
# ------------------------------------------------------------------


def _summary_cards(results: list[TestResult]) -> str:
    """Build summary stat cards."""
    total = len(results)
    passed = sum(1 for r in results if r.outcome == 'passed')
    failed = sum(1 for r in results if r.outcome == 'failed')
    skipped = sum(
        1 for r in results if r.outcome == 'skipped'
    )
    duration = sum(r.duration for r in results)

    def _card(value: str, label: str, cls: str = '') -> str:
        c = f' {cls}' if cls else ''
        return (
            f'<div class="card{c}">'
            f'<div class="card-value">{value}</div>'
            f'<div class="card-label">{label}</div>'
            f'</div>'
        )

    return (
        '<div class="summary-cards">'
        + _card(str(total), 'Total')
        + _card(str(passed), 'Passed', 'passed')
        + _card(str(failed), 'Failed', 'failed')
        + _card(str(skipped), 'Skipped', 'skipped')
        + _card(f'{duration:.1f}s', 'Duration')
        + '</div>'
    )


def _detail_row(r: TestResult) -> str:
    """Build one ``<tr>`` for the detail table."""
    name = _short_name(r.node_id)
    cls = r.outcome
    if not r.report:
        return (
            f'<tr class="{cls}">'
            f'<td title="{r.node_id}">{name}</td>'
            f'<td>{r.outcome}</td>'
            f'<td>{r.duration:.1f}</td>'
            + '<td>\u2014</td>' * 10
            + '</tr>'
        )

    rp = r.report
    rss_mb = rp.rss_growth_bytes / (1024 * 1024)
    fd_d = rp.fd_end - rp.fd_start
    thr_d = rp.thread_end - rp.thread_start

    eps_s = ''
    if rp.eps_slope is not None and rp.eps_mean > 0:
        pct = rp.eps_slope * 60.0 / rp.eps_mean * 100.0
        eps_s = f'{pct:+.2f}%/min'

    rss_s = ''
    if rp.rss_slope is not None:
        mb = rp.rss_slope * 60.0 / (1024 * 1024)
        rss_s = f'{mb:+.4f} MB/min'

    return (
        f'<tr class="{cls}">'
        f'<td title="{r.node_id}">{name}</td>'
        f'<td>{r.outcome}</td>'
        f'<td>{r.duration:.1f}</td>'
        f'<td>{rp.eps_mean:.0f}</td>'
        f'<td>{rp.eps_p50:.0f}</td>'
        f'<td>{rp.eps_p95:.0f}</td>'
        f'<td>{rp.eps_p99:.0f}</td>'
        f'<td>{rss_mb:.2f}</td>'
        f'<td>{fd_d:+d}</td>'
        f'<td>{thr_d:+d}</td>'
        f'<td>{eps_s}</td>'
        f'<td>{rss_s}</td>'
        f'<td>{rp.total_events:,}</td>'
        f'</tr>'
    )


def _detail_table(results: list[TestResult]) -> str:
    """Build the per-test performance detail table."""
    header = (
        '<tr>'
        '<th>Test</th><th>Status</th>'
        '<th>Duration</th>'
        '<th>EPS Mean</th><th>p50</th>'
        '<th>p95</th><th>p99</th>'
        '<th>RSS Growth</th>'
        '<th>FD \u0394</th><th>Thread \u0394</th>'
        '<th>EPS Slope</th><th>RSS Slope</th>'
        '<th>Events</th>'
        '</tr>'
    )
    rows = '\n'.join(_detail_row(r) for r in results)
    return (
        f'<table><thead>{header}</thead>'
        f'<tbody>{rows}</tbody></table>'
    )


# ------------------------------------------------------------------
# CSS
# ------------------------------------------------------------------

_CSS = """\
:root {
  --bg: #fff; --bg2: #f8f9fa; --fg: #212529;
  --border: #dee2e6; --accent: #3780bf;
  --green: #28a745; --red: #dc3545; --yellow: #ffc107;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #1a1a2e; --bg2: #16213e; --fg: #e0e0e0;
    --border: #333; --accent: #5dade2;
    --green: #2ecc71; --red: #e74c3c; --yellow: #f39c12;
  }
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont,
    'Segoe UI', Roboto, sans-serif;
  background: var(--bg); color: var(--fg);
  padding: 2rem; max-width: 1400px; margin: 0 auto;
}
h1 { margin-bottom: .5rem; }
.timestamp { color: #888; margin-bottom: 2rem; font-size: .9rem; }
.summary-cards {
  display: flex; gap: 1rem;
  margin-bottom: 2rem; flex-wrap: wrap;
}
.card {
  background: var(--bg2); border: 1px solid var(--border);
  border-radius: 8px; padding: 1rem 1.5rem;
  text-align: center; min-width: 100px;
}
.card-value { font-size: 2rem; font-weight: bold; }
.card-label { font-size: .85rem; color: #888; }
.card.passed .card-value { color: var(--green); }
.card.failed .card-value { color: var(--red); }
.card.skipped .card-value { color: var(--yellow); }
section { margin-bottom: 2rem; }
h2 {
  margin-bottom: 1rem;
  border-bottom: 2px solid var(--accent);
  padding-bottom: .5rem;
}
table {
  width: 100%; border-collapse: collapse;
  font-size: .85rem; overflow-x: auto; display: block;
}
thead { position: sticky; top: 0; }
th, td {
  padding: .5rem .75rem; text-align: left;
  border-bottom: 1px solid var(--border); white-space: nowrap;
}
th { background: var(--bg2); font-weight: 600; }
tr:hover { background: var(--bg2); }
tr.passed td:nth-child(2) { color: var(--green); }
tr.failed td:nth-child(2) { color: var(--red); font-weight: bold; }
tr.skipped td:nth-child(2) { color: var(--yellow); }
.chart { width: 100%; height: 450px; }
footer {
  margin-top: 3rem; color: #888;
  font-size: .8rem; text-align: center;
}
"""


# ------------------------------------------------------------------
# Chart section helper
# ------------------------------------------------------------------


def _chart_section(
    div_id: str,
    title: str,
    *,
    visible: bool,
) -> str:
    """Return a chart ``<section>`` or empty string."""
    if not visible:
        return ''
    return (
        f'<section id="{div_id}-section">'
        f'<h2>{title}</h2>'
        f'<div id="{div_id}" class="chart"></div>'
        f'</section>'
    )


# ------------------------------------------------------------------
# Main entry point
# ------------------------------------------------------------------


def generate_html_report(
    store: ReportStore,
    output_path: str,
) -> None:
    """Generate a self-contained HTML report file."""
    results = store.results
    ts = time.strftime('%Y-%m-%d %H:%M:%S')

    charts_js = '\n'.join(
        s for s in [
            _eps_time_series(results),
            _rss_time_series(results),
            _resource_chart(results),
            _eps_box_plot(results),
            _scale_ramp_up(results),
            _trend_chart(results),
        ] if s
    )

    has_snap = any(r.snapshots for r in results)
    has_scale = any(r.scale_data for r in results)
    has_trends = any(
        r.report and r.report.eps_slope is not None
        for r in results
    )

    body_parts = [
        '<h1>Eventum Test Report</h1>',
        f'<div class="timestamp">Generated: {ts}</div>',
        '<section><h2>Summary</h2>',
        _summary_cards(results),
        '</section>',
        '<section><h2>Test Results</h2>',
        _detail_table(results),
        '</section>',
        _chart_section('eps-chart', 'EPS Over Time', visible=has_snap),
        _chart_section(
            'rss-chart', 'RSS Memory Over Time', visible=has_snap,
        ),
        _chart_section(
            'resource-chart',
            'File Descriptors &amp; Threads',
            visible=has_snap,
        ),
        _chart_section(
            'eps-box-chart', 'EPS Distribution', visible=has_snap,
        ),
        _chart_section(
            'scale-chart', 'Scale Ramp-Up', visible=has_scale,
        ),
        _chart_section(
            'trend-chart', 'Trend Analysis', visible=has_trends,
        ),
        '<footer>Generated by Eventum Test Reporter</footer>',
    ]

    html = (
        '<!DOCTYPE html>\n<html lang="en">\n<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" '
        'content="width=device-width, initial-scale=1">\n'
        f'<title>Eventum Test Report \u2014 {ts}</title>\n'
        f'<script src="{PLOTLY_CDN}"></script>\n'
        f'<style>\n{_CSS}</style>\n'
        '</head>\n<body>\n'
        + '\n'.join(p for p in body_parts if p)
        + f'\n<script>\n{charts_js}\n</script>\n'
        '</body>\n</html>'
    )

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding='utf-8')
    print(  # noqa: T201
        f'\nTest report written to: {path.resolve()}',
    )
