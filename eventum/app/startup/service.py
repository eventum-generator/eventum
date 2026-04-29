"""CRUD orchestration over the startup file."""

import threading
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from pathlib import Path

from eventum.app.startup.exceptions import (
    StartupConflictError,
    StartupError,
    StartupNotFoundError,
)
from eventum.app.startup.mapping import (
    RawEntriesValidationError,
    StartupEntryMapper,
)
from eventum.app.startup.models import (
    StartupGeneratorParameters,
    StartupGeneratorParametersList,
)
from eventum.app.startup.storage import StartupFile
from eventum.core.parameters import GenerationParameters


class Startup:
    """CRUD over the startup file.

    Owns a `StartupFile` and a `StartupEntryMapper` and serializes all
    public methods through a single `RLock`.

    Returned parameters always have absolute paths. Mutating methods
    refuse to touch a file that is currently invalid.
    """

    def __init__(
        self,
        *,
        file_path: Path,
        generators_dir: Path,
        generation_parameters: GenerationParameters,
    ) -> None:
        """Initialize Startup.

        Parameters
        ----------
        file_path : Path
            Location of the startup file.

        generators_dir : Path
            Base directory for normalizing relative generator paths.

        generation_parameters : GenerationParameters
            Defaults applied over each entry's unset fields.

        """
        self._file = StartupFile(file_path=file_path)
        self._mapper = StartupEntryMapper(
            generators_dir=generators_dir,
            generation_parameters=generation_parameters,
        )
        self._lock = threading.RLock()

    def get_all(self) -> StartupGeneratorParametersList:
        """Read all entries.

        Returns
        -------
        StartupGeneratorParametersList
            All entries with defaults applied and paths normalized to
            absolute form.

        Raises
        ------
        StartupError
            If the file cannot be read, parsed, or validated.

        """
        with self._lock:
            return self._parse(self._file.read())

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
        StartupError
            If the file cannot be read, parsed, or validated.

        StartupNotFoundError
            If no entry with the provided id exists.

        """
        with self._lock:
            for params in self._parse(self._file.read()).root:
                if params.id == id:
                    return params

            raise self._build_not_found_error(id)

    def add(self, params: StartupGeneratorParameters) -> None:
        """Append a new entry.

        Parameters
        ----------
        params : StartupGeneratorParameters
            Entry to append. Path may be relative or absolute; it is
            normalized to absolute before persistence.

        Raises
        ------
        StartupError
            If the file cannot be read, parsed, validated, or written.

        StartupConflictError
            If an entry with the same id already exists.

        """
        with self._mutating() as raw:
            if self._find_index(raw, params.id) is not None:
                raise self._build_conflict_error(params.id)
            raw.append(self._mapper.serialize(params))

    def update(self, params: StartupGeneratorParameters) -> None:
        """Replace an existing entry.

        Other entries are preserved as-read: their fields, values,
        and key order are passed through unchanged. The replaced
        entry is re-serialized so its unset fields are omitted from
        storage.

        Parameters
        ----------
        params : StartupGeneratorParameters
            New entry value.

        Raises
        ------
        StartupError
            If the file cannot be read, parsed, validated, or written.

        StartupNotFoundError
            If no entry with `params.id` exists.

        """
        with self._mutating() as raw:
            index = self._require_index(raw, params.id)
            raw[index] = self._mapper.serialize(params)

    def delete(self, id: str) -> None:
        """Remove an entry.

        Parameters
        ----------
        id : str
            Id of the entry to remove.

        Raises
        ------
        StartupError
            If the file cannot be read, parsed, validated, or written.

        StartupNotFoundError
            If no entry with the provided id exists.

        """
        with self._mutating() as raw:
            del raw[self._require_index(raw, id)]

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
        StartupError
            If the file cannot be read, parsed, validated, or written.

        """
        targets = set(ids)
        with self._mutating() as raw:
            deleted = [entry['id'] for entry in raw if entry['id'] in targets]
            raw[:] = [entry for entry in raw if entry['id'] not in targets]
            return deleted

    @contextmanager
    def _mutating(self) -> Iterator[list[dict]]:
        """Read, validate, yield raw entries, atomically write on exit.

        Mutate the yielded list IN PLACE: `append`, `__setitem__`,
        `del`, slice assignment (`raw[:] = ...`). Reassigning the local
        name has no effect on the persisted state.

        On exception inside the `with` block, no write happens and the
        file is unchanged.
        """
        with self._lock:
            raw = self._file.read()
            self._parse(raw)  # validate; typed result discarded
            yield raw
            self._file.write(raw)

    def _parse(self, raw: list[dict]) -> StartupGeneratorParametersList:
        """Validate raw entries and return them as typed models."""
        try:
            return self._mapper.parse(raw)
        except RawEntriesValidationError as e:
            raise StartupError(
                str(e),
                context={**e.context, 'file_path': str(self._file.path)},
            ) from None

    @staticmethod
    def _find_index(entries: list[dict], id: str) -> int | None:
        """Return index of entry with matching id, or None."""
        for i, entry in enumerate(entries):
            if entry['id'] == id:
                return i
        return None

    def _require_index(self, entries: list[dict], id: str) -> int:
        """Return index of entry with matching id; raise if missing."""
        index = self._find_index(entries, id)
        if index is None:
            raise self._build_not_found_error(id)
        return index

    @staticmethod
    def _build_not_found_error(id: str) -> StartupNotFoundError:
        """Build a StartupNotFoundError for the given id."""
        msg = 'Generator is not present in the startup file'
        return StartupNotFoundError(msg, context={'value': id})

    @staticmethod
    def _build_conflict_error(id: str) -> StartupConflictError:
        """Build a StartupConflictError for the given id."""
        msg = 'Generator is already present in the startup file'
        return StartupConflictError(msg, context={'value': id})
