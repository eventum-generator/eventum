"""Logging parameters."""

from typing import Literal

from pydantic import BaseModel, Field


class LogParameters(BaseModel, extra='forbid', frozen=True):
    """Log parameters.

    Attributes
    ----------
    level : Literal['debug', 'info', 'warning', 'error', 'critical'],\
        default='info'
        Logging level.

    third_party_level : Literal['debug', 'info', 'warning', 'error',\
        'critical'], default='warning'
        Logging level of third-party libraries.

    format : Literal['plain', 'json'], default='plain'
        Logging format.

    max_bytes : int, default=10485760
        Max bytes for log file before rotation.

    backups : int, default=5
        Number of rotated log files to keep.

    """

    level: Literal['debug', 'info', 'warning', 'error', 'critical'] = 'info'
    third_party_level: Literal[
        'debug',
        'info',
        'warning',
        'error',
        'critical',
    ] = 'warning'
    format: Literal['plain', 'json'] = 'plain'
    max_bytes: int = Field(default=10 * 1024 * 1024, ge=1024)  # 10MiB
    backups: int = Field(default=5, ge=1)
