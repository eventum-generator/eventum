"""Event plugin production benchmarks.

Measures how fast each event plugin can produce events from timestamps.
Each test generates 5 million events at varying complexity levels.
Tests are pure CPU operations — no Docker backends required.

All tests are marked ``@pytest.mark.performance``.
"""

from __future__ import annotations

import textwrap
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest
from jinja2 import DictLoader

from eventum.plugins.event.plugins.replay.config import (
    ReplayEventPluginConfig,
)
from eventum.plugins.event.plugins.replay.plugin import ReplayEventPlugin
from eventum.plugins.event.plugins.script.config import (
    ScriptEventPluginConfig,
)
from eventum.plugins.event.plugins.script.plugin import ScriptEventPlugin
from eventum.plugins.event.plugins.template.config import (
    TemplateConfigForFSMMode,
    TemplateEventPluginConfig,
    TemplateEventPluginConfigForFSMMode,
    TemplatePickingMode,
    TemplateTransition,
)
from eventum.plugins.event.plugins.template.fsm.fields import Always, Ge
from eventum.plugins.event.plugins.template.plugin import TemplateEventPlugin
from tests.performance._helpers import (
    TEMPLATE_MINIMAL,
    TEMPLATE_TYPICAL,
    PerfResult,
    create_template_plugin,
    print_report,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EVENT_COUNT = 500_000

# FSM template sources — 3-state cycling machine with shared state.
# Cycle: a→a→a→b→c→a→... (counter increments in a, resets in c).
_FSM_TEMPLATE_A = """\
{%- set counter = shared.get('counter', 0) -%}
{%- do shared.set('counter', counter + 1) -%}
{%- set hosts = ['web-01','web-02','api-01','api-02','db-01','db-02','cache-01','queue-01'] -%}
{%- set categories = ['authentication','network','process','web','database'] -%}
{%- set actions = ['login','logout','query','update','delete','create','export','import','sync','backup'] -%}
{%- set severities = ['low','medium','high','critical'] -%}
{%- set protocols = ['tcp','udp','http','https','grpc','ws'] -%}
{
  "@timestamp": "{{ timestamp.isoformat() }}",
  "state": "a",
  "counter": {{ counter + 1 }},
  "event": {
    "category": "{{ categories | random }}",
    "kind": "event",
    "action": "{{ actions | random }}",
    "severity": "{{ severities | random }}",
    "sequence": {{ counter + 1 }}
  },
  "host": {"name": "{{ hosts | random }}", "uptime": {{ range(1000, 999999) | random }}},
  "source": {"ip": "10.{{ range(0,255) | random }}.{{ range(0,255) | random }}.{{ range(1,254) | random }}"},
  "destination": {"ip": "192.168.{{ range(0,255) | random }}.{{ range(1,254) | random }}", "port": {{ range(1024, 65535) | random }}},
  "network": {"protocol": "{{ protocols | random }}", "bytes": {{ range(64, 1048576) | random }}},
  "user": {"name": "user-{{ range(1000, 9999) | random }}", "domain": "{{ ['corp','lab','dev','staging'] | random }}.example.com"},
  "process": {"pid": {{ range(100, 65535) | random }}, "name": "{{ ['nginx','python','java','node','go'] | random }}"},
  "metrics": {
    "cpu": {{ range(0, 100) | random }},
    "memory": {{ range(0, 100) | random }},
    "disk_io": {{ range(0, 10000) | random }},
    "net_rx": {{ range(0, 1000000) | random }},
    "net_tx": {{ range(0, 1000000) | random }},
    "latency_ms": {{ range(1, 9999) | random }},
    "queue_depth": {{ range(0, 500) | random }},
    "thread_count": {{ range(1, 256) | random }},
    "open_files": {{ range(10, 10000) | random }},
    "gc_pause_ns": {{ range(1000, 9999999) | random }}
  },
  "tags": {{ ['benchmark','perf','test','synthetic','generated'] | tojson }},
  "message": "State A: iteration {{ counter + 1 }} on {{ hosts | random | upper }} via {{ protocols | random }} severity={{ severities | random | upper }} action={{ actions | random }} pid={{ range(100, 65535) | random }}"
}\
"""

_FSM_TEMPLATE_B = """\
{%- set total = shared.get('counter', 0) -%}
{%- set actions = ['process','analyze','aggregate','transform','enrich','correlate'] -%}
{%- set statuses = ['ok','warn','skip','error','timeout','retry'] -%}
{%- set regions = ['us-east-1','us-west-2','eu-west-1','ap-southeast-1'] -%}
{
  "@timestamp": "{{ timestamp.isoformat() }}",
  "state": "b",
  "action": "{{ actions | random }}",
  "summary": {
    "total_steps": {{ total }},
    "status": "{{ statuses | random }}",
    "region": "{{ regions | random }}",
    "duration_ms": {{ range(1, 9999) | random }},
    "throughput": {{ range(100, 999999) | random }},
    "error_rate": {{ range(0, 100) | random }}
  },
  "host": {"name": "aggregator-{{ range(1, 10) | random }}", "az": "{{ regions | random }}-{{ ['a','b','c'] | random }}"},
  "source": {"ip": "172.{{ range(16,31) | random }}.{{ range(0,255) | random }}.{{ range(1,254) | random }}"},
  "http": {
    "method": "{{ ['GET','POST','PUT','DELETE','PATCH'] | random }}",
    "status_code": {{ [200,201,204,301,400,401,403,404,500,502,503] | random }},
    "url": "/api/v{{ range(1,4) | random }}/{{ ['users','orders','products','settings','metrics'] | random }}/{{ range(1, 99999) | random }}"
  },
  "tags": {{ (['aggregation', statuses | random, regions | random]) | tojson }},
  "message": "State B: {{ actions | random | upper }} total={{ total }} status={{ statuses | random }} region={{ regions | random }} throughput={{ range(100, 999999) | random }} method={{ ['GET','POST','PUT'] | random }}"
}\
"""

_FSM_TEMPLATE_C = """\
{%- set counter = shared.get('counter', 0) -%}
{%- do shared.clear() -%}
{%- set ops = ['reset','gc','checkpoint','flush','compact','rebalance'] -%}
{%- set outcomes = ['success','partial','deferred'] -%}
{
  "@timestamp": "{{ timestamp.isoformat() }}",
  "state": "c",
  "action": "reset",
  "previous_counter": {{ counter }},
  "cleanup": {
    "operation": "{{ ops | random }}",
    "outcome": "{{ outcomes | random }}",
    "freed_bytes": {{ range(1024, 10485760) | random }},
    "duration_us": {{ range(10, 999999) | random }},
    "gc_gen": {{ range(0, 3) | random }}
  },
  "host": {"name": "controller-{{ range(1, 5) | random }}", "cpu": {{ range(0, 100) | random }}},
  "tags": {{ ['reset','cycle_complete', ops | random, outcomes | random] | tojson }},
  "message": "State C: cycle complete after {{ counter }} iterations op={{ ops | random | upper }} outcome={{ outcomes | random }} freed={{ range(1024, 10485760) | random }} gc_gen={{ range(0, 3) | random }}"
}\
"""


# ---------------------------------------------------------------------------
# Shared benchmark runner
# ---------------------------------------------------------------------------


def _run_event_benchmark(
    plugin: object,
    perf_result: PerfResult,
    label: str,
    *,
    plugin_name: str,
    variant: str,
) -> None:
    """Run a fixed-count event plugin benchmark."""
    params = {'timestamp': datetime.now(UTC), 'tags': ()}

    total = 0
    start = time.monotonic()
    while total < EVENT_COUNT:
        total += len(plugin.produce(params=params))
    duration = time.monotonic() - start

    perf_result.duration_seconds = duration
    perf_result.total_events = total
    perf_result.metadata = {'plugin': plugin_name, 'variant': variant}

    print_report(label, perf_result)
    assert total > 0


# ---------------------------------------------------------------------------
# Script fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def script_minimal_path(tmp_path: Path) -> Path:
    """Create a minimal script — f-string, no imports."""
    p = tmp_path / 'produce.py'
    p.write_text(
        textwrap.dedent("""\
            def produce(params):
                return f'{{"@timestamp": "{params["timestamp"].isoformat()}"}}'
        """),
    )
    return p


@pytest.fixture
def script_typical_path(tmp_path: Path) -> Path:
    """Create a typical script — json.dumps, several fields."""
    p = tmp_path / 'produce.py'
    p.write_text(
        textwrap.dedent("""\
            import json

            def produce(params):
                return json.dumps({
                    "@timestamp": params["timestamp"].isoformat(),
                    "event": {"kind": "event", "module": "benchmark"},
                    "host": {"name": "bench-host-01"},
                    "message": "benchmark event",
                })
        """),
    )
    return p


@pytest.fixture
def script_complex_path(tmp_path: Path) -> Path:
    """Create a complex script — heavy computation, 1 event per call."""
    p = tmp_path / 'produce.py'
    p.write_text(
        textwrap.dedent("""\
            import hashlib
            import json
            import random

            HOSTS = [f"node-{i:03d}" for i in range(50)]
            ACTIONS = ["login", "logout", "query", "update", "delete",
                       "create", "export", "import", "sync", "backup"]

            def produce(params):
                ts = params["timestamp"].isoformat()
                session = hashlib.md5(ts.encode()).hexdigest()
                metrics = {f"metric_{j}": random.random() * 1000 for j in range(20)}
                tags = random.sample(ACTIONS, k=3)
                return json.dumps({
                    "@timestamp": ts,
                    "event": {
                        "kind": "event",
                        "category": random.choice(ACTIONS),
                    },
                    "host": {"name": random.choice(HOSTS)},
                    "session": {"id": session},
                    "source": {"ip": f"10.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"},
                    "user": {"name": f"user-{random.randint(1000,9999)}"},
                    "metrics": metrics,
                    "tags": tags,
                    "message": f"session={session[:8]} "
                               f"host={random.choice(HOSTS)} "
                               f"action={','.join(tags)}",
                })
        """),
    )
    return p


# ---------------------------------------------------------------------------
# Replay fixtures
# ---------------------------------------------------------------------------

_REPLAY_LINE_COUNT = 10_000


@pytest.fixture
def replay_plain_path(tmp_path: Path) -> Path:
    """Create a 10K-line log file with no timestamps."""
    p = tmp_path / 'plain.log'
    lines = [
        f'INFO [test.module] Request {i} processed successfully'
        for i in range(_REPLAY_LINE_COUNT)
    ]
    p.write_text('\n'.join(lines))
    return p


@pytest.fixture
def replay_regex_path(tmp_path: Path) -> Path:
    """Create a 10K-line log file with ISO timestamps."""
    p = tmp_path / 'access.log'
    lines = [
        f'2024-01-15T12:00:{i % 60:02d}.000Z INFO '
        f'[test.module] Request {i} processed successfully'
        for i in range(_REPLAY_LINE_COUNT)
    ]
    p.write_text('\n'.join(lines))
    return p


@pytest.fixture
def replay_formatted_path(tmp_path: Path) -> Path:
    """Create a 10K-line log file with ~500-char lines and timestamps."""
    p = tmp_path / 'verbose.log'
    padding = 'x' * 400
    lines = [
        f'2024-01-15T12:00:{i % 60:02d}.000Z INFO '
        f'[test.module] Request {i} {padding}'
        for i in range(_REPLAY_LINE_COUNT)
    ]
    p.write_text('\n'.join(lines))
    return p


# ---------------------------------------------------------------------------
# Template plugin tests
# ---------------------------------------------------------------------------


@pytest.mark.performance
def test_template_minimal(
    perf_result: PerfResult,
) -> None:
    """Measure bare Jinja2 rendering overhead."""
    plugin = create_template_plugin(templates={'event': TEMPLATE_MINIMAL})
    _run_event_benchmark(
        plugin,
        perf_result,
        'Template: minimal',
        plugin_name='template',
        variant='minimal',
    )


@pytest.mark.performance
def test_template_typical(
    perf_result: PerfResult,
) -> None:
    """Measure realistic ECS-like template rendering."""
    plugin = create_template_plugin(templates={'event': TEMPLATE_TYPICAL})
    _run_event_benchmark(
        plugin,
        perf_result,
        'Template: typical',
        plugin_name='template',
        variant='typical',
    )


@pytest.mark.performance
def test_template_complex(
    perf_result: PerfResult,
) -> None:
    """Measure FSM mode: 3 templates, shared state transitions."""
    loader = DictLoader(
        {
            'a.jinja': _FSM_TEMPLATE_A,
            'b.jinja': _FSM_TEMPLATE_B,
            'c.jinja': _FSM_TEMPLATE_C,
        }
    )
    config = TemplateEventPluginConfig(
        root=TemplateEventPluginConfigForFSMMode(
            params={},
            samples={},
            mode=TemplatePickingMode.FSM,
            templates=[
                {
                    'state_a': TemplateConfigForFSMMode(
                        template=Path('a.jinja'),
                        initial=True,
                        transitions=[
                            TemplateTransition(
                                to='state_b',
                                when=Ge(ge={'shared.counter': 3}),
                            ),
                        ],
                    )
                },
                {
                    'state_b': TemplateConfigForFSMMode(
                        template=Path('b.jinja'),
                        transitions=[
                            TemplateTransition(
                                to='state_c',
                                when=Always(always=None),
                            ),
                        ],
                    )
                },
                {
                    'state_c': TemplateConfigForFSMMode(
                        template=Path('c.jinja'),
                        transitions=[
                            TemplateTransition(
                                to='state_a',
                                when=Always(always=None),
                            ),
                        ],
                    )
                },
            ],
        ),
    )
    plugin = TemplateEventPlugin(
        config=config,
        params={'id': 1, 'templates_loader': loader},
    )
    _run_event_benchmark(
        plugin,
        perf_result,
        'Template: complex (FSM, shared state)',
        plugin_name='template',
        variant='complex',
    )


# ---------------------------------------------------------------------------
# Script plugin tests
# ---------------------------------------------------------------------------


@pytest.mark.performance
def test_script_minimal(
    perf_result: PerfResult,
    script_minimal_path: Path,
) -> None:
    """Measure script plugin: bare f-string return."""
    plugin = ScriptEventPlugin(
        config=ScriptEventPluginConfig(path=script_minimal_path.name),
        params={'id': 1, 'base_path': script_minimal_path.parent},
    )
    _run_event_benchmark(
        plugin,
        perf_result,
        'Script: minimal',
        plugin_name='script',
        variant='minimal',
    )


@pytest.mark.performance
def test_script_typical(
    perf_result: PerfResult,
    script_typical_path: Path,
) -> None:
    """Measure script plugin: json.dumps with several fields."""
    plugin = ScriptEventPlugin(
        config=ScriptEventPluginConfig(path=script_typical_path.name),
        params={'id': 1, 'base_path': script_typical_path.parent},
    )
    _run_event_benchmark(
        plugin,
        perf_result,
        'Script: typical',
        plugin_name='script',
        variant='typical',
    )


@pytest.mark.performance
def test_script_complex(
    perf_result: PerfResult,
    script_complex_path: Path,
) -> None:
    """Measure script plugin: heavy computation per call."""
    plugin = ScriptEventPlugin(
        config=ScriptEventPluginConfig(path=script_complex_path.name),
        params={'id': 1, 'base_path': script_complex_path.parent},
    )
    _run_event_benchmark(
        plugin,
        perf_result,
        'Script: complex',
        plugin_name='script',
        variant='complex',
    )


# ---------------------------------------------------------------------------
# Replay plugin tests
# ---------------------------------------------------------------------------


@pytest.mark.performance
def test_replay_plain(
    perf_result: PerfResult,
    replay_plain_path: Path,
) -> None:
    """Measure replay plugin: raw file read, no timestamp substitution."""
    plugin = ReplayEventPlugin(
        config=ReplayEventPluginConfig(
            path=replay_plain_path.name,
            repeat=True,
        ),
        params={'id': 1, 'base_path': replay_plain_path.parent},
    )
    _run_event_benchmark(
        plugin,
        perf_result,
        'Replay: plain',
        plugin_name='replay',
        variant='plain',
    )


@pytest.mark.performance
def test_replay_regex(
    perf_result: PerfResult,
    replay_regex_path: Path,
) -> None:
    """Measure replay plugin: timestamp regex substitution."""
    plugin = ReplayEventPlugin(
        config=ReplayEventPluginConfig(
            path=replay_regex_path.name,
            timestamp_pattern=r'(?P<timestamp>\d{4}-\d{2}-\d{2}T[\d:.]+Z)',
            repeat=True,
        ),
        params={'id': 1, 'base_path': replay_regex_path.parent},
    )
    _run_event_benchmark(
        plugin,
        perf_result,
        'Replay: regex',
        plugin_name='replay',
        variant='regex',
    )


@pytest.mark.performance
def test_replay_formatted(
    perf_result: PerfResult,
    replay_formatted_path: Path,
) -> None:
    """Measure replay plugin: regex + custom strftime + long lines."""
    plugin = ReplayEventPlugin(
        config=ReplayEventPluginConfig(
            path=replay_formatted_path.name,
            timestamp_pattern=r'(?P<timestamp>\d{4}-\d{2}-\d{2}T[\d:.]+Z)',
            timestamp_format='%Y-%m-%d %H:%M:%S',
            repeat=True,
        ),
        params={'id': 1, 'base_path': replay_formatted_path.parent},
    )
    _run_event_benchmark(
        plugin,
        perf_result,
        'Replay: formatted',
        plugin_name='replay',
        variant='formatted',
    )
