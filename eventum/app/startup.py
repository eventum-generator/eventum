"""Operations over the application's startup file."""

from collections.abc import Iterable

import yaml
from pydantic import ValidationError

from eventum.app.models.generators import (
    StartupGeneratorParameters,
    StartupGeneratorParametersList,
)
from eventum.app.models.settings import Settings
from eventum.exceptions import ContextualError
from eventum.utils.validation_prettier import prettify_validation_errors


class StartupError(ContextualError):
    """Base error for startup file operations."""


class StartupFileError(StartupError):
    """Startup file cannot be read or written due to OS error."""


class StartupFormatError(StartupError):
    """Startup file content is malformed or does not validate."""


class StartupNotFoundError(StartupError):
    """Generator with provided id is not present in startup file."""


class StartupConflictError(StartupError):
    """Generator with provided id already exists in startup file."""


class Startup:
    """Entry point for CRUD over the startup file.

    All returned parameters have absolute paths (storage canonical
    form). Inputs may carry relative paths - they are normalized
    against `settings.path.generators_dir` before persistence.
    """

    def __init__(self, settings: Settings) -> None:
        """Initialize Startup.

        Parameters
        ----------
        settings : Settings
            Application settings. `settings.path.startup` locates the
            file; `settings.path.generators_dir` is the base for path
            normalization; `settings.generation` supplies defaults
            applied over each entry.

        """
        self._settings = settings

    def get_all(self) -> StartupGeneratorParametersList:
        """Read all entries.

        Returns
        -------
        StartupGeneratorParametersList
            All entries with defaults applied and paths normalized to
            absolute form.

        Raises
        ------
        StartupFileError
            If the file cannot be read.

        StartupFormatError
            If the file content is malformed or does not validate.

        """
        raw = self._read_raw()
        return self._validate(raw)

    def get(self, id: str) -> StartupGeneratorParameters:
        """Read a single entry by id.

        Parameters
        ----------
        id : str
            Generator id.

        Returns
        -------
        StartupGeneratorParameters
            Entry with defaults applied and path normalized to
            absolute.

        Raises
        ------
        StartupFileError
            If the file cannot be read.

        StartupFormatError
            If the file content is malformed or does not validate.

        StartupNotFoundError
            If no entry with the provided id exists.

        """
        for params in self.get_all().root:
            if params.id == id:
                return params

        msg = 'Generator with this ID is not defined'
        raise StartupNotFoundError(msg, context={'generator_id': id})

    def add(self, params: StartupGeneratorParameters) -> None:
        """Append a new entry.

        Parameters
        ----------
        params : StartupGeneratorParameters
            Entry to append. Path may be relative or absolute; it is
            normalized to absolute against
            `settings.path.generators_dir` before persistence.

        Raises
        ------
        StartupFileError
            If the file cannot be read or written.

        StartupFormatError
            If existing file content is malformed or does not validate.

        StartupConflictError
            If an entry with the same id already exists.

        """
        raw = self._read_raw()

        for entry in raw:
            if entry.get('id') == params.id:
                msg = 'Generator with this ID is already defined'
                raise StartupConflictError(
                    msg,
                    context={'generator_id': params.id},
                )

        raw.append(self._dump_entry(params))
        self._write_raw(raw)

    def update(
        self,
        id: str,
        params: StartupGeneratorParameters,
    ) -> None:
        """Replace an existing entry.

        Other entries are preserved byte-identically (their unset
        fields stay unset, key order is preserved).

        Parameters
        ----------
        id : str
            Id of the entry to replace.

        params : StartupGeneratorParameters
            New entry value. Path may be relative or absolute; it is
            normalized to absolute against
            `settings.path.generators_dir` before persistence.

        Raises
        ------
        StartupFileError
            If the file cannot be read or written.

        StartupFormatError
            If existing file content is malformed or does not validate.

        StartupNotFoundError
            If no entry with the provided id exists.

        """
        raw = self._read_raw()
        index = self._find_index(raw, id)
        raw[index] = self._dump_entry(params)
        self._write_raw(raw)

    def delete(self, id: str) -> None:
        """Remove an entry.

        Parameters
        ----------
        id : str
            Id of the entry to remove.

        Raises
        ------
        StartupFileError
            If the file cannot be read or written.

        StartupFormatError
            If existing file content is malformed or does not validate.

        StartupNotFoundError
            If no entry with the provided id exists.

        """
        raw = self._read_raw()
        index = self._find_index(raw, id)
        del raw[index]
        self._write_raw(raw)

    def bulk_delete(self, ids: Iterable[str]) -> list[str]:
        """Remove several entries.

        Parameters
        ----------
        ids : Iterable[str]
            Ids of entries to remove. Ids that do not match any entry
            are silently skipped.

        Returns
        -------
        list[str]
            Ids that were actually deleted, in the order they appeared
            in the file.

        Raises
        ------
        StartupFileError
            If the file cannot be read or written.

        StartupFormatError
            If existing file content is malformed or does not validate.

        """
        raw = self._read_raw()
        targets = set(ids)

        deleted: list[str] = []
        remaining: list[dict] = []
        for entry in raw:
            entry_id = entry.get('id')
            if entry_id in targets:
                deleted.append(entry_id)
            else:
                remaining.append(entry)

        self._write_raw(remaining)
        return deleted

    def _read_raw(self) -> list[dict]:
        """Read and parse the startup file into a list of dicts."""
        try:
            with self._settings.path.startup.open() as f:
                content = f.read()
        except OSError as e:
            msg = 'Failed to read startup file'
            raise StartupFileError(
                msg,
                context={
                    'file_path': str(self._settings.path.startup),
                    'reason': str(e),
                },
            ) from None

        try:
            parsed = yaml.load(content, Loader=yaml.SafeLoader)
        except yaml.error.YAMLError as e:
            msg = 'Failed to parse startup file'
            raise StartupFormatError(
                msg,
                context={
                    'file_path': str(self._settings.path.startup),
                    'reason': str(e),
                },
            ) from None

        if parsed is None:
            return []

        if not isinstance(parsed, list):
            msg = 'Startup file content is not a list'
            raise StartupFormatError(
                msg,
                context={
                    'file_path': str(self._settings.path.startup),
                },
            )

        return parsed

    def _write_raw(self, raw: list[dict]) -> None:
        """Serialize and write a list of dicts back to the file."""
        content = yaml.dump(raw, sort_keys=False)

        try:
            with self._settings.path.startup.open('w') as f:
                f.write(content)
        except OSError as e:
            msg = 'Failed to write startup file'
            raise StartupFileError(
                msg,
                context={
                    'file_path': str(self._settings.path.startup),
                    'reason': str(e),
                },
            ) from None

    def _validate(
        self,
        raw: list[dict],
    ) -> StartupGeneratorParametersList:
        """Validate raw content and normalize paths to absolute."""
        build = StartupGeneratorParametersList.build_over_generation_parameters
        try:
            params_list = build(
                object=raw,
                generation_parameters=self._settings.generation,
            )
        except ValidationError as e:
            msg = 'Startup file content is invalid'
            raise StartupFormatError(
                msg,
                context={
                    'file_path': str(self._settings.path.startup),
                    'reason': prettify_validation_errors(e.errors()),
                },
            ) from None

        normalized = tuple(
            params.as_absolute(base_dir=self._settings.path.generators_dir)
            for params in params_list.root
        )
        return StartupGeneratorParametersList(root=normalized)

    def _find_index(self, raw: list[dict], id: str) -> int:
        """Find the index of an entry by id."""
        for i, entry in enumerate(raw):
            if entry.get('id') == id:
                return i

        msg = 'Generator with this ID is not defined'
        raise StartupNotFoundError(msg, context={'generator_id': id})

    def _dump_entry(self, params: StartupGeneratorParameters) -> dict:
        """Serialize params to a dict with 'id' as the first key."""
        absolute = params.as_absolute(
            base_dir=self._settings.path.generators_dir,
        )
        data = absolute.model_dump(mode='json', exclude_unset=True)

        if 'id' in data:
            data = {'id': data.pop('id'), **data}

        return data
