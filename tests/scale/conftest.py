"""Fixtures for scale tests."""

import os
from pathlib import Path

import pytest
import pytest_asyncio

from eventum.core.generator import Generator
from eventum.core.parameters import GeneratorParameters
from tests.integration.conftest import (
    CLICKHOUSE_HOST,
    CLICKHOUSE_PORT,
    KAFKA_BOOTSTRAP,
    OPENSEARCH_URL,
)

GENERATORS_DIR = Path(__file__).parent / 'generators'
DEFAULT_EVENT_COUNT = 50000


@pytest.fixture()
def generator_factory(tmp_path):
    """Factory for creating Generator instances with test YAML configs.

    Returns a callable that creates a Generator targeting a specific
    backend with given parameters.
    """

    def factory(
        backend: str,
        gen_id: str,
        event_count: int = DEFAULT_EVENT_COUNT,
        extra_params: dict | None = None,
    ) -> Generator:
        config_path = GENERATORS_DIR / backend / 'generator.yml'
        assert config_path.exists(), f'Config not found: {config_path}'

        params = {
            'event_count': str(event_count),
        }

        # Add backend-specific params
        if backend == 'opensearch':
            params.update({
                'opensearch_url': OPENSEARCH_URL,
                'index': f'eventum_scale_{gen_id}',
            })
        elif backend == 'clickhouse':
            params.update({
                'clickhouse_host': CLICKHOUSE_HOST,
                'clickhouse_port': str(CLICKHOUSE_PORT),
                'database': 'eventum_test',
                'table': f'eventum_scale_{gen_id}',
            })
        elif backend == 'kafka':
            params.update({
                'kafka_bootstrap': KAFKA_BOOTSTRAP,
                'topic': f'eventum_scale_{gen_id}',
            })
        elif backend == 'tcp':
            # TCP port must be provided via extra_params
            params.update({
                'tcp_host': '127.0.0.1',
                'tcp_port': '0',
            })

        if extra_params:
            params.update(extra_params)

        generator_params = GeneratorParameters(
            id=gen_id,
            path=config_path,
            live_mode=False,  # sample mode for deterministic count
            params=params,
        )

        return Generator(params=generator_params)

    return factory
