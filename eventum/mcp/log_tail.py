"""Bounded reading of log file tails for the log-reading tools."""

from pathlib import Path

DEFAULT_LOG_LINES = 200
MAX_LOG_LINES = 1000
TAIL_MAX_BYTES = 65536


def tail_lines(path: Path, count: int) -> list[str]:
    """Return the last lines of a file, reading a bounded tail.

    Parameters
    ----------
    path : Path
        File to read.

    count : int
        Number of trailing lines to return.

    Returns
    -------
    list[str]
        Up to `count` trailing lines.

    """
    size = path.stat().st_size
    read = min(size, TAIL_MAX_BYTES)
    with path.open('rb') as f:
        f.seek(size - read)
        data = f.read()

    lines = data.decode('utf-8', errors='replace').splitlines()

    if read < size and len(lines) > 1:
        # Drop the leading line - it is a partial cut from mid-file.
        # Keep it when it is the only line (one oversized line).
        lines = lines[1:]

    return lines[-count:]
