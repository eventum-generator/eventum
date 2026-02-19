"""Construction paths for log files."""

from pathlib import Path
from typing import Literal, assert_never


def construct_generator_logfile_path(
    format: Literal['plain', 'json'],
    logs_dir: Path,
    generator_id: str,
) -> Path:
    """Construct generator log file path.

    Parameters
    ----------
    format : Literal['plain', 'json']
        Log format.

    logs_dir : Path
        Directory for log files.

    generator_id : str
        Generator ID.

    Returns
    -------
    Path
        Filepath to generator log file.

    """
    match format:
        case 'json':
            extension = 'json'
        case 'plain':
            extension = 'log'
        case f:
            assert_never(f)

    filename = f'generator_{generator_id}.{extension}'

    return logs_dir / filename


def construct_main_logfile_path(
    format: Literal['plain', 'json'],
    logs_dir: Path,
) -> Path:
    """Construct main log file path.

    Parameters
    ----------
    format : Literal['plain', 'json']
        Log format.

    logs_dir : Path
        Directory for log files.

    Returns
    -------
    Path
        Filepath to main log file.

    """
    match format:
        case 'json':
            extension = 'json'
        case 'plain':
            extension = 'log'
        case f:
            assert_never(f)

    filename = f'main.{extension}'

    return logs_dir / filename


def construct_server_logfile_path(
    logs_dir: Path,
    log_type: Literal['access', 'error'],
) -> Path:
    """Construct server log file path.

    Parameters
    ----------
    logs_dir : Path
        Directory for log files.

    log_type : Literal['access', 'error']
        Server log type.

    Returns
    -------
    Path
        Filepath to api log file.

    """
    filename = f'server_{log_type}.log'

    return logs_dir / filename
