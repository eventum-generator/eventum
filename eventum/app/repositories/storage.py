"""Low-level YAML file I/O for the repositories file."""

from pathlib import Path
from typing import Any

import yaml

from eventum.app.repositories.exceptions import RepositoryError


class RepositoriesFile:
    """Reads and writes raw entries to/from the repositories file.

    Pure I/O over `list[dict]`. Knows nothing about the schema of an
    entry; knows nothing about concurrency - the service layer is
    responsible for serializing access.

    Errors raised here always carry `file_path` in the context.
    """

    def __init__(self, *, file_path: Path) -> None:
        """Initialize RepositoriesFile.

        Parameters
        ----------
        file_path : Path
            Location of the repositories YAML file.

        """
        self._file_path = file_path

    @property
    def path(self) -> Path:
        """Location of the repositories file."""
        return self._file_path

    def read(self) -> list[dict]:
        """Read the file and return its content as a list of dicts.

        A missing file reads as an empty list: an instance that never
        connected a repository has no file to keep.

        Returns
        -------
        list[dict]
            File content as a list of raw entries.

        Raises
        ------
        RepositoryError
            If the file cannot be read, decoded, parsed, or its
            top-level value is not a YAML list.

        """
        if not self._file_path.exists():
            return []

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
        RepositoryError
            If the file cannot be written.

        """
        content = yaml.dump(entries, sort_keys=False, allow_unicode=True)
        target = (
            self._file_path.resolve()
            if self._file_path.is_symlink()
            else self._file_path
        )
        tmp_path = target.with_suffix(target.suffix + '.tmp')
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            tmp_path.write_text(content, encoding='utf-8')
            tmp_path.replace(target)
        except OSError as e:
            tmp_path.unlink(missing_ok=True)
            msg = 'Cannot write repositories file'
            raise self._build_error(msg, reason=str(e)) from None

    def _read_text(self) -> str:
        try:
            return self._file_path.read_text(encoding='utf-8')
        except OSError as e:
            msg = 'Cannot read repositories file'
            raise self._build_error(msg, reason=str(e)) from None
        except UnicodeDecodeError as e:
            msg = 'Repositories file is not valid UTF-8'
            raise self._build_error(msg, reason=str(e)) from None

    def _parse(self, content: str) -> list[dict]:
        try:
            parsed = yaml.safe_load(content)
        except yaml.YAMLError as e:
            msg = 'Repositories file is not valid YAML'
            raise self._build_error(msg, reason=str(e)) from None

        if parsed is None:
            return []

        if not isinstance(parsed, list):
            msg = 'Repositories file root is not a YAML list'
            raise self._build_error(msg)

        return parsed

    def _build_error(
        self,
        message: str,
        *,
        reason: str | None = None,
    ) -> RepositoryError:
        """Build a RepositoryError carrying the file path (and reason)."""
        context: dict[str, Any] = {'file_path': str(self._file_path)}
        if reason is not None:
            context['reason'] = reason
        return RepositoryError(message, context=context)
