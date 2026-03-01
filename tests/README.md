# Integration, Performance, Longevity, Scale & E2E Tests

Test suite for Eventum. Tests verify that events flow correctly through the full application and each output plugin into real backend services, measuring throughput, data integrity, and resource stability over time.

## Overview

| Category        | Purpose                                          | Marker         | Duration     |
|-----------------|--------------------------------------------------|----------------|--------------|
| **Integration** | Data integrity, error recovery, edge cases        | `integration`  | ~5 min       |
| **Performance** | Throughput benchmarks (EPS) across batch/event sizes | `performance` | ~10 min      |
| **Longevity**   | Soak tests — sustained writes checking for leaks  | `longevity`    | 2–10 min     |
| **Scale**       | Full generator pipeline pushing high event counts  | `scale`        | ~10 min      |
| **E2E**         | Full app via `eventum generate` CLI subprocess     | `e2e`          | ~5 min       |

Supported backends: **OpenSearch**, **ClickHouse**, **Kafka**, **TCP**.

## Architecture

### Event Verification Pipeline

Every test event carries embedded metadata for end-to-end verification:

```
EventFactory  →  Output Plugin  →  Backend  →  BackendConsumer  →  EventVerifier
```

1. **EventFactory** creates ECS-compliant JSON events with a `_test` field containing `batch_id`, `sequence_id`, and a SHA-256 `content_hash` of the payload (computed before the `_test` field is added).
2. Events are written through the actual output plugin to a real backend service.
3. **BackendConsumer** (one per backend) reads events back from the service.
4. **EventVerifier** compares received events against expectations: hash integrity, duplicate detection, missing sequence IDs, and ordering.

### Key Components

- **`EventFactory`** (`integration/event_factory.py`) — Generates verifiable events in four size categories: SMALL (~200B), MEDIUM (~2KB), LARGE (~50KB), HUGE (~1MB+).
- **`EventVerifier`** (`integration/verification.py`) — Validates consumed events: content hash verification, duplicate/missing detection, ordering checks. Returns a `VerificationResult`.
- **`BackendConsumer`** (`integration/backends/base.py`) — Abstract base with `setup()`, `teardown()`, `consume_all()`, `count()`, and `wait_for_count()`. Concrete implementations for each backend.
- **`MetricsCollector`** (`integration/metrics.py`) — Collects periodic snapshots of EPS, RSS, file descriptors, threads, and GC activity. Produces a `PerformanceReport` with percentile stats and linear-regression trend analysis.
- **Assertion helpers** (`integration/assertions.py`) — `assert_no_throughput_degradation()`, `assert_no_memory_leak()`, `assert_no_fd_leak()`, `assert_threads_stable()`.

## Prerequisites

- **Docker** (or Docker Desktop) with Compose v2
- **Python 3.14+**
- **uv** package manager

## Quick Start

```bash
# 1. Start backend services
docker compose -f tests/docker/docker-compose.yml up -d

# 2. Wait for services to be healthy
docker compose -f tests/docker/docker-compose.yml ps

# 3. Run tests (pick a category)
uv run pytest tests/integration/ -m integration --no-cov -v

# 4. Tear down
docker compose -f tests/docker/docker-compose.yml down -v
```

## Running Tests

### Integration tests (all backends)

```bash
uv run pytest tests/integration/ -m integration --no-cov -v
```

### Integration tests (single backend)

```bash
uv run pytest tests/integration/plugins/test_opensearch_integration.py -v --no-cov
uv run pytest tests/integration/plugins/test_clickhouse_integration.py -v --no-cov
uv run pytest tests/integration/plugins/test_kafka_integration.py -v --no-cov
uv run pytest tests/integration/plugins/test_tcp_integration.py -v --no-cov
```

### Performance tests

Measures sustained write throughput across batch sizes (1, 10, 100, 1000) and event sizes (SMALL, MEDIUM, LARGE), plus concurrent writer benchmarks.

```bash
uv run pytest tests/performance/ -m performance --no-cov -vs
```

Per backend:

```bash
uv run pytest tests/performance/test_throughput.py -m performance --no-cov -vs -k opensearch
```

### Longevity tests

Runs continuous writes for a configurable duration (default 120s). Checks for throughput degradation, memory leaks, FD leaks, thread growth, and data integrity over time.

```bash
uv run pytest tests/longevity/ -m longevity --no-cov -vs
```

Extended run (10 minutes):

```bash
EVENTUM_LONGEVITY_DURATION=600 uv run pytest tests/longevity/ -m longevity --no-cov -vs
```

### Scale tests

Runs full generator pipelines (YAML config + script plugin) pushing high event counts through each backend.

```bash
uv run pytest tests/scale/ -m scale --no-cov -vs
```

### E2E tests

Exercises the full `eventum generate` CLI as a subprocess — exactly as a user would run it. Events flow through the complete Input → Event → Output pipeline and are verified in real backend services.

```bash
uv run pytest tests/e2e/ -m e2e --no-cov -vs
```

Per backend:

```bash
uv run pytest tests/e2e/test_opensearch.py -m e2e --no-cov -vs
uv run pytest tests/e2e/test_clickhouse.py -m e2e --no-cov -vs
uv run pytest tests/e2e/test_kafka.py -m e2e --no-cov -vs
```

CLI-only tests (no Docker needed):

```bash
uv run pytest tests/e2e/test_cli.py -m e2e --no-cov -vs
```

## Environment Variables

| Variable                      | Default              | Description                                |
|-------------------------------|----------------------|--------------------------------------------|
| `OPENSEARCH_URL`              | `http://localhost:9200` | OpenSearch endpoint                     |
| `CLICKHOUSE_HOST`             | `localhost`          | ClickHouse hostname                        |
| `CLICKHOUSE_PORT`             | `8123`               | ClickHouse HTTP port                       |
| `KAFKA_BOOTSTRAP`             | `localhost:9094`     | Kafka bootstrap servers (external listener)|
| `EVENTUM_LONGEVITY_DURATION`  | `120`                | Longevity test duration in seconds         |
| `EVENTUM_TEST_BATCH_ID`       | *(auto-generated)*   | Override batch ID for debugging            |

## Directory Structure

```
tests/
├── docker/
│   ├── docker-compose.yml          # Local development services
│   ├── docker-compose.ci.yml       # CI-specific overrides
│   └── clickhouse/
│       └── init.sql                # ClickHouse schema bootstrap
├── integration/
│   ├── conftest.py                 # Shared fixtures (service readiness, factories)
│   ├── event_factory.py            # EventFactory — verifiable ECS event generation
│   ├── verification.py             # EventVerifier — hash & sequence validation
│   ├── metrics.py                  # MetricsCollector — EPS, RSS, FD, thread snapshots
│   ├── assertions.py               # Statistical assertion helpers
│   ├── backends/
│   │   ├── base.py                 # BackendConsumer ABC
│   │   ├── opensearch.py           # OpenSearchConsumer
│   │   ├── clickhouse.py           # ClickHouseConsumer
│   │   ├── kafka.py                # KafkaConsumer
│   │   └── tcp.py                  # TcpConsumer (in-process TCP server)
│   └── plugins/
│       ├── conftest.py             # Plugin-specific fixtures
│       ├── test_opensearch_integration.py
│       ├── test_clickhouse_integration.py
│       ├── test_kafka_integration.py
│       └── test_tcp_integration.py
├── performance/
│   ├── conftest.py
│   └── test_throughput.py          # Throughput benchmarks (batch size x event size matrix)
├── longevity/
│   ├── conftest.py
│   └── test_longevity.py           # Soak tests: sustained throughput, integrity, FD cycles
├── e2e/
│   ├── conftest.py                 # Subprocess runner, consumer fixtures
│   ├── test_opensearch.py          # OpenSearch e2e (6 tests)
│   ├── test_clickhouse.py          # ClickHouse e2e (6 tests)
│   ├── test_kafka.py               # Kafka e2e (6 tests)
│   └── test_cli.py                 # CLI behavior (5 tests)
└── scale/
    ├── conftest.py                 # Generator factory fixture
    └── generators/
        ├── base/
        │   └── produce_events.py   # Shared script plugin for scale & e2e tests
        ├── opensearch/
        │   └── generator.yml
        ├── clickhouse/
        │   └── generator.yml
        ├── kafka/
        │   └── generator.yml
        └── tcp/
            └── generator.yml
```

## Writing New Tests

### Adding a new backend

1. Create `tests/integration/backends/mybackend.py` implementing `BackendConsumer`:
   ```python
   from tests.integration.backends.base import BackendConsumer

   class MyBackendConsumer(BackendConsumer):
       async def setup(self) -> None: ...
       async def teardown(self) -> None: ...
       async def consume_all(self, timeout: float = 10.0) -> list[str]: ...
       async def count(self) -> int: ...
   ```

2. Create `tests/integration/plugins/test_mybackend_integration.py` with `pytestmark = pytest.mark.integration`.

3. Add the backend to the CI matrix in `.github/workflows/integration-tests.yml`.

4. Add a service definition to `tests/docker/docker-compose.yml`.

5. Add throughput tests in `tests/performance/test_throughput.py` and longevity tests in `tests/longevity/test_longevity.py`.

### Adding new test scenarios

Use `EventFactory` and `EventVerifier` for data integrity tests:

```python
async def test_my_scenario(event_factory):
    consumer = MyBackendConsumer(...)
    await consumer.setup()

    plugin = MyOutputPlugin(config=..., params={'id': 1})
    await plugin.open()

    try:
        batch = event_factory.create_batch(100, EventSize.MEDIUM)
        await plugin.write([e.raw_json for e in batch])

        await consumer.wait_for_count(100, timeout=30)
        events = await consumer.consume_all()

        verifier = EventVerifier(event_factory.batch_id, 100)
        result = verifier.verify(events)
        assert result.is_perfect, result.summary()
    finally:
        await plugin.close()
        await consumer.teardown()
```

### Using MetricsCollector

For performance-oriented tests:

```python
async def test_my_perf_scenario(metrics_collector):
    metrics_collector.start()

    for _ in range(iterations):
        written = await plugin.write(batch)
        metrics_collector.record_events(written)

    report = metrics_collector.finalize()

    assert_no_throughput_degradation(report)
    assert_no_memory_leak(report)
    assert_no_fd_leak(report)
```

The collector handles warmup exclusion (first 5s by default), periodic snapshots, and produces a `PerformanceReport` with EPS percentiles (p50/p95/p99), RSS tracking, FD/thread counts, GC stats, and linear-regression trend analysis.

## CI

The GitHub Actions workflow (`.github/workflows/integration-tests.yml`) runs on:

- **Push** to `master`/`develop` (when output plugin, core, or test files change)
- **Pull requests** to `master`
- **Nightly schedule** (3 AM UTC) with extended longevity duration (600s)
- **Manual dispatch** with configurable longevity duration and scale toggle

### Job pipeline

```
integration (4x matrix)  →  performance (4x matrix)
                          →  longevity (4x matrix)
                          →  scale (single job)
```

Performance, longevity, and scale jobs run in parallel after integration passes. Each matrix entry runs against its own set of service containers. All jobs upload JUnit XML reports as artifacts (retained 30 days).

**Note:** All service containers (OpenSearch, ClickHouse, Kafka) start for every matrix job, including TCP. TCP tests use an in-process server and ignore the external services. The idle containers are harmless overhead.

## Troubleshooting

### Services not ready

The test fixtures wait up to 60 seconds for each service with automatic retries. If services still fail to start:

```bash
# Check service health
docker compose -f tests/docker/docker-compose.yml ps
docker compose -f tests/docker/docker-compose.yml logs opensearch

# Restart a specific service
docker compose -f tests/docker/docker-compose.yml restart kafka
```

### Kafka not reachable

Kafka uses KRaft mode (no ZooKeeper) with two listeners: `PLAINTEXT` for internal and `EXTERNAL` on port 9094 for host access. If tests cannot connect:

- Verify `KAFKA_BOOTSTRAP` points to `localhost:9094` (not 9092)
- Check that the external listener is advertised correctly in docker-compose
- Kafka may take 30+ seconds to elect a controller on first start

### Timeouts on `wait_for_count`

If tests fail with `TimeoutError` from `BackendConsumer.wait_for_count()`:

- Increase the timeout parameter in the test
- Check that the backend service is healthy and not under memory pressure
- For OpenSearch, the default refresh interval is 1 second — freshly written documents may not be immediately searchable

### Performance numbers vary between runs

Throughput benchmarks use soft thresholds (warnings, not failures) because EPS depends on hardware. The hard assertions only check for throughput *degradation* over time (declining slope) and resource leaks, not absolute EPS values.

### Longevity tests fail on CI

The default duration is 120 seconds. Nightly runs use 600 seconds. If a longevity test fails:

- Check the printed report for which assertion failed (throughput slope, RSS growth, FD count, thread count)
- Memory growth under 50 MB and RSS slope under 1 MB/min are the default thresholds
- FD growth must stay under 10 over the full run; thread growth under 5
