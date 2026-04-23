"""CRUD over the application's startup file.

The startup file (located at `settings.path.startup`, shipped as
`config/startup.yml`) lists the generators the app loads on boot:
each entry is a `StartupGeneratorParameters` model (generator id,
path to its config, autostart flag, generation overrides). This
module is the single entry point for reading and mutating that list
and is shared by `App.start()` and the HTTP API.

Storage convention: generator paths are stored absolute. Inputs may
carry relative paths; the module normalizes them against
`settings.path.generators_dir` before persistence.
"""

from collections.abc import Iterable

import yaml
from pydantic import ValidationError

from eventum.app.models.settings import Settings
from eventum.app.models.startup import (
    StartupGeneratorParameters,
    StartupGeneratorParametersList,
)
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
    form). Mutating methods validate the whole file before writing
    and refuse to touch a currently-invalid file.
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
        return self._validate(self._read_raw())

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
        raise StartupNotFoundError(msg, context={'value': id})

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
            If the current file content is malformed or does not
            validate.

        StartupConflictError
            If an entry with the same id already exists.

        """
        raw = self._read_and_validate()

        if self._find_index_or_none(raw, params.id) is not None:
            msg = 'Generator with this ID is already defined'
            raise StartupConflictError(msg, context={'value': params.id})

        raw.append(self._dump_entry(params))
        self._write_raw(raw)

    def update(self, params: StartupGeneratorParameters) -> None:
        """Replace an existing entry.

        The entry identified by `params.id` is replaced. Other entries
        are preserved byte-identically (their unset fields stay unset,
        key order preserved).

        Parameters
        ----------
        params : StartupGeneratorParameters
            New entry value. Path may be relative or absolute; it is
            normalized to absolute against
            `settings.path.generators_dir` before persistence.

        Raises
        ------
        StartupFileError
            If the file cannot be read or written.

        StartupFormatError
            If the current file content is malformed or does not
            validate.

        StartupNotFoundError
            If no entry with `params.id` exists.

        """
        raw = self._read_and_validate()
        raw[self._find_index(raw, params.id)] = self._dump_entry(params)
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
            If the current file content is malformed or does not
            validate.

        StartupNotFoundError
            If no entry with the provided id exists.

        """
        raw = self._read_and_validate()
        del raw[self._find_index(raw, id)]
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
            If the current file content is malformed or does not
            validate.

        """
        raw = self._read_and_validate()
        targets = set(ids)

        deleted: list[str] = []
        remaining: list[dict] = []
        for entry in raw:
            if entry['id'] in targets:
                deleted.append(entry['id'])
            else:
                remaining.append(entry)

        self._write_raw(remaining)
        return deleted

    def _read_and_validate(self) -> list[dict]:
        """Read raw content and raise if it fails validation."""
        raw = self._read_raw()
        self._validate(raw)
        return raw

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
                context={'file_path': str(self._settings.path.startup)},
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

        return StartupGeneratorParametersList(
            root=tuple(
                params.as_absolute(base_dir=self._settings.path.generators_dir)
                for params in params_list.root
            ),
        )

    @staticmethod
    def _find_index_or_none(raw: list[dict], id: str) -> int | None:
        """Return index of entry with matching id, or None."""
        for i, entry in enumerate(raw):
            if entry['id'] == id:
                return i
        return None

    def _find_index(self, raw: list[dict], id: str) -> int:
        """Return index of entry with matching id, raise if absent."""
        index = self._find_index_or_none(raw, id)
        if index is None:
            msg = 'Generator with this ID is not defined'
            raise StartupNotFoundError(msg, context={'value': id})
        return index

    def _dump_entry(self, params: StartupGeneratorParameters) -> dict:
        """Serialize params to a dict with 'id' as the first key."""
        absolute = params.as_absolute(
            base_dir=self._settings.path.generators_dir,
        )
        data = absolute.model_dump(mode='json', exclude_unset=True)
        return {'id': data.pop('id'), **data}
