"""CLI behavior tests for ``eventum generate``.

These tests exercise exit codes, signal handling, verbose output, and
error paths of the CLI itself. Most do NOT require Docker services —
they use a minimal stdout-based generator config.
"""

import pytest

from tests.e2e.conftest import (
    run_eventum_generate,
    run_eventum_raw,
)

pytestmark = [pytest.mark.e2e, pytest.mark.asyncio]


async def test_exit_code_success(stdout_config, gen_id, batch_id):
    """Valid config produces exit code 0."""
    result = await run_eventum_generate(
        config_path=stdout_config,
        gen_id=gen_id,
        params={'event_count': '10'},
        env_override={'EVENTUM_TEST_BATCH_ID': batch_id},
    )

    assert result.returncode == 0, (
        f'Expected exit code 0, got {result.returncode}:\n'
        f'{result.stderr[-2000:]}'
    )


async def test_exit_code_nonexistent_path(gen_id):
    """Non-existent config path causes exit code 1 (start failure)."""
    result = await run_eventum_raw(
        [
            'generate',
            '--id', gen_id,
            '--path', '/tmp/nonexistent_eventum_config_12345.yml',
            '--live-mode', 'false',
            '--params', '{"event_count": "10"}',
        ],
        timeout=30,
    )

    assert result.returncode != 0, (
        'Expected non-zero exit code for non-existent config'
    )


async def test_exit_code_invalid_yaml(tmp_path, gen_id):
    """Malformed YAML in config causes exit code 1."""
    bad_config = tmp_path / 'bad.yml'
    bad_config.write_text(': invalid: yaml: {{{}\nnot valid at all!')

    result = await run_eventum_raw(
        [
            'generate',
            '--id', gen_id,
            '--path', str(bad_config),
            '--live-mode', 'false',
            '--params', '{"event_count": "10"}',
        ],
        timeout=30,
    )

    assert result.returncode != 0, (
        'Expected non-zero exit code for invalid YAML'
    )


async def test_exit_code_missing_required_option():
    """Missing --id causes validation error (exit code 1).

    The ``from_model`` decorator passes all options to Pydantic for
    validation, so missing ``--id`` is caught by the model validator
    (exit 1) rather than Click's own required-option check (exit 2).
    """
    result = await run_eventum_raw(
        [
            'generate',
            '--path', '/tmp/dummy.yml',
            '--live-mode', 'false',
        ],
        timeout=30,
    )

    assert result.returncode == 1, (
        f'Expected exit code 1 (validation error), got {result.returncode}'
    )
    assert 'failed to validate' in result.stdout.lower(), (
        'Expected validation error message in stdout'
    )


async def test_exit_code_unknown_command():
    """Unknown subcommand causes Click error (exit code 2)."""
    result = await run_eventum_raw(
        ['nonexistent-subcommand'],
        timeout=30,
    )

    assert result.returncode == 2, (
        f'Expected exit code 2 (Click error), got {result.returncode}'
    )


async def test_verbose_output(stdout_config, gen_id, batch_id):
    """Running with -vvvv produces structured log lines on stderr."""
    result = await run_eventum_generate(
        config_path=stdout_config,
        gen_id=gen_id,
        params={'event_count': '10'},
        env_override={'EVENTUM_TEST_BATCH_ID': batch_id},
    )

    assert result.returncode == 0

    # With -vvvv (INFO level), stderr should contain log output
    assert len(result.stderr) > 0, (
        'Expected log output on stderr with -vvvv'
    )
    # Structured logs from structlog should contain the generator ID
    # or common log keywords
    stderr_lower = result.stderr.lower()
    assert any(
        keyword in stderr_lower
        for keyword in ['starting', 'generator', 'info', 'event']
    ), (
        f'stderr does not contain expected log keywords:\n'
        f'{result.stderr[:1000]}'
    )
