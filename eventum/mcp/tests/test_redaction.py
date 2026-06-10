"""Tests for config-scoped secret redaction."""

from pathlib import Path

import pytest

from eventum.mcp import redaction
from eventum.mcp.redaction import read_config_secret_values


def test_resolves_referenced_secrets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Values of the secrets the config references are returned."""
    monkeypatch.setattr(redaction, 'get_secret', lambda name: f'val-{name}')
    cfg = tmp_path / 'generator.yml'
    cfg.write_text('output:\n  - token: ${secrets.api}\n')
    assert read_config_secret_values(cfg) == ['val-api']


def test_missing_file_returns_empty(tmp_path: Path) -> None:
    """An unreadable config path yields no values, not an error."""
    assert read_config_secret_values(tmp_path / 'absent.yml') == []


def test_no_secrets_returns_empty(tmp_path: Path) -> None:
    """A config that references no secrets yields no values."""
    cfg = tmp_path / 'generator.yml'
    cfg.write_text('output:\n  - stdout: {}\n')
    assert read_config_secret_values(cfg) == []


@pytest.mark.parametrize('exc_type', [ValueError, OSError])
def test_unresolvable_secret_skipped(
    exc_type: type[Exception],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A secret that fails to resolve is skipped, not propagated.

    Covers both raise paths of ``get_secret`` (missing secret and
    keyring error); the remaining referenced secrets still resolve.
    """

    def fake_get_secret(name: str) -> str:
        if name == 'broken':
            msg = 'Secret is missing'
            raise exc_type(msg)
        return f'val-{name}'

    monkeypatch.setattr(redaction, 'get_secret', fake_get_secret)
    cfg = tmp_path / 'generator.yml'
    cfg.write_text(
        'output:\n  - token: ${secrets.broken}\n    password: ${secrets.api}\n'
    )
    assert read_config_secret_values(cfg) == ['val-api']
