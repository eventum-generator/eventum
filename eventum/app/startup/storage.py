"""Low-level YAML file I/O for the startup file."""

from pathlib import Path
from typing import Any

import yaml

from eventum.app.startup.exceptions import StartupError


class StartupFile:
    """Reads and writes raw entries to/from the startup YAML file.

    Pure I/O over `list[dict]`. Knows nothing about schema, defaults,
    or paths inside entries; knows nothing about concurrency - the
    service layer is responsible for serializing access.

    Errors raised here always carry `file_path` in the context.
    """

    def __init__(self, *, file_path: Path) -> None:
        """Initialize StartupFile.

        Parameters
        ----------
        file_path : Path
            Location of the startup YAML file.

        """
        self._file_path = file_path

    @property
    def path(self) -> Path:
        """Location of the startup file."""
        return self._file_path

    def read(self) -> list[dict]:
        """Read the file and return its content as a list of dicts.

        Returns
        -------
        list[dict]
            File content as a list of raw entries. Empty file returns
            an empty list.

        Raises
        ------
        StartupError
            If the file cannot be read, decoded, parsed, or its
            top-level value is not a YAML list.

        """
        return self._parse(self._read_text())

    def write(self, entries: list[dict]) -> None:
        """Atomically replace the file content with `entries`.

        Writes go through a sibling tempfile and `Path.replace`. If
        the file is a symlink, the link target is replaced so the
        symlink itself stays intact. On failure the tempfile is
        removed and the original file is unchanged.

        Parameters
        ----------
        entries : list[dict]
            Entries to persist.

        Raises
        ------
        StartupError
            If the file cannot be written.

        """
        content = yaml.dump(entries, sort_keys=False)
        target = (
            self._file_path.resolve()
            if self._file_path.is_symlink()
            else self._file_path
        )
        tmp_path = target.with_suffix(target.suffix + '.tmp')
        try:
            tmp_path.write_text(content)
            tmp_path.replace(target)
        except OSError as e:
            tmp_path.unlink(missing_ok=True)
            msg = 'Cannot write startup file'
            raise self._build_error(msg, reason=str(e)) from None

    def _read_text(self) -> str:
        try:
            return self._file_path.read_text()
        except OSError as e:
            msg = 'Cannot read startup file'
            raise self._build_error(msg, reason=str(e)) from None
        except UnicodeDecodeError as e:
            msg = 'Startup file is not valid UTF-8'
            raise self._build_error(msg, reason=str(e)) from None

    def _parse(self, content: str) -> list[dict]:
        try:
            parsed = yaml.safe_load(content)
        except yaml.YAMLError as e:
            msg = 'Startup file is not valid YAML'
            raise self._build_error(msg, reason=str(e)) from None

        if parsed is None:
            return []

        if not isinstance(parsed, list):
            msg = 'Startup file root is not a YAML list'
            raise self._build_error(msg)

        return parsed

    def _build_error(
        self,
        message: str,
        *,
        reason: str | None = None,
    ) -> StartupError:
        """Build a StartupError carrying the file path (and reason)."""
        context: dict[str, Any] = {'file_path': str(self._file_path)}
        if reason is not None:
            context['reason'] = reason
        return StartupError(message, context=context)
