"""Sample reader that provides unified interface for accessing samples
of different types.
"""

from collections import namedtuple
from collections.abc import Callable, Iterable
from io import StringIO
from pathlib import Path
from typing import Any

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


class SampleLoadError(ContextualError):
    """Failed to load sample."""


class Sample:
    """Immutable sample."""

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
            headers = [f'_{i}' for i in range(dataset.width)]

        if headers:
            self._row_type: type[tuple] | None = namedtuple(  # type: ignore[misc] # noqa: PYI024
                'Row',
                headers,
                rename=True,
            )
        else:
            self._row_type = None

    def __len__(self) -> int:
        return len(self._dataset)

    def __getitem__(self, key: Any) -> list | tuple:
        result = self._dataset[key]

        if self._row_type is not None and isinstance(result, tuple):
            return self._row_type(*result)

        return result


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
        data.load(
            in_stream=f,
            format='csv',
            headers=config.header,
            delimiter=config.delimiter,
        )
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
