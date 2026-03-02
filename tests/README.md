# Tests

Two categories: **integration** (output plugin correctness) and **performance** (input/event plugin throughput).

| Category        | Scope                                        | Marker        | Docker |
|-----------------|----------------------------------------------|---------------|--------|
| **Integration** | Output plugins against real backends         | `integration` | Yes    |
| **Performance** | Input and event plugin throughput (EPS)      | `performance` | No     |

## Quick Start

```bash
# Start backends (integration tests only)
docker compose -f tests/docker/docker-compose.yml up -d

# Run tests
uv run pytest tests/integration/ -m integration --no-cov -v
uv run pytest tests/performance/ -m performance --no-cov -vs

# Tear down
docker compose -f tests/docker/docker-compose.yml down -v
```

## Integration

Output plugins against real OpenSearch, ClickHouse, and Kafka. Data integrity (hash checks, sequence validation, duplicate detection), error handling, edge cases.

```bash
uv run pytest tests/integration/ -m integration --no-cov -v
uv run pytest tests/integration/test_opensearch.py -v --no-cov
uv run pytest tests/integration/test_clickhouse.py -v --no-cov
uv run pytest tests/integration/test_kafka.py -v --no-cov
```

## Performance

Pure CPU throughput benchmarks for input and event plugins.

```bash
# Input plugins (6 plugins x 3 batch sizes = 18 tests)
uv run pytest tests/performance/test_input_plugins.py -m performance --no-cov -vs

# Event plugins (3 plugins x 3 variants = 9 tests)
uv run pytest tests/performance/test_event_plugins.py -m performance --no-cov -vs
```

## Environment Variables

| Variable         | Default                 | Description         |
|------------------|-------------------------|---------------------|
| `OPENSEARCH_URL` | `http://localhost:9200` | OpenSearch endpoint |
| `CLICKHOUSE_HOST`| `localhost`             | ClickHouse hostname |
| `CLICKHOUSE_PORT`| `8123`                  | ClickHouse HTTP port|
| `KAFKA_BOOTSTRAP`| `localhost:9094`        | Kafka bootstrap     |

## Structure

```text
tests/
├── conftest.py                    # Report hooks + free-threaded Python compat
├── metrics.py                     # MetricsCollector, PerformanceReport, snapshots
├── docker/
│   ├── docker-compose.yml         # Local dev services
│   ├── docker-compose.ci.yml      # CI overlay (reduced resources)
│   └── clickhouse/
├── integration/
│   ├── conftest.py                # Service readiness + plugin fixtures
│   ├── backends/
│   │   ├── base.py                # BackendConsumer ABC
│   │   ├── opensearch.py
│   │   ├── clickhouse.py
│   │   └── kafka.py
│   ├── event_factory.py           # Verifiable ECS events
│   ├── verification.py            # Hash & sequence validation
│   ├── test_opensearch.py
│   ├── test_clickhouse.py
│   └── test_kafka.py
├── performance/
│   ├── conftest.py                # perf_result fixture
│   ├── _helpers.py                # PerfResult, templates, print_report
│   ├── test_input_plugins.py
│   └── test_event_plugins.py
└── reporting/
    ├── store.py                   # TestResult + ReportStore
    └── html.py                    # HTML report with Plotly charts
```

## HTML Report

Pass `--test-report=<path>` to generate an interactive HTML report with Plotly charts:

```bash
uv run pytest tests/ --no-cov -vs --test-report=/tmp/report.html
```

## Troubleshooting

**Services not ready** — fixtures wait 60s with retries. Check: `docker compose -f tests/docker/docker-compose.yml ps`

**Kafka not reachable** — KRaft mode, external listener on port 9094. Verify `KAFKA_BOOTSTRAP=localhost:9094`.

**Performance numbers vary** — hardware-dependent. No assertions on absolute values.
