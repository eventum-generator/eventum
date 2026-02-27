"""Tests for service manager."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml
from flatten_dict import unflatten  # type: ignore[import-untyped]

from eventum.app.models.settings import Settings
from eventum.cli.service_manager import (
    BinaryNotFoundError,
    ServiceAlreadyInstalledError,
    ServiceError,
    ServiceManager,
    ServicePaths,
    SystemdNotAvailableError,
)


@pytest.fixture()
def _mock_platform():
    with (
        patch(
            'eventum.cli.service_manager.sys.platform',
            'linux',
        ),
        patch(
            'eventum.cli.service_manager.shutil.which',
            return_value='/usr/bin/systemctl',
        ),
    ):
        yield


@pytest.fixture()
def manager(_mock_platform):
    return ServiceManager(user_mode=False)


@pytest.fixture()
def user_manager(_mock_platform):
    return ServiceManager(user_mode=True)


# --- Platform checks ---


def test_check_platform_non_linux():
    with (
        patch('eventum.cli.service_manager.sys') as mock_sys,
        patch('eventum.cli.service_manager.shutil') as mock_shutil,
    ):
        mock_sys.platform = 'darwin'
        mock_shutil.which.return_value = '/usr/bin/systemctl'

        with pytest.raises(ServiceError, match='only supported on Linux'):
            ServiceManager(user_mode=False)


def test_check_systemd_not_available():
    with (
        patch('eventum.cli.service_manager.sys') as mock_sys,
        patch('eventum.cli.service_manager.shutil') as mock_shutil,
    ):
        mock_sys.platform = 'linux'
        mock_shutil.which.return_value = None

        with pytest.raises(
            SystemdNotAvailableError,
            match='not available',
        ):
            ServiceManager(user_mode=False)


# --- resolve_paths ---


def test_resolve_paths_system(manager):
    paths = manager.resolve_paths(
        config_dir=Path('/etc/eventum'),
        log_dir=Path('/var/log/eventum'),
    )

    assert paths.config_dir == Path('/etc/eventum')
    assert paths.log_dir == Path('/var/log/eventum')
    assert paths.generators_dir == Path('/etc/eventum/generators')
    assert paths.config_file == Path('/etc/eventum/eventum.yml')
    assert paths.startup_file == Path('/etc/eventum/startup.yml')
    assert paths.cryptfile == Path('/etc/eventum/cryptfile.cfg')
    assert paths.unit_file == Path(
        '/etc/systemd/system/eventum.service',
    )
    assert paths.user_mode is False


def test_resolve_paths_user(user_manager):
    home = Path.home()
    paths = user_manager.resolve_paths(
        config_dir=home / '.config' / 'eventum',
        log_dir=home / '.local' / 'state' / 'eventum' / 'logs',
    )

    assert paths.config_dir == home / '.config' / 'eventum'
    assert paths.unit_file == (
        home / '.config' / 'systemd' / 'user' / 'eventum.service'
    )
    assert paths.user_mode is True


# --- detect_binary ---


def test_detect_binary_on_path(manager):
    with patch(
        'eventum.cli.service_manager.shutil.which',
        return_value='/usr/local/bin/eventum',
    ):
        binary = manager.detect_binary()
        assert binary == Path('/usr/local/bin/eventum')


def test_detect_binary_fallback_venv(manager):
    with (
        patch(
            'eventum.cli.service_manager.shutil.which',
            return_value=None,
        ),
        patch(
            'eventum.cli.service_manager.sys.executable',
            '/opt/venv/bin/python',
        ),
        patch.object(Path, 'is_file', return_value=True),
    ):
        binary = manager.detect_binary()
        assert binary.name == 'eventum'


def test_detect_binary_not_found(manager):
    with (
        patch(
            'eventum.cli.service_manager.shutil.which',
            return_value=None,
        ),
        patch(
            'eventum.cli.service_manager.sys.executable',
            '/opt/venv/bin/python',
        ),
        patch.object(Path, 'is_file', return_value=False),
    ):
        with pytest.raises(BinaryNotFoundError, match='Could not find'):
            manager.detect_binary()


# --- create_directories ---


def test_create_directories(manager, tmp_path):
    paths = manager.resolve_paths(
        config_dir=tmp_path / 'config',
        log_dir=tmp_path / 'logs',
    )

    created = manager.create_directories(paths)

    assert (tmp_path / 'config').is_dir()
    assert (tmp_path / 'config' / 'generators').is_dir()
    assert (tmp_path / 'logs').is_dir()
    assert len(created) == 3


def test_create_directories_existing(manager, tmp_path):
    config_dir = tmp_path / 'config'
    config_dir.mkdir()
    (config_dir / 'generators').mkdir()
    (tmp_path / 'logs').mkdir()

    paths = manager.resolve_paths(
        config_dir=config_dir,
        log_dir=tmp_path / 'logs',
    )

    created = manager.create_directories(paths)
    assert len(created) == 0


# --- generate_config ---


def test_generate_config(manager, tmp_path):
    paths = manager.resolve_paths(
        config_dir=tmp_path / 'config',
        log_dir=tmp_path / 'logs',
    )
    (tmp_path / 'config').mkdir(parents=True)

    result = manager.generate_config(paths)

    assert result is True
    assert paths.config_file.exists()

    with paths.config_file.open() as f:
        content = f.read()

    assert '# Eventum Configuration' in content
    assert 'path.logs' in content


def test_generate_config_already_exists(manager, tmp_path):
    paths = manager.resolve_paths(
        config_dir=tmp_path / 'config',
        log_dir=tmp_path / 'logs',
    )
    (tmp_path / 'config').mkdir(parents=True)
    paths.config_file.write_text('existing content')

    result = manager.generate_config(paths)
    assert result is False
    assert paths.config_file.read_text() == 'existing content'


def test_generated_config_validates_against_settings(manager, tmp_path):
    """Ensure generated config passes Settings.model_validate."""
    paths = manager.resolve_paths(
        config_dir=tmp_path / 'config',
        log_dir=tmp_path / 'logs',
    )
    (tmp_path / 'config').mkdir(parents=True)
    manager.generate_config(paths)

    with paths.config_file.open() as f:
        data = yaml.load(f, Loader=yaml.SafeLoader)

    nested = unflatten(data, splitter='dot')
    settings = Settings.model_validate(nested)

    assert settings.path.logs == paths.log_dir
    assert settings.path.generators_dir == paths.generators_dir
    assert settings.path.startup == paths.startup_file
    assert settings.path.keyring_cryptfile == paths.cryptfile
    assert settings.server.port == 9474
    assert settings.generation.timezone == 'UTC'
    assert settings.log.level == 'info'


# --- generate_startup ---


def test_generate_startup(manager, tmp_path):
    paths = manager.resolve_paths(
        config_dir=tmp_path / 'config',
        log_dir=tmp_path / 'logs',
    )
    (tmp_path / 'config').mkdir(parents=True)

    result = manager.generate_startup(paths)
    assert result is True
    assert paths.startup_file.exists()

    data = yaml.load(paths.startup_file.read_text(), Loader=yaml.SafeLoader)
    assert data == []


def test_generate_startup_already_exists(manager, tmp_path):
    paths = manager.resolve_paths(
        config_dir=tmp_path / 'config',
        log_dir=tmp_path / 'logs',
    )
    (tmp_path / 'config').mkdir(parents=True)
    paths.startup_file.write_text('existing')

    assert manager.generate_startup(paths) is False


# --- create_cryptfile ---


def test_create_cryptfile(manager, tmp_path):
    paths = manager.resolve_paths(
        config_dir=tmp_path / 'config',
        log_dir=tmp_path / 'logs',
    )
    (tmp_path / 'config').mkdir(parents=True)

    result = manager.create_cryptfile(paths)
    assert result is True
    assert paths.cryptfile.exists()
    assert paths.cryptfile.read_text() == ''


def test_create_cryptfile_already_exists(manager, tmp_path):
    paths = manager.resolve_paths(
        config_dir=tmp_path / 'config',
        log_dir=tmp_path / 'logs',
    )
    (tmp_path / 'config').mkdir(parents=True)
    paths.cryptfile.write_text('data')

    assert manager.create_cryptfile(paths) is False


# --- generate_unit_content ---


def test_generate_unit_content_system(manager, tmp_path):
    paths = manager.resolve_paths(
        config_dir=tmp_path / 'config',
        log_dir=tmp_path / 'logs',
    )

    content = manager.generate_unit_content(
        paths,
        Path('/usr/local/bin/eventum'),
    )

    assert 'WantedBy=multi-user.target' in content
    assert (
        f'ExecStart=/usr/local/bin/eventum run -c {paths.config_file}'
        in content
    )
    assert 'ExecReload=/bin/kill -HUP $MAINPID' in content
    assert 'SuccessExitStatus=1' in content


def test_generate_unit_content_user(user_manager, tmp_path):
    paths = user_manager.resolve_paths(
        config_dir=tmp_path / 'config',
        log_dir=tmp_path / 'logs',
    )

    content = user_manager.generate_unit_content(
        paths,
        Path('/home/user/.local/bin/eventum'),
    )

    assert 'WantedBy=default.target' in content


# --- install_unit ---


def test_install_unit(manager, tmp_path):
    unit_dir = tmp_path / 'systemd'
    unit_file = unit_dir / 'eventum.service'

    paths = ServicePaths(
        config_dir=tmp_path / 'config',
        log_dir=tmp_path / 'logs',
        generators_dir=tmp_path / 'config' / 'generators',
        config_file=tmp_path / 'config' / 'eventum.yml',
        startup_file=tmp_path / 'config' / 'startup.yml',
        cryptfile=tmp_path / 'config' / 'cryptfile.cfg',
        unit_file=unit_file,
        user_mode=False,
    )

    with patch.object(manager, '_daemon_reload'):
        manager.install_unit(paths, '[Unit]\nDescription=Test\n')

    assert unit_file.exists()
    assert '[Unit]' in unit_file.read_text()


def test_install_unit_already_exists(manager, tmp_path):
    unit_dir = tmp_path / 'systemd'
    unit_dir.mkdir()
    unit_file = unit_dir / 'eventum.service'
    unit_file.write_text('existing')

    paths = ServicePaths(
        config_dir=tmp_path / 'config',
        log_dir=tmp_path / 'logs',
        generators_dir=tmp_path / 'config' / 'generators',
        config_file=tmp_path / 'config' / 'eventum.yml',
        startup_file=tmp_path / 'config' / 'startup.yml',
        cryptfile=tmp_path / 'config' / 'cryptfile.cfg',
        unit_file=unit_file,
        user_mode=False,
    )

    with pytest.raises(
        ServiceAlreadyInstalledError,
        match='already installed',
    ):
        manager.install_unit(paths, 'content')


# --- stop/disable/remove ---


def test_stop_service(manager):
    with patch.object(manager, '_systemctl') as mock:
        manager.stop_service()
        mock.assert_called_once_with('stop', 'eventum', check=False)


def test_disable_service(manager):
    with patch.object(manager, '_systemctl') as mock:
        manager.disable_service()
        mock.assert_called_once_with('disable', 'eventum', check=False)


def test_remove_unit(manager, tmp_path):
    unit_file = tmp_path / 'eventum.service'
    unit_file.write_text('content')

    with patch.object(manager, '_daemon_reload'):
        manager.remove_unit(unit_file)

    assert not unit_file.exists()


# --- purge_directory ---


def test_purge_directory(manager, tmp_path):
    target = tmp_path / 'to_remove'
    target.mkdir()
    (target / 'file.txt').write_text('data')

    manager.purge_directory(target)
    assert not target.exists()


def test_purge_directory_nonexistent(manager, tmp_path):
    target = tmp_path / 'nonexistent'
    manager.purge_directory(target)  # should not raise


# --- get_status ---


def test_get_status_installed_running(manager, tmp_path):
    unit_file = tmp_path / 'eventum.service'
    unit_file.write_text(
        '[Service]\n'
        'ExecStart=/usr/local/bin/eventum run -c /etc/eventum/eventum.yml\n',
    )

    with (
        patch.object(manager, '_find_unit_file', return_value=unit_file),
        patch.object(manager, '_is_active', return_value=True),
        patch.object(manager, '_is_enabled', return_value=True),
    ):
        status = manager.get_status()

    assert status.installed is True
    assert status.active is True
    assert status.enabled is True
    assert status.config_file == Path('/etc/eventum/eventum.yml')


def test_get_status_not_installed(manager):
    with patch.object(manager, '_find_unit_file', return_value=None):
        status = manager.get_status()

    assert status.installed is False
    assert status.active is False
    assert status.unit_file is None


# --- _systemctl ---


def test_systemctl_user_flag(user_manager):
    with patch(
        'eventum.cli.service_manager.subprocess.run',
    ) as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        user_manager._systemctl('status', 'eventum')

        args = mock_run.call_args[0][0]
        assert args == ['systemctl', '--user', 'status', 'eventum']


def test_systemctl_system_mode(manager):
    with patch(
        'eventum.cli.service_manager.subprocess.run',
    ) as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        manager._systemctl('status', 'eventum')

        args = mock_run.call_args[0][0]
        assert args == ['systemctl', 'status', 'eventum']


# --- _extract_config_path ---


def test_extract_config_path(tmp_path):
    unit_file = tmp_path / 'eventum.service'
    unit_file.write_text(
        '[Service]\n'
        'ExecStart=/usr/local/bin/eventum run -c /etc/eventum/eventum.yml\n',
    )

    result = ServiceManager._extract_config_path(unit_file)
    assert result == Path('/etc/eventum/eventum.yml')


def test_extract_config_path_missing(tmp_path):
    unit_file = tmp_path / 'eventum.service'
    unit_file.write_text('[Service]\nExecStart=/usr/local/bin/eventum run\n')

    result = ServiceManager._extract_config_path(unit_file)
    assert result is None
