"""Sample reader that provides unified interface for accessing samples
of different types.
"""

import random
from collections.abc import Callable, Iterable
from io import StringIO
from pathlib import Path
from typing import Any, Self

import structlog
import tablib  # type: ignore[import-untyped]
from tablib.exceptions import InvalidDimensions  # type: ignore[import-untyped]

from eventum.exceptions import ContextualError
from eventum.plugins.event.plugins.template.config import (
    CSVSampleConfig,
    ItemsSampleConfig,
    JSONSampleConfig,
    SampleConfig,
    SampleType,
)

logger = structlog.stdlib.get_logger()

_EMPTY_FIELD_MAP: dict[str, int] = {}


class SampleLoadError(ContextualError):
    """Failed to load sample."""


class SamplePickError(ContextualError):
    """Failed to pick from sample."""


class Row(tuple):  # noqa: SLOT001
    """Immutable sample row with named and index access."""

    def __new__(
        cls,
        values: Iterable[Any],
        field_map: dict[str, int] | None = None,
    ) -> Self:
        """Create a new row.

        Parameters
        ----------
        values : Iterable[Any]
            Row values.

        field_map : dict[str, int] | None, default=None
            Mapping of field names to indices for named
            access.

        """
        instance = super().__new__(cls, values)
        object.__setattr__(
            instance,
            '_field_map',
            field_map if field_map is not None
            else _EMPTY_FIELD_MAP,
        )
        return instance

    def __getattr__(self, name: str) -> Any:
        try:
            return self[self._field_map[name]]
        except KeyError:
            raise AttributeError(name) from None

    def __repr__(self) -> str:
        if self._field_map:
            pairs = ', '.join(
                f'{f}={self[i]!r}'
                for f, i in self._field_map.items()
            )
            return f'Row({pairs})'
        return f'Row({super().__repr__()})'


class Sample:
    """Immutable sample with picking support."""

    __slots__ = (
        '_cum_weights_cache',
        '_dataset',
        '_field_map',
        '_rows',
    )

    def __init__(self, dataset: tablib.Dataset) -> None:
        """Initialize sample.

        Parameters
        ----------
        dataset : tablib.Dataset
            Sample data.

        """
        self._dataset = dataset

        if dataset.headers:
            headers = dataset.headers
        else:
            headers = [
                f'_{i}' for i in range(dataset.width)
            ]

        self._field_map: dict[str, int] = (
            {name: i for i, name in enumerate(headers)}
            if headers
            else _EMPTY_FIELD_MAP
        )

        self._rows: tuple[Row, ...] = tuple(
            Row(dataset[i], self._field_map)
            for i in range(len(dataset))
        )

        self._cum_weights_cache: dict[
            str, list[float],
        ] = {}

    def __len__(self) -> int:
        return len(self._rows)

    def __getitem__(self, key: Any) -> Any:
        if isinstance(key, int):
            return self._rows[key]
        return self._dataset[key]

    def pick(self) -> Row:
        """Pick a random row (uniform)."""
        return random.choice(self._rows)

    def pick_n(self, n: int) -> list[Row]:
        """Pick n random rows (uniform, with replacement)."""
        return random.choices(self._rows, k=n)

    def weighted_pick(self, weight: str) -> Row:
        """Pick a random row weighted by the named column."""
        cum_weights = self._get_cum_weights(weight)
        return random.choices(
            self._rows,
            cum_weights=cum_weights,
            k=1,
        )[0]

    def weighted_pick_n(
        self, weight: str, n: int,
    ) -> list[Row]:
        """Pick n random rows weighted by the named column."""
        cum_weights = self._get_cum_weights(weight)
        return random.choices(
            self._rows,
            cum_weights=cum_weights,
            k=n,
        )

    def _get_cum_weights(
        self, column: str,
    ) -> list[float]:
        """Get cached cumulative weights for a column."""
        if column in self._cum_weights_cache:
            return self._cum_weights_cache[column]

        headers = self._dataset.headers
        if headers is None or column not in headers:
            msg = 'Weight column not found in sample'
            raise SamplePickError(
                msg,
                context={
                    'column': column,
                    'available_headers': (
                        list(headers) if headers else []
                    ),
                },
            )

        raw_weights = self._dataset[column]

        cum = 0.0
        cum_weights: list[float] = []
        for i, value in enumerate(raw_weights):
            try:
                w = float(value)
            except (TypeError, ValueError):
                msg = (
                    'Weight column contains '
                    'non-numeric value'
                )
                raise SamplePickError(
                    msg,
                    context={
                        'column': column,
                        'row': i,
                        'value': repr(value),
                    },
                ) from None

            if w < 0:
                msg = (
                    'Weight column contains '
                    'negative value'
                )
                raise SamplePickError(
                    msg,
                    context={
                        'column': column,
                        'row': i,
                        'value': repr(value),
                    },
                )
            cum += w
            cum_weights.append(cum)

        if cum == 0.0:
            msg = 'All weights are zero'
            raise SamplePickError(
                msg,
                context={'column': column},
            )

        self._cum_weights_cache[column] = cum_weights
        return cum_weights


def _load_items_sample(config: ItemsSampleConfig, _: Path) -> Sample:
    """Load sample using configuration of type `items`.

    Parameters
    ----------
    config: ItemsSampleConfig
        Sample configuration.

    base_path : Path
        Base path for resolving relative paths.

    Returns
    -------
    Sample
        Loaded sample.

    """
    data = tablib.Dataset()

    try:
        first_row = config.source[0]
    except IndexError:
        first_row = []

    if isinstance(first_row, Iterable) and not isinstance(first_row, str):
        data.extend(config.source)
    else:
        data.extend((item,) for item in config.source)

    return Sample(data)


def _load_csv_sample(config: CSVSampleConfig, base_path: Path) -> Sample:
    """Load sample using configuration of type `csv`.

    Parameters
    ----------
    config: CSVSampleConfig
        Sample configuration.

    base_path : Path
        Base path for resolving relative paths.

    Returns
    -------
    Sample
        Loaded sample.

    Raises
    ------
    Exception
        If some error occurs during sample loading.

    """
    data = tablib.Dataset()

    if config.source.is_absolute():
        resolved_path = config.source
    else:
        resolved_path = base_path / config.source

    with resolved_path.open() as f:
        try:
            data.load(
                in_stream=f,
                format='csv',
                headers=config.header,
                delimiter=config.delimiter,
                quotechar=config.quotechar,
            )
        except InvalidDimensions:
            hint = (
                'If values contain the delimiter character, '
                'wrap them in quotes per RFC 4180'
            )
            msg = 'CSV rows have inconsistent column counts'
            raise SampleLoadError(
                msg,
                context={
                    'file_path': str(resolved_path),
                    'hint': hint,
                },
            ) from None

        return Sample(data)


def _load_json_sample(config: JSONSampleConfig, base_path: Path) -> Sample:
    """Load sample using configuration of type `json`.

    Parameters
    ----------
    config: JSONSampleConfig
        Sample configuration.

    base_path : Path
        Base path for resolving relative paths.

    Returns
    -------
    Sample
        Loaded sample.

    Raises
    ------
    Exception
        If some error occurs during sample loading.

    """
    if config.source.is_absolute():
        resolved_path = config.source
    else:
        resolved_path = base_path / config.source

    with resolved_path.open() as f:
        content = f.read()

    data = tablib.Dataset()

    try:
        data.load(
            in_stream=StringIO(content),
            format='json',
        )
    except InvalidDimensions:
        msg = 'JSON sample objects have inconsistent keys'
        raise SampleLoadError(
            msg,
            context={'file_path': str(resolved_path)},
        ) from None

    return Sample(data)


def _get_sample_loader(
    sample_type: SampleType,
) -> Callable[[SampleConfig, Path], Sample]:
    """Get sample loader for specified sample type.

    Parameters
    ----------
    sample_type : SampleType
        Type of sample.

    Returns
    -------
    Callable[[SampleConfig, Path], Sample]
        Function for loading sample of specified type.

    Raises
    ------
    ValueError
        If no loader is registered for specified sample type.

    """
    try:
        return {
            SampleType.ITEMS: _load_items_sample,
            SampleType.CSV: _load_csv_sample,
            SampleType.JSON: _load_json_sample,
        }[sample_type]  # type: ignore[return-value]
    except KeyError as e:
        msg = f'No loader is available for sample type `{e}`'
        raise ValueError(msg) from e


class SamplesReader:
    """Samples reader."""

    def __init__(
        self,
        config: dict[str, SampleConfig],
        base_path: Path,
    ) -> None:
        """Initialize samples reader.

        Parameters
        ----------
        config : dict[str, SampleConfig]
            Sample names to their configurations mapping.

        base_path : Path
            Base path for resolving relative paths.

        Raises
        ------
        SampleLoadError
            If some error occurs during samples loading.

        """
        self._base_path = base_path
        self._samples = self._load_samples(config)

    def __getitem__(self, name: str) -> Sample:
        try:
            return self._samples[name]
        except KeyError as e:
            msg = f'No such sample `{e}`'
            raise KeyError(msg) from None

    def _load_samples(
        self,
        config: dict[str, SampleConfig],
    ) -> dict[str, Sample]:
        """Load samples specified in config.

        Parameters
        ----------
        config : dict[str, SampleConfig]
            Sample names to their configurations mapping.

        Returns
        -------
        dict[str, Sample]
            Sample names to their data mapping.

        Raises
        ------
        SampleLoadError
            If some error occurs during samples loading.

        """
        samples: dict[str, Sample] = {}

        for name, sample_config in config.items():
            logger.debug('Loading sample', sample_alias=name)
            loader = _get_sample_loader(sample_config.root.type)
            try:
                sample = loader(sample_config.root, self._base_path)  # type: ignore[arg-type]
            except SampleLoadError:
                raise
            except Exception as e:  # noqa: BLE001
                msg = 'Failed to load sample'
                raise SampleLoadError(
                    msg,
                    context={'sample_alias': name, 'reason': str(e)},
                ) from None

            samples[name] = sample

        return samples
