"""Commands for managing Eventum systemd service."""

import os
import sys
from pathlib import Path

import click
import yaml
from pydantic import BaseModel

from eventum.cli.pydantic_converter import from_model
from eventum.cli.service_manager import (
    SERVICE_NAME,
    ServiceError,
    ServiceManager,
    ServicePaths,
    ServiceStatus,
)


def _default_config_dir(*, user_mode: bool) -> Path:
    """Get default configuration directory.

    Parameters
    ----------
    user_mode : bool
        Whether to return user-level path or system-level path.

    Returns
    -------
    Path
        Default configuration directory path.

    """
    if user_mode:
        return Path.home() / '.config' / 'eventum'
    return Path('/etc/eventum')


def _default_log_dir(*, user_mode: bool) -> Path:
    """Get default log directory.

    Parameters
    ----------
    user_mode : bool
        Whether to return user-level path or system-level path.

    Returns
    -------
    Path
        Default log directory path.

    """
    if user_mode:
        return Path.home() / '.local' / 'state' / 'eventum' / 'logs'
    return Path('/var/log/eventum')


def _resolve_user_mode(*, user_flag: bool) -> bool:
    """Determine effective user mode.

    Parameters
    ----------
    user_flag : bool
        Whether ``--user`` flag was passed.

    Returns
    -------
    bool
        True for user-level service, False for system-level.

    """
    return user_flag or os.geteuid() != 0


class InstallParameters(BaseModel, extra='forbid', frozen=True):
    """Install parameters.

    Attributes
    ----------
    config_dir : Path | None, default=None
        Directory for configuration files.

    log_dir : Path | None, default=None
        Directory for log files.

    """

    config_dir: Path | None = None
    log_dir: Path | None = None


@click.group('service')
def cli() -> None:
    """Manage Eventum systemd service."""


def _resolve_dir(
    value: Path | None,
    *,
    prompt_text: str,
    default: Path,
    no_ask: bool,
) -> Path:
    """Prompt for a directory path if not provided via CLI option.

    Parameters
    ----------
    value : Path | None
        Value provided via CLI option, or None if not provided.

    prompt_text : str
        Text to display when prompting the user.

    default : Path
        Default value to use when prompting or when ``no_ask``
        is True.

    no_ask : bool
        Whether to skip the interactive prompt and use the default.

    Returns
    -------
    Path
        Resolved directory path.

    """
    if value is not None:
        return value

    if no_ask:
        return default

    return Path(click.prompt(prompt_text, default=str(default)))


def _print_install_summary(
    paths: ServicePaths,
    binary: Path,
    *,
    effective_user_mode: bool,
) -> None:
    """Print installation summary before confirmation."""
    mode_label = 'user' if effective_user_mode else 'system'
    click.echo()
    click.echo(
        'Eventum service will be installed with the following settings:',
    )
    click.echo(f'  Mode:       {mode_label}')
    click.echo(f'  Binary:     {binary}')
    click.echo(f'  Config dir: {paths.config_dir}')
    click.echo(f'  Log dir:    {paths.log_dir}')
    click.echo(f'  Unit file:  {paths.unit_file}')
    click.echo()


def _perform_install(
    manager: ServiceManager,
    paths: ServicePaths,
    binary: Path,
) -> None:
    """Create dirs, generate configs, install unit file."""
    created_dirs = manager.create_directories(paths)
    for d in created_dirs:
        click.echo(f'Created {d}/')

    if manager.generate_config(paths):
        click.echo(f'Generated {paths.config_file}')
    else:
        click.echo(
            f'Existing configuration preserved at {paths.config_file}',
        )

    if manager.generate_startup(paths):
        click.echo(f'Generated {paths.startup_file}')
    else:
        click.echo(
            f'Existing startup file preserved at {paths.startup_file}',
        )

    if manager.create_cryptfile(paths):
        click.echo(f'Created {paths.cryptfile}')

    unit_content = manager.generate_unit_content(paths, binary)
    manager.install_unit(paths, unit_content)
    click.echo(f'Installed {paths.unit_file}')
    click.echo('Reloaded systemd daemon')


def _print_next_steps(
    paths: ServicePaths,
    *,
    effective_user_mode: bool,
) -> None:
    """Print post-install instructions."""
    click.echo()
    click.echo('Done! Next steps:')

    prefix = 'sudo ' if not effective_user_mode else ''
    user_flag = ' --user' if effective_user_mode else ''

    click.echo(
        f'  1. Review configuration:  cat {paths.config_file}',
    )
    click.echo(
        f'  2. Enable on boot:        '
        f'{prefix}systemctl{user_flag} enable {SERVICE_NAME}',
    )
    click.echo(
        f'  3. Start the service:     '
        f'{prefix}systemctl{user_flag} start {SERVICE_NAME}',
    )
    click.echo(
        '  4. Check status:          eventum service status',
    )


@cli.command()
@from_model(InstallParameters)
@click.option(
    '--user',
    'user_mode',
    is_flag=True,
    default=False,
    help='Install as user service (even when running as root).',
)
@click.option(
    '--no-ask',
    is_flag=True,
    default=False,
    help='Skip confirmation prompts.',
)
def install(
    install_parameters: InstallParameters,
    user_mode: bool,  # noqa: FBT001
    no_ask: bool,  # noqa: FBT001
) -> None:
    """Install Eventum as a systemd service."""
    effective_user_mode = _resolve_user_mode(user_flag=user_mode)

    try:
        manager = ServiceManager(user_mode=effective_user_mode)
    except ServiceError as e:
        click.echo(f'Error: {e}', err=True)
        sys.exit(1)

    config_dir = _resolve_dir(
        install_parameters.config_dir,
        prompt_text='Configuration directory',
        default=_default_config_dir(user_mode=effective_user_mode),
        no_ask=no_ask,
    )
    log_dir = _resolve_dir(
        install_parameters.log_dir,
        prompt_text='Log directory',
        default=_default_log_dir(user_mode=effective_user_mode),
        no_ask=no_ask,
    )

    try:
        paths = manager.resolve_paths(config_dir, log_dir)
        binary = manager.detect_binary()
    except ServiceError as e:
        click.echo(f'Error: {e}', err=True)
        sys.exit(1)

    _print_install_summary(
        paths,
        binary,
        effective_user_mode=effective_user_mode,
    )

    if not no_ask and not click.confirm('Proceed?', default=True):
        click.echo('Aborted.')
        sys.exit(0)

    try:
        _perform_install(manager, paths, binary)
    except PermissionError:
        click.echo(
            'Error: Permission denied. Run with sudo for '
            'system service or use --user for user service.',
            err=True,
        )
        sys.exit(1)
    except ServiceError as e:
        click.echo(f'Error: {e}', err=True)
        sys.exit(1)

    _print_next_steps(
        paths,
        effective_user_mode=effective_user_mode,
    )


def _extract_config_dir(
    svc_status: ServiceStatus,
) -> Path | None:
    """Extract config_dir from installed service."""
    if svc_status.config_file is None:
        return None
    return svc_status.config_file.parent


def _extract_log_dir(
    svc_status: ServiceStatus,
) -> Path | None:
    """Extract log_dir from installed service config."""
    if svc_status.config_file is None:
        return None

    try:
        with svc_status.config_file.open() as f:
            data = yaml.load(f, Loader=yaml.SafeLoader)
        if isinstance(data, dict) and 'path.logs' in data:
            return Path(data['path.logs'])
    except OSError, yaml.error.YAMLError:
        click.echo(
            f'Warning: Could not read {svc_status.config_file}, '
            'log directory will not be purged.',
            err=True,
        )

    return None


def _perform_uninstall(
    manager: ServiceManager,
    unit_file: Path,
) -> None:
    """Stop, disable, and remove the service unit."""
    click.echo(f'Stopping {SERVICE_NAME} service...')
    manager.stop_service()

    click.echo(f'Disabling {SERVICE_NAME} service...')
    manager.disable_service()

    manager.remove_unit(unit_file)
    click.echo(f'Removed {unit_file}')
    click.echo('Reloaded systemd daemon')


def _purge_data(
    manager: ServiceManager,
    config_dir: Path | None,
    log_dir: Path | None,
) -> None:
    """Interactively purge config and log directories."""
    if (
        config_dir is not None
        and config_dir.exists()
        and click.confirm(
            f'Remove configuration directory {config_dir}/ '
            f'and all its contents?',
            default=False,
        )
    ):
        manager.purge_directory(config_dir)
        click.echo(f'Removed {config_dir}/')

    if (
        log_dir is not None
        and log_dir.exists()
        and click.confirm(
            f'Remove log directory {log_dir}/ and all its contents?',
            default=False,
        )
    ):
        manager.purge_directory(log_dir)
        click.echo(f'Removed {log_dir}/')


@cli.command()
@click.option(
    '--user',
    'user_mode',
    is_flag=True,
    default=False,
    help='Uninstall user service (even when running as root).',
)
@click.option(
    '--purge',
    is_flag=True,
    default=False,
    help='Also remove configuration and log directories.',
)
def uninstall(
    user_mode: bool,  # noqa: FBT001
    purge: bool,  # noqa: FBT001
) -> None:
    """Uninstall Eventum systemd service."""
    effective_user_mode = _resolve_user_mode(user_flag=user_mode)

    try:
        manager = ServiceManager(user_mode=effective_user_mode)
    except ServiceError as e:
        click.echo(f'Error: {e}', err=True)
        sys.exit(1)

    svc_status = manager.get_status()

    if not svc_status.installed:
        click.echo('Error: Service is not installed.', err=True)
        sys.exit(1)

    config_dir = _extract_config_dir(svc_status)
    log_dir = _extract_log_dir(svc_status) if purge else None

    assert svc_status.unit_file is not None  # noqa: S101

    try:
        _perform_uninstall(manager, svc_status.unit_file)
    except PermissionError:
        click.echo(
            'Error: Permission denied. Run with sudo for '
            'system service or use --user for user service.',
            err=True,
        )
        sys.exit(1)
    except ServiceError as e:
        click.echo(f'Error: {e}', err=True)
        sys.exit(1)

    if purge:
        _purge_data(manager, config_dir, log_dir)

    click.echo()
    click.echo('Done!')

    if not purge and config_dir is not None:
        click.echo(
            f'Configuration files preserved in {config_dir}/',
        )
        click.echo()
        click.echo('To also remove configuration and logs, run:')
        prefix = 'sudo ' if not effective_user_mode else ''
        user_flag = ' --user' if effective_user_mode else ''
        click.echo(
            f'  {prefix}eventum service uninstall{user_flag} --purge',
        )


@cli.command()
@click.option(
    '--user',
    'user_mode',
    is_flag=True,
    default=False,
    help='Check user service status.',
)
def status(
    user_mode: bool,  # noqa: FBT001
) -> None:
    """Show Eventum service status."""
    effective_user_mode = _resolve_user_mode(user_flag=user_mode)

    try:
        manager = ServiceManager(user_mode=effective_user_mode)
    except ServiceError as e:
        click.echo(f'Error: {e}', err=True)
        sys.exit(1)

    svc_status = manager.get_status()

    if not svc_status.installed:
        click.echo(
            f'Service:  {click.style("not installed", fg="red")}',
        )
        sys.exit(0)

    state_text = (
        click.style('active (running)', fg='green')
        if svc_status.active
        else click.style('inactive', fg='yellow')
    )
    enabled_text = (
        click.style('yes', fg='green')
        if svc_status.enabled
        else click.style('no', fg='yellow')
    )

    click.echo(
        f'Service:  {click.style("installed", fg="green")}',
    )
    click.echo(f'Unit:     {svc_status.unit_file}')
    click.echo(f'State:    {state_text}')
    click.echo(f'Enabled:  {enabled_text}')

    if svc_status.config_file is not None:
        click.echo(f'Config:   {svc_status.config_file}')
