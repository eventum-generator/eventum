"""Construction paths for log files."""

from pathlib import Path
from typing import Literal, assert_never


def construct_channel_logfile_path(
    format: Literal['plain', 'json'],
    logs_dir: Path,
    channel: str,
) -> Path:
    """Construct log file path of a channel.

    Parameters
    ----------
    format : Literal['plain', 'json']
        Log format.

    logs_dir : Path
        Directory for log files.

    channel : str
        Channel name.

    Returns
    -------
    Path
        Filepath to the channel log file.

    """
    match format:
        case 'json':
            extension = 'json'
        case 'plain':
            extension = 'log'
        case f:
            assert_never(f)

    filename = f'{channel}.{extension}'

    return logs_dir / filename
