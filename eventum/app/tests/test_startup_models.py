"""Tests for startup generator parameters models."""

from pathlib import Path

from eventum.app.startup import StartupGeneratorParameters


def test_startup_generator_parameters_autostart_default() -> None:
    """Default autostart is True."""
    params = StartupGeneratorParameters(
        id='gen1',
        path=Path('config.yml'),
    )
    assert params.autostart is True  # noqa: S101


def test_startup_generator_parameters_autostart_false() -> None:
    """Explicit autostart=False is preserved."""
    params = StartupGeneratorParameters(
        id='gen1',
        path=Path('config.yml'),
        autostart=False,
    )
    assert params.autostart is False  # noqa: S101


def test_startup_generator_parameters_scenarios_default() -> None:
    """Default scenarios list is empty."""
    params = StartupGeneratorParameters(
        id='gen1',
        path=Path('config.yml'),
    )
    assert params.scenarios == []  # noqa: S101


def test_startup_generator_parameters_scenarios_set() -> None:
    """Explicit scenarios list is preserved."""
    params = StartupGeneratorParameters(
        id='gen1',
        path=Path('config.yml'),
        scenarios=['scenario-a', 'scenario-b'],
    )
    assert params.scenarios == ['scenario-a', 'scenario-b']  # noqa: S101
