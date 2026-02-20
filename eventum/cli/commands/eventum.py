"""Commands for starting app or single generator."""

import os
import signal
import sys
from pathlib import Path
from typing import Literal, NoReturn

import click
import structlog
import yaml
from flatten_dict import unflatten  # type: ignore[import-untyped]
from pydantic import ValidationError
from setproctitle import setproctitle

import eventum
import eventum.logging.config as logconf
from eventum.app.hooks import InstanceHooks
from eventum.app.main import App, AppError
from eventum.app.models.settings import Settings
from eventum.cli.pydantic_converter import from_model
from eventum.cli.splash_screen import SPLASH_SCREEN
from eventum.core.generator import Generator
from eventum.core.parameters import GeneratorParameters
from eventum.security.manage import SECURITY_SETTINGS
from eventum.utils.validation_prettier import prettify_validation_errors

setproctitle('eventum')
logger = structlog.stdlib.get_logger()


@click.group('eventum')
@click.version_option(
    version=eventum.__version__,
    package_name=eventum.__name__,
    message=SPLASH_SCREEN,
)
def cli():  # noqa: ANN201
    """Data generation platform."""  # noqa: D401


def _start_app_instance(config: str) -> App:
    """Start application instance."""
    config_path = Path(config)
    try:
        with config_path.open() as f:
            try:
                data = yaml.load(f, Loader=yaml.SafeLoader)
            except yaml.error.YAMLError as e:
                click.echo(
                    f'Error: Failed to parse configuration YAML content: {e}',
                    err=True,
                )
                sys.exit(1)
    except OSError as e:
        click.echo(
            f'Error: Failed to open config file: {e}',
            err=True,
        )
        sys.exit(1)

    data = unflatten(data, splitter='dot')

    try:
        settings = Settings.model_validate(data)
    except ValidationError as e:
        click.echo(
            (
                'Error: Failed to validate settings:'
                + os.linesep
                + prettify_validation_errors(e.errors(), sep=os.linesep)
            ),
            err=True,
        )
        sys.exit(1)

    # Since current function can be called many times, we should clear logconf
    logconf.clear()

    logconf.use_console_and_file(
        format=settings.log.format,
        level=settings.log.level.upper(),  # type: ignore[arg-type]
        logs_dir=settings.path.logs,
        backup_count=settings.log.backups,
        max_bytes=settings.log.max_bytes,
    )

    click.echo(SPLASH_SCREEN)

    app = App(
        settings=settings,
        instance_hooks=InstanceHooks(
            get_settings_file_path=lambda: config_path,
            terminate=lambda: os.kill(os.getpid(), signal.SIGTERM),
            restart=lambda: os.kill(os.getpid(), signal.SIGHUP),
        ),
    )

    logger.info('Starting application')
    try:
        app.start()
    except AppError as e:
        logger.error(str(e), **e.context)
        sys.exit(1)
    except Exception as e:
        logger.exception(
            'Unexpected error occurred during app execution',
            reason=str(e),
        )
        sys.exit(1)

    return app


@cli.command
@click.option(
    '-c',
    '--config',
    required=True,
    help='Path to main configuration file',
    type=click.Path(exists=True, resolve_path=True),
)
def run(config: str) -> None:
    """Run application with all defined generators."""
    app: App = None  # type: ignore[assignment]

    def handle_termination(signal_num: int) -> NoReturn:
        nonlocal app

        logger.info(
            'OS signal is received',
            signal=signal.Signals(signal_num).name,
        )
        logger.info('App is going to be stopped')
        app.stop()
        sys.exit(1)

    def handle_restart(signal_num: int) -> None:
        nonlocal app

        logger.info(
            'OS signal is received',
            signal=signal.Signals(signal_num).name,
        )
        logger.info('App is going to be restarted')
        app.stop()
        app = _start_app_instance(config=config)

    app = _start_app_instance(config=config)

    signal.signal(signal.SIGINT, lambda sig, __: handle_termination(sig))
    signal.signal(signal.SIGTERM, lambda sig, __: handle_termination(sig))
    signal.signal(signal.SIGHUP, lambda sig, __: handle_restart(sig))

    while True:
        signal.pause()


type VerbosityLevel = Literal[1, 2, 3, 4, 5]
type NonVerbose = Literal[0]

VERBOSITY_TO_LOG_LEVEL: dict[VerbosityLevel, logconf.LogLevel] = {
    1: 'CRITICAL',
    2: 'ERROR',
    3: 'WARNING',
    4: 'INFO',
    5: 'DEBUG',
}


@cli.command
@from_model(GeneratorParameters)
@click.option(
    '-v',
    '--verbose',
    count=True,
    type=click.IntRange(0, 5),
    default=0,
    show_default=True,
    help=(
        'Level of verbosity for printed logs '
        '(default: disabled, -v: critical, -vv: errors, '
        '-vvv: warnings, -vvvv: info, -vvvvv: debug)'
    ),
)
@click.option(
    '--cryptfile',
    default=None,
    type=click.Path(exists=True, resolve_path=True),
    help='Path to keyring cryptfile',
)
def generate(
    generator_parameters: GeneratorParameters,
    verbose: NonVerbose | VerbosityLevel,
    cryptfile: str | None,
) -> None:
    """Generate events using single generator."""
    if verbose == 0:
        logconf.disable()
    else:
        logconf.use_stderr(level=VERBOSITY_TO_LOG_LEVEL[verbose])

    if cryptfile is not None:
        SECURITY_SETTINGS['cryptfile_location'] = Path(cryptfile)

    logger.info('Starting generator')
    generator = Generator(generator_parameters)
    status = generator.start()

    if not status:
        logger.error('Failed to start generator')
        sys.exit(1)

    def handle_termination(signal_num: int) -> NoReturn:
        logger.info(
            'Termination signal is received',
            signal=signal.Signals(signal_num).name,
        )
        generator.stop()
        sys.exit(128 + signal_num)

    signal.signal(signal.SIGINT, lambda sig, __: handle_termination(sig))
    signal.signal(signal.SIGTERM, lambda sig, __: handle_termination(sig))

    generator.join()
    sys.exit(0)


if __name__ == '__main__':
    cli()
