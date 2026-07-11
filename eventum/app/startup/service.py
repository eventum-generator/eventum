"""CRUD orchestration over the startup file."""

import threading
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from pathlib import Path

from eventum.app.startup.exceptions import (
    ScenarioConflictError,
    ScenarioNotFoundError,
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

    def list_scenarios(self) -> list[str]:
        """List the distinct scenario names across all entries.

        Returns
        -------
        list[str]
            Sorted, de-duplicated scenario names.

        Raises
        ------
        StartupError
            If the file cannot be read, parsed, or validated.

        """
        with self._lock:
            params_list = self._parse(self._file.read())

        names: set[str] = set()
        for params in params_list.root:
            names.update(params.scenarios)
        return sorted(names)

    def get_scenario_generators(self, scenario: str) -> list[str]:
        """List ids of generators tagged with a scenario, in file order.

        Parameters
        ----------
        scenario : str
            Scenario name.

        Returns
        -------
        list[str]
            Ids of generators carrying the tag; empty if none do.

        Raises
        ------
        StartupError
            If the file cannot be read, parsed, or validated.

        """
        with self._lock:
            params_list = self._parse(self._file.read())

        return [
            params.id
            for params in params_list.root
            if scenario in params.scenarios
        ]

    def tag_scenario(self, id: str, scenario: str) -> None:
        """Add a scenario tag to one generator entry.

        Parameters
        ----------
        id : str
            Generator id to tag.

        scenario : str
            Scenario name to add.

        Raises
        ------
        StartupError
            If the file cannot be read, parsed, validated, or written.

        StartupNotFoundError
            If no entry with the provided id exists.

        ScenarioConflictError
            If the entry already carries the tag.

        """
        with self._mutating() as raw:
            entry = raw[self._require_index(raw, id)]
            scenarios = entry.get('scenarios', [])
            if scenario in scenarios:
                raise self._build_scenario_conflict_error(id, scenario)
            scenarios.append(scenario)
            entry['scenarios'] = scenarios

    def untag_scenario(self, id: str, scenario: str) -> None:
        """Remove a scenario tag from one generator entry.

        Parameters
        ----------
        id : str
            Generator id to untag.

        scenario : str
            Scenario name to remove.

        Raises
        ------
        StartupError
            If the file cannot be read, parsed, validated, or written.

        ScenarioNotFoundError
            If the entry does not exist or does not carry the tag.

        """
        with self._mutating() as raw:
            index = self._find_index(raw, id)
            entry = raw[index] if index is not None else None
            if entry is None or scenario not in entry.get('scenarios', []):
                raise self._build_membership_not_found_error(id, scenario)
            self._drop_scenario(entry, scenario)

    def delete_scenario(self, scenario: str) -> list[str]:
        """Remove a scenario tag from every entry that carries it.

        Parameters
        ----------
        scenario : str
            Scenario name to remove everywhere.

        Returns
        -------
        list[str]
            Ids of generators that were untagged, in file order.

        Raises
        ------
        StartupError
            If the file cannot be read, parsed, validated, or written.

        ScenarioNotFoundError
            If no entry carries the tag.

        """
        with self._mutating() as raw:
            affected: list[str] = []
            for entry in raw:
                if scenario in entry.get('scenarios', []):
                    affected.append(entry['id'])
                    self._drop_scenario(entry, scenario)

            # Raising discards the in-place edits: _mutating skips the
            # write when the block raises.
            if not affected:
                raise self._build_scenario_not_found_error(scenario)
            return affected

    @staticmethod
    def _drop_scenario(entry: dict, scenario: str) -> None:
        """Remove a scenario from a raw entry, dropping an empty list."""
        remaining = [s for s in entry.get('scenarios', []) if s != scenario]
        if remaining:
            entry['scenarios'] = remaining
        else:
            entry.pop('scenarios', None)

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

    @staticmethod
    def _build_scenario_conflict_error(
        id: str, scenario: str
    ) -> ScenarioConflictError:
        """Build a ScenarioConflictError for an already-tagged entry."""
        msg = 'Generator already belongs to this scenario'
        return ScenarioConflictError(
            msg, context={'value': id, 'name': scenario}
        )

    @staticmethod
    def _build_membership_not_found_error(
        id: str, scenario: str
    ) -> ScenarioNotFoundError:
        """Build a ScenarioNotFoundError for a missing membership."""
        msg = 'Generator does not belong to this scenario'
        return ScenarioNotFoundError(
            msg, context={'value': id, 'name': scenario}
        )

    @staticmethod
    def _build_scenario_not_found_error(
        scenario: str,
    ) -> ScenarioNotFoundError:
        """Build a ScenarioNotFoundError for an absent scenario."""
        msg = 'Scenario is not present in the startup file'
        return ScenarioNotFoundError(msg, context={'name': scenario})
