"""Tests for settings serialization."""

from pathlib import Path

import yaml

from eventum.app.models.parameters.log import LogParameters
from eventum.app.models.parameters.path import PathParameters
from eventum.app.models.parameters.server import ServerParameters
from eventum.app.models.settings import Settings, write_settings
from eventum.core.parameters import GenerationParameters

# 'generators' spelled in Cyrillic
NON_ASCII_DIR_NAME = 'генераторы'


def _build_settings(tmp_path: Path) -> Settings:
    return Settings(
        server=ServerParameters(),
        generation=GenerationParameters(),
        log=LogParameters(),
        path=PathParameters(
            logs=tmp_path / 'logs',
            startup=tmp_path / 'startup.yml',
            generators_dir=tmp_path / NON_ASCII_DIR_NAME,
            keyring_cryptfile=tmp_path / 'keyring.cfg',
        ),
    )


def test_write_settings_keeps_non_ascii_unescaped(tmp_path: Path) -> None:
    """Non-ASCII values are written verbatim, not as escapes."""
    settings = _build_settings(tmp_path)
    path = tmp_path / 'eventum.yml'

    write_settings(settings, path)

    content = path.read_text(encoding='utf-8')
    assert NON_ASCII_DIR_NAME in content
    assert '\\u' not in content


def test_write_settings_is_readable_back(tmp_path: Path) -> None:
    """Written settings parse back into the same values."""
    settings = _build_settings(tmp_path)
    path = tmp_path / 'eventum.yml'

    write_settings(settings, path)

    parsed = yaml.safe_load(path.read_text(encoding='utf-8'))
    assert parsed['path']['generators_dir'] == str(
        settings.path.generators_dir
    )
