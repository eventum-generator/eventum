"""Command for running Eventum as an MCP stdio server."""

from pathlib import Path
from typing import get_args

import click
import structlog

import eventum.logging.config as logconf

logger = structlog.stdlib.get_logger()

LOG_LEVELS = get_args(logconf.LogLevel.__value__)


@click.command('mcp')
@click.option(
    '--generators-dir',
    required=True,
    type=click.Path(exists=True, file_okay=False, resolve_path=True),
    help='Path to generators directory.',
)
@click.option(
    '--config-filename',
    default='generator.yml',
    show_default=True,
    help='Generator config filename inside each generator directory.',
)
@click.option(
    '--read-only',
    is_flag=True,
    default=False,
    help='Run in read-only mode (disable write tools).',
)
@click.option(
    '--log-level',
    type=click.Choice(LOG_LEVELS),
    default='WARNING',
    show_default=True,
    help='Level of logs emitted to stderr.',
)
@click.option(
    '--keyring-cryptfile',
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    default=None,
    help='Path to the keyring cryptfile that list_secret_names reads.',
)
def cli(
    generators_dir: str,
    config_filename: str,
    read_only: bool,  # noqa: FBT001
    log_level: logconf.LogLevel,
    keyring_cryptfile: str | None,
) -> None:
    """Run Eventum as a read-only or authoring MCP stdio server.

    Stdout is reserved exclusively for the MCP JSON-RPC stream; logs go
    to stderr at the chosen level and no splash screen is emitted.
    """
    # Stdout is the MCP JSON-RPC channel - route logs to stderr only.
    logconf.use_stderr(level=log_level)

    if keyring_cryptfile is not None:
        from eventum.security.manage import SECURITY_SETTINGS

        SECURITY_SETTINGS['cryptfile_location'] = Path(keyring_cryptfile)

    from eventum.mcp.context import FileAuthoringContext
    from eventum.mcp.server import build_server

    context = FileAuthoringContext(
        generators_dir=Path(generators_dir),
        read_only=read_only,
        config_filename=config_filename,
    )
    server = build_server(context)
    logger.info(
        'Starting MCP server',
        mcp_transport='stdio',
        read_only=read_only,
    )
    server.run(transport='stdio')
