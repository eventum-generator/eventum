"""Tests for eventum service CLI commands."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from eventum.cli.service_manager import (
    BinaryNotFoundError,
    ServiceAlreadyInstalledError,
    ServiceError,
    ServicePaths,
    ServiceStatus,
    SystemdNotAvailableError,
)


@pytest.fixture()
def _mock_service_manager():
    """Patch ServiceManager to avoid platform/systemd checks."""
    with patch(
        'eventum.cli.commands.service.ServiceManager',
    ) as mock_cls:
        instance = MagicMock()
        mock_cls.return_value = instance
        instance.detect_binary.return_value = Path('/usr/local/bin/eventum')
        instance.create_directories.return_value = [
            Path('/etc/eventum'),
            Path('/etc/eventum/generators'),
            Path('/var/log/eventum'),
        ]
        instance.generate_config.return_value = True
        instance.generate_startup.return_value = True
        instance.create_cryptfile.return_value = True
        instance.generate_unit_content.return_value = '[Unit]\nTest\n'
        instance.resolve_paths.return_value = ServicePaths(
            config_dir=Path('/etc/eventum'),
            log_dir=Path('/var/log/eventum'),
            generators_dir=Path('/etc/eventum/generators'),
            config_file=Path('/etc/eventum/eventum.yml'),
            startup_file=Path('/etc/eventum/startup.yml'),
            cryptfile=Path('/etc/eventum/cryptfile.cfg'),
            unit_file=Path('/etc/systemd/system/eventum.service'),
            user_mode=False,
        )
        yield mock_cls, instance


@pytest.fixture()
def runner():
    return CliRunner()


def _import_cli():
    """Import cli lazily to avoid module-level side effects."""
    from eventum.cli.commands.service import cli

    return cli


# --- install ---


@patch('eventum.cli.commands.service.os.geteuid', return_value=0)
def test_install_non_interactive(mock_euid, _mock_service_manager, runner):
    _, instance = _mock_service_manager
    cli = _import_cli()

    result = runner.invoke(
        cli,
        [
            'install',
            '--config-dir',
            '/etc/eventum',
            '--log-dir',
            '/var/log/eventum',
            '--no-ask',
        ],
    )

    assert result.exit_code == 0, result.output
    assert 'Done!' in result.output
    assert 'Next steps' in result.output
    instance.install_unit.assert_called_once()


@patch('eventum.cli.commands.service.os.geteuid', return_value=0)
def test_install_interactive(mock_euid, _mock_service_manager, runner):
    cli = _import_cli()

    result = runner.invoke(
        cli,
        ['install'],
        input='/etc/eventum\n/var/log/eventum\ny\n',
    )

    assert result.exit_code == 0, result.output
    assert 'Done!' in result.output


@patch('eventum.cli.commands.service.os.geteuid', return_value=0)
def test_install_aborted(mock_euid, _mock_service_manager, runner):
    _, instance = _mock_service_manager
    cli = _import_cli()

    result = runner.invoke(
        cli,
        ['install'],
        input='/etc/eventum\n/var/log/eventum\nn\n',
    )

    assert result.exit_code == 0
    assert 'Aborted' in result.output
    instance.install_unit.assert_not_called()


@patch('eventum.cli.commands.service.os.geteuid', return_value=0)
def test_install_already_installed(mock_euid, _mock_service_manager, runner):
    _, instance = _mock_service_manager
    instance.install_unit.side_effect = ServiceAlreadyInstalledError(
        'already installed',
    )
    cli = _import_cli()

    result = runner.invoke(
        cli,
        [
            'install',
            '--config-dir',
            '/etc/eventum',
            '--log-dir',
            '/var/log/eventum',
            '--no-ask',
        ],
    )

    assert result.exit_code == 1
    assert 'already installed' in result.output


@patch('eventum.cli.commands.service.os.geteuid', return_value=0)
def test_install_binary_not_found(mock_euid, _mock_service_manager, runner):
    _, instance = _mock_service_manager
    instance.detect_binary.side_effect = BinaryNotFoundError('not found')
    cli = _import_cli()

    result = runner.invoke(
        cli,
        [
            'install',
            '--config-dir',
            '/etc/eventum',
            '--log-dir',
            '/var/log/eventum',
            '--no-ask',
        ],
    )

    assert result.exit_code == 1
    assert 'not found' in result.output


@patch('eventum.cli.commands.service.os.geteuid', return_value=0)
def test_install_permission_denied(mock_euid, _mock_service_manager, runner):
    _, instance = _mock_service_manager
    instance.create_directories.side_effect = PermissionError()
    cli = _import_cli()

    result = runner.invoke(
        cli,
        [
            'install',
            '--config-dir',
            '/etc/eventum',
            '--log-dir',
            '/var/log/eventum',
            '--no-ask',
        ],
    )

    assert result.exit_code == 1
    assert 'Permission denied' in result.output


@patch('eventum.cli.commands.service.os.geteuid', return_value=1000)
def test_install_user_mode_auto(mock_euid, _mock_service_manager, runner):
    mock_cls, _ = _mock_service_manager
    cli = _import_cli()

    runner.invoke(
        cli,
        [
            'install',
            '--config-dir',
            '/tmp/config',
            '--log-dir',
            '/tmp/logs',
            '--no-ask',
        ],
    )

    mock_cls.assert_called_once_with(user_mode=True)


@patch('eventum.cli.commands.service.os.geteuid', return_value=0)
def test_install_user_flag_forces_user_mode(
    mock_euid,
    _mock_service_manager,
    runner,
):
    mock_cls, _ = _mock_service_manager
    cli = _import_cli()

    runner.invoke(
        cli,
        [
            'install',
            '--user',
            '--config-dir',
            '/etc/eventum',
            '--log-dir',
            '/var/log/eventum',
            '--no-ask',
        ],
    )

    mock_cls.assert_called_once_with(user_mode=True)


@patch('eventum.cli.commands.service.os.geteuid', return_value=0)
def test_install_preserves_existing_config(
    mock_euid,
    _mock_service_manager,
    runner,
):
    _, instance = _mock_service_manager
    instance.generate_config.return_value = False
    cli = _import_cli()

    result = runner.invoke(
        cli,
        [
            'install',
            '--config-dir',
            '/etc/eventum',
            '--log-dir',
            '/var/log/eventum',
            '--no-ask',
        ],
    )

    assert result.exit_code == 0
    assert 'Existing configuration preserved' in result.output


@patch('eventum.cli.commands.service.os.geteuid', return_value=0)
def test_install_systemd_not_available(mock_euid, runner):
    cli = _import_cli()

    with patch(
        'eventum.cli.commands.service.ServiceManager',
        side_effect=SystemdNotAvailableError('systemd not available'),
    ):
        result = runner.invoke(
            cli,
            [
                'install',
                '--config-dir',
                '/etc/eventum',
                '--log-dir',
                '/var/log/eventum',
                '--no-ask',
            ],
        )

    assert result.exit_code == 1
    assert 'systemd not available' in result.output


# --- uninstall ---


@patch('eventum.cli.commands.service.os.geteuid', return_value=0)
def test_uninstall_success(mock_euid, _mock_service_manager, runner):
    _, instance = _mock_service_manager
    instance.get_status.return_value = ServiceStatus(
        installed=True,
        active=True,
        enabled=True,
        unit_file=Path('/etc/systemd/system/eventum.service'),
        config_file=Path('/etc/eventum/eventum.yml'),
        user_mode=False,
    )
    cli = _import_cli()

    result = runner.invoke(cli, ['uninstall'])

    assert result.exit_code == 0, result.output
    assert 'Done!' in result.output
    instance.stop_service.assert_called_once()
    instance.disable_service.assert_called_once()
    instance.remove_unit.assert_called_once()


@patch('eventum.cli.commands.service.os.geteuid', return_value=0)
def test_uninstall_not_installed(mock_euid, _mock_service_manager, runner):
    _, instance = _mock_service_manager
    instance.get_status.return_value = ServiceStatus(
        installed=False,
        active=False,
        enabled=False,
        unit_file=None,
        config_file=None,
        user_mode=False,
    )
    cli = _import_cli()

    result = runner.invoke(cli, ['uninstall'])

    assert result.exit_code == 1
    assert 'not installed' in result.output


@patch('eventum.cli.commands.service.os.geteuid', return_value=0)
def test_uninstall_purge(mock_euid, _mock_service_manager, runner):
    _, instance = _mock_service_manager
    instance.get_status.return_value = ServiceStatus(
        installed=True,
        active=False,
        enabled=False,
        unit_file=Path('/etc/systemd/system/eventum.service'),
        config_file=Path('/etc/eventum/eventum.yml'),
        user_mode=False,
    )
    cli = _import_cli()

    # Mock extract helpers to avoid filesystem access
    with (
        patch(
            'eventum.cli.commands.service._extract_config_dir',
            return_value=Path('/etc/eventum'),
        ),
        patch(
            'eventum.cli.commands.service._extract_log_dir',
            return_value=Path('/var/log/eventum'),
        ),
        patch('pathlib.Path.exists', return_value=True),
    ):
        result = runner.invoke(
            cli,
            ['uninstall', '--purge'],
            input='y\ny\n',
        )

    assert result.exit_code == 0, result.output
    assert 'Done!' in result.output
    assert instance.purge_directory.call_count == 2


@patch('eventum.cli.commands.service.os.geteuid', return_value=0)
def test_uninstall_shows_preserved_hint(
    mock_euid,
    _mock_service_manager,
    runner,
):
    _, instance = _mock_service_manager
    instance.get_status.return_value = ServiceStatus(
        installed=True,
        active=False,
        enabled=False,
        unit_file=Path('/etc/systemd/system/eventum.service'),
        config_file=Path('/etc/eventum/eventum.yml'),
        user_mode=False,
    )
    cli = _import_cli()

    result = runner.invoke(cli, ['uninstall'])

    assert result.exit_code == 0, result.output
    assert 'Configuration files preserved' in result.output
    assert '--purge' in result.output


# --- status ---


@patch('eventum.cli.commands.service.os.geteuid', return_value=0)
def test_status_installed_running(mock_euid, _mock_service_manager, runner):
    _, instance = _mock_service_manager
    instance.get_status.return_value = ServiceStatus(
        installed=True,
        active=True,
        enabled=True,
        unit_file=Path('/etc/systemd/system/eventum.service'),
        config_file=Path('/etc/eventum/eventum.yml'),
        user_mode=False,
    )
    cli = _import_cli()

    result = runner.invoke(cli, ['status'])

    assert result.exit_code == 0
    assert 'installed' in result.output
    assert '/etc/eventum/eventum.yml' in result.output


@patch('eventum.cli.commands.service.os.geteuid', return_value=0)
def test_status_not_installed(mock_euid, _mock_service_manager, runner):
    _, instance = _mock_service_manager
    instance.get_status.return_value = ServiceStatus(
        installed=False,
        active=False,
        enabled=False,
        unit_file=None,
        config_file=None,
        user_mode=False,
    )
    cli = _import_cli()

    result = runner.invoke(cli, ['status'])

    assert result.exit_code == 0
    assert 'not installed' in result.output


@patch('eventum.cli.commands.service.os.geteuid', return_value=0)
def test_status_installed_inactive(mock_euid, _mock_service_manager, runner):
    _, instance = _mock_service_manager
    instance.get_status.return_value = ServiceStatus(
        installed=True,
        active=False,
        enabled=False,
        unit_file=Path('/etc/systemd/system/eventum.service'),
        config_file=Path('/etc/eventum/eventum.yml'),
        user_mode=False,
    )
    cli = _import_cli()

    result = runner.invoke(cli, ['status'])

    assert result.exit_code == 0
    assert 'installed' in result.output
    assert 'inactive' in result.output
