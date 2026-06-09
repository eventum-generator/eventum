"""Tests for MCP error scrubbing and translation."""

from pathlib import Path

from eventum.core.config_loader import ConfigurationLoadError
from eventum.mcp.errors import (
    ToolFailure,
    scrub_context,
    scrub_log_line,
    scrub_message,
    to_tool_error,
)


def test_scrub_relativizes_paths_and_allowlists(tmp_path: Path) -> None:
    """file_path relativized; reason forwarded verbatim if no redact_values."""
    gens = tmp_path / 'generators'
    token = 'sup3r-secret-value'  # noqa: S105
    err = ConfigurationLoadError(
        'Invalid configuration',
        context={
            'file_path': str(gens / 'g' / 'generator.yml'),
            'reason': f'field "password": {token!r} - invalid',
        },
    )
    failure = to_tool_error(err, generators_dir=gens)

    assert isinstance(failure, ToolFailure)
    assert failure.error == 'Invalid configuration'
    assert str(gens) not in repr(failure.details)
    assert failure.details.get('file_path') == 'g/generator.yml'
    assert token in failure.details['reason']


def test_scrub_drops_unknown_keys(tmp_path: Path) -> None:
    """Keys not in the allow-list are dropped."""
    err = ConfigurationLoadError(
        'x',
        context={'file_path': str(tmp_path / 'a'), 'internal_ptr': '0xdead'},
    )
    failure = to_tool_error(err, generators_dir=tmp_path)
    assert 'internal_ptr' not in failure.details


def test_scrub_falls_back_to_basename_outside_generators_dir(
    tmp_path: Path,
) -> None:
    """file_path outside generators_dir is reduced to its basename."""
    err = ConfigurationLoadError(
        'x',
        context={'file_path': '/etc/passwd'},
    )
    failure = to_tool_error(err, generators_dir=tmp_path)
    assert failure.details['file_path'] == 'passwd'
    assert '/etc' not in repr(failure.details)


def test_reason_absolute_path_relativized(tmp_path: Path) -> None:
    """Absolute paths inside reason text are scrubbed."""
    gens = tmp_path / 'generators'
    err = ConfigurationLoadError(
        'Invalid configuration',
        context={
            'file_path': str(gens / 'g' / 'generator.yml'),
            'reason': (
                'Failed to read: [Errno 2] No such file: '
                f"'{gens / 'g' / 'x.yml'}'"
            ),
        },
    )
    failure = to_tool_error(err, generators_dir=gens)
    # no absolute path under generators_dir remains anywhere in details
    assert str(gens) not in repr(failure.details)


def test_reason_secret_value_redacted(tmp_path: Path) -> None:
    """Values in redact_values are replaced with [redacted] in reason."""
    gens = tmp_path / 'generators'
    credential = 'sup3r-secret-pw'
    err = ConfigurationLoadError(
        'Invalid configuration',
        context={'reason': f'field password: {credential!r} is invalid'},
    )
    failure = to_tool_error(
        err, generators_dir=gens, redact_values=[credential]
    )
    assert credential not in repr(failure.details)
    assert '[redacted]' in failure.details['reason']


def test_scrub_context_reason_path_scrubbed_direct_route(
    tmp_path: Path,
) -> None:
    """Per-event route: scrub_context strips abs paths from reason.

    Mirrors a replay PluginProduceError where ``reason`` is the OSError
    string embedding an absolute path. preview_events calls
    scrub_context directly (not to_tool_error), so the scrub must run
    here too. Covers a path under generators_dir and one outside it.
    """
    gens = tmp_path / 'generators'
    inside = gens / 'g' / 'replay.log'
    outside = tmp_path / 'elsewhere' / 'replay.log'
    context = {
        'file_path': str(inside),
        'reason': (
            f"[Errno 13] Permission denied: '{inside}' (fallback '{outside}')"
        ),
    }

    out = scrub_context(context, gens)

    assert str(gens) not in repr(out)
    assert str(tmp_path) not in repr(out)
    assert out['file_path'] == 'g/replay.log'


def test_error_message_is_scrubbed(tmp_path: Path) -> None:
    """The top-level message is scrubbed too (defense-in-depth)."""
    gens = tmp_path / 'generators'
    secret = 'sup3r-secret'  # noqa: S105
    err = ConfigurationLoadError(
        f"failed at '{gens / 'g' / 'x.yml'}' with {secret}",
        context={},
    )
    failure = to_tool_error(err, generators_dir=gens, redact_values=[secret])
    assert str(gens) not in failure.error
    assert secret not in failure.error
    assert '[redacted]' in failure.error


def test_scrub_log_line_reduces_paths_and_redacts(tmp_path: Path) -> None:
    """Workspace and foreign abs paths reduced; secret values redacted."""
    gens = tmp_path / 'generators'
    logs = tmp_path / 'logs'
    secret = 's3cr3t-tok'  # noqa: S105
    line = (
        f'rendering {gens / "g" / "t.jinja"} failed at '
        f'File "/opt/app/.venv/lib/x.py" token={secret}'
    )
    out = scrub_log_line(line, gens, logs, [secret])
    assert str(gens) not in out
    assert '/opt/app/.venv' not in out
    assert 'x.py' in out
    assert secret not in out
    assert '[redacted]' in out


def test_scrub_log_line_preserves_urls(tmp_path: Path) -> None:
    """A URL is not mangled into a path basename."""
    gens = tmp_path / 'generators'
    logs = tmp_path / 'logs'
    line = 'GET https://api.example.com/v1/users 200'
    out = scrub_log_line(line, gens, logs, [])
    assert 'https://api.example.com/v1/users' in out


def test_scrub_log_line_redacts_path_shaped_secret(tmp_path: Path) -> None:
    """A secret whose value is a path is redacted whole, not basenamed."""
    gens = tmp_path / 'generators'
    logs = tmp_path / 'logs'
    secret = '/run/secrets/db.sock'  # noqa: S105
    out = scrub_log_line(f'connect via {secret} ok', gens, logs, [secret])
    assert secret not in out
    assert 'db.sock' not in out
    assert '[redacted]' in out


def test_reason_path_shaped_secret_redacted(tmp_path: Path) -> None:
    """to_tool_error redacts a path-shaped secret before relativizing."""
    gens = tmp_path / 'generators'
    secret = '/var/secrets/key.pem'  # noqa: S105
    err = ConfigurationLoadError(
        'Invalid configuration',
        context={'reason': f"failed to load '{secret}'"},
    )
    failure = to_tool_error(err, generators_dir=gens, redact_values=[secret])
    assert secret not in repr(failure.details)
    assert 'key.pem' not in repr(failure.details)
    assert '[redacted]' in failure.details['reason']


def test_scrub_message_relativizes_and_redacts(tmp_path: Path) -> None:
    """scrub_message strips abs paths and redacts secrets in a message."""
    gens = tmp_path / 'generators'
    secret = 'sup3r-secret-pw'  # noqa: S105
    message = f"render failed at '{gens / 'g' / 't.jinja'}' with {secret}"
    out = scrub_message(message, gens, [secret])
    assert str(gens) not in out
    assert secret not in out
    assert '[redacted]' in out
