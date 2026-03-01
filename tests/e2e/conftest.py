"""Fixtures and helpers for end-to-end tests.

E2E tests exercise the full ``eventum generate`` CLI via subprocess,
exactly as a user would run it. The subprocess writes events into real
backend services; backend consumers read them back for verification.
"""

import asyncio
import json
import os
import signal
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import pytest
import yaml

from tests.integration.backends.clickhouse import ClickHouseConsumer
from tests.integration.backends.kafka import KafkaConsumer
from tests.integration.backends.opensearch import OpenSearchConsumer
from tests.integration.conftest import (
    CLICKHOUSE_HOST,
    CLICKHOUSE_PORT,
    KAFKA_BOOTSTRAP,
    OPENSEARCH_URL,
    _check_clickhouse,
    _check_kafka,
    _check_opensearch,
    _wait_for_service,
)

PROJECT_ROOT = Path(__file__).parent.parent.parent
GENERATORS_DIR = Path(__file__).parent.parent / 'scale' / 'generators'


@dataclass
class GenerateResult:
    """Result of running ``eventum generate`` as a subprocess."""

    returncode: int
    stdout: str
    stderr: str


async def run_eventum_generate(
    config_path: Path,
    gen_id: str,
    params: dict,
    *,
    timeout: float = 120,
    extra_args: list[str] | None = None,
    env_override: dict[str, str] | None = None,
) -> GenerateResult:
    """Run ``eventum generate`` as an async subprocess.

    Parameters
    ----------
    config_path : Path
        Path to the generator YAML config (resolved to absolute).
    gen_id : str
        Generator ID passed via ``--id``.
    params : dict
        Parameters serialized as JSON for ``--params``.
    timeout : float
        Maximum seconds to wait for the subprocess.
    extra_args : list[str] | None
        Additional CLI arguments appended to the command.
    env_override : dict[str, str] | None
        Extra environment variables merged into the subprocess env.

    Returns
    -------
    GenerateResult
        Subprocess exit code, stdout, and stderr.

    Raises
    ------
    asyncio.TimeoutError
        If the subprocess does not finish within *timeout*.

    """
    cmd = [
        'uv', 'run', 'eventum', 'generate',
        '--id', gen_id,
        '--path', str(config_path.resolve()),
        '--live-mode', 'false',
        '--params', json.dumps(params),
        '-vvvv',
    ]
    if extra_args:
        cmd.extend(extra_args)

    env = {**os.environ}
    if env_override:
        env.update(env_override)

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
        cwd=str(PROJECT_ROOT),
    )
    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(), timeout=timeout,
        )
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise

    assert proc.returncode is not None
    return GenerateResult(
        returncode=proc.returncode,
        stdout=stdout_bytes.decode() if stdout_bytes else '',
        stderr=stderr_bytes.decode() if stderr_bytes else '',
    )


async def run_eventum_with_signal(
    config_path: Path,
    gen_id: str,
    params: dict,
    *,
    signal_num: int = signal.SIGTERM,
    signal_delay: float = 2.0,
    timeout: float = 30,
    env_override: dict[str, str] | None = None,
) -> GenerateResult:
    """Run ``eventum generate`` and send a signal after a delay.

    Launches the subprocess, waits *signal_delay* seconds, sends
    *signal_num*, then waits for the process to exit.

    Parameters
    ----------
    signal_num : int
        Signal number (default ``SIGTERM``).
    signal_delay : float
        Seconds to wait before sending the signal.
    timeout : float
        Maximum seconds to wait after sending the signal.

    """
    cmd = [
        'uv', 'run', 'eventum', 'generate',
        '--id', gen_id,
        '--path', str(config_path.resolve()),
        '--live-mode', 'false',
        '--params', json.dumps(params),
        '-vvvv',
    ]

    env = {**os.environ}
    if env_override:
        env.update(env_override)

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
        cwd=str(PROJECT_ROOT),
    )

    await asyncio.sleep(signal_delay)
    proc.send_signal(signal_num)

    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(), timeout=timeout,
        )
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise

    assert proc.returncode is not None
    return GenerateResult(
        returncode=proc.returncode,
        stdout=stdout_bytes.decode() if stdout_bytes else '',
        stderr=stderr_bytes.decode() if stderr_bytes else '',
    )


async def run_eventum_raw(
    args: list[str],
    *,
    timeout: float = 30,
) -> GenerateResult:
    """Run ``uv run eventum`` with arbitrary arguments.

    Used by CLI tests that need to pass malformed or incomplete options.
    """
    cmd = ['uv', 'run', 'eventum', *args]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=str(PROJECT_ROOT),
    )
    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(), timeout=timeout,
        )
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise

    assert proc.returncode is not None
    return GenerateResult(
        returncode=proc.returncode,
        stdout=stdout_bytes.decode() if stdout_bytes else '',
        stderr=stderr_bytes.decode() if stderr_bytes else '',
    )


# -- Service readiness fixtures (session-scoped) --


@pytest.fixture(scope='session')
def _ensure_opensearch():
    """Block until OpenSearch is reachable."""
    _wait_for_service(_check_opensearch, 'OpenSearch')


@pytest.fixture(scope='session')
def _ensure_clickhouse():
    """Block until ClickHouse is reachable."""
    _wait_for_service(_check_clickhouse, 'ClickHouse')


@pytest.fixture(scope='session')
def _ensure_kafka():
    """Block until Kafka is reachable."""
    _wait_for_service(_check_kafka, 'Kafka')


# -- Consumer fixtures --


@pytest.fixture()
def opensearch_consumer(_ensure_opensearch):
    """Create an OpenSearchConsumer with a unique ephemeral index."""
    return OpenSearchConsumer(
        base_url=OPENSEARCH_URL,
        username='admin',
        password='admin',
    )


@pytest.fixture()
def clickhouse_consumer(_ensure_clickhouse):
    """Create a ClickHouseConsumer with a unique ephemeral table."""
    return ClickHouseConsumer(
        host=CLICKHOUSE_HOST,
        port=CLICKHOUSE_PORT,
    )


@pytest.fixture()
def kafka_consumer(_ensure_kafka):
    """Create a KafkaConsumer with a unique ephemeral topic."""
    return KafkaConsumer(
        bootstrap_servers=KAFKA_BOOTSTRAP,
    )


# -- Shared helpers --


@pytest.fixture()
def batch_id():
    """Generate a unique batch ID for test event tracking."""
    return uuid4().hex


@pytest.fixture()
def gen_id():
    """Generate a unique generator ID."""
    return f'e2e_{uuid4().hex[:8]}'


@pytest.fixture()
def stdout_config(tmp_path):
    """Create a minimal generator config that outputs to stdout.

    Used by CLI tests that don't need external backend services.
    """
    script_path = GENERATORS_DIR / 'base' / 'produce_events.py'
    config = {
        'input': [{'static': {'count': '${params.event_count}'}}],
        'event': {'script': {'path': str(script_path.resolve())}},
        'output': [{'stdout': {'stream': 'stdout'}}],
    }
    config_path = tmp_path / 'generator.yml'
    with config_path.open('w') as f:
        yaml.dump(config, f)
    return config_path
