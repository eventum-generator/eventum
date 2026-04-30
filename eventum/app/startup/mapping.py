"""Bidirectional translation between raw entries and typed models."""

from pathlib import Path

from flatten_dict import flatten, unflatten  # type: ignore[import-untyped]
from pydantic import ValidationError

from eventum.app.startup.models import (
    StartupGeneratorParameters,
    StartupGeneratorParametersList,
)
from eventum.core.parameters import GenerationParameters
from eventum.exceptions import ContextualError
from eventum.utils.validation_prettier import prettify_validation_errors


class RawEntriesValidationError(ContextualError):
    """Raw entries failed schema validation."""


class StartupEntryMapper:
    """Translation between raw entries (`list[dict]`) and typed models.

    Stateful only with configuration values (`generators_dir`,
    `generation_parameters`); never touches the file system.
    """

    def __init__(
        self,
        *,
        generators_dir: Path,
        generation_parameters: GenerationParameters,
    ) -> None:
        """Initialize StartupEntryMapper.

        Parameters
        ----------
        generators_dir : Path
            Base directory for normalizing relative generator paths.

        generation_parameters : GenerationParameters
            Defaults applied over each entry's unset fields.

        """
        self._generators_dir = generators_dir
        self._flat_defaults = flatten(
            generation_parameters.model_dump(),
            reducer='dot',
        )

    def parse(
        self,
        entries: list[dict],
    ) -> StartupGeneratorParametersList:
        """Validate raw entries; return them as typed models.

        Each entry is merged with `generation_parameters` defaults
        (entry values win over defaults), validated against the schema,
        and its path is normalized to absolute against
        `generators_dir`.

        Parameters
        ----------
        entries : list[dict]
            Raw entries (as parsed from YAML).

        Returns
        -------
        StartupGeneratorParametersList
            Validated entries with defaults applied and paths
            normalized to absolute.

        Raises
        ------
        RawEntriesValidationError
            If any entry fails Pydantic schema validation.

        """
        try:
            validated = [self._apply_defaults(entry) for entry in entries]
        except ValidationError as e:
            msg = 'Startup file fails schema validation'
            raise RawEntriesValidationError(
                msg,
                context={'reason': prettify_validation_errors(e.errors())},
            ) from None

        return StartupGeneratorParametersList(
            root=tuple(
                params.as_absolute(base_dir=self._generators_dir)
                for params in validated
            ),
        )

    def _apply_defaults(self, entry: dict) -> StartupGeneratorParameters:
        """Merge `entry` with cached defaults; validate as a model."""
        merged = unflatten(
            self._flat_defaults | flatten(entry, reducer='dot'),
            splitter='dot',
        )
        return StartupGeneratorParameters.model_validate(merged)

    def serialize(self, params: StartupGeneratorParameters) -> dict:
        """Serialize params to a raw entry with abs path and id-first.

        Parameters
        ----------
        params : StartupGeneratorParameters
            Entry to serialize. Path may be relative or absolute; it is
            normalized to absolute.

        Returns
        -------
        dict
            Raw entry suitable for storage. `id` is the first key;
            unset fields are omitted.

        """
        absolute = params.as_absolute(base_dir=self._generators_dir)
        data = absolute.model_dump(mode='json', exclude_unset=True)
        return {'id': data.pop('id'), **data}
