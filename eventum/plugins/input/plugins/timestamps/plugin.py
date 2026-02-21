"""Definition of timestamps input plugin."""

from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import override

from numpy import array, astype, datetime64
from numpy.typing import NDArray

from eventum.plugins.exceptions import PluginConfigurationError
from eventum.plugins.input.base.plugin import InputPlugin, InputPluginParams
from eventum.plugins.input.plugins.timestamps.config import (
    TimestampsInputPluginConfig,
)
from eventum.plugins.input.utils.array_utils import get_future_slice
from eventum.plugins.input.utils.time_utils import now64, to_naive


class TimestampsInputPlugin(
    InputPlugin[TimestampsInputPluginConfig, InputPluginParams],
):
    """Input plugin for generating events at specified timestamps."""

    @override
    def __init__(
        self,
        config: TimestampsInputPluginConfig,
        params: InputPluginParams,
    ) -> None:
        super().__init__(config, params)

        if isinstance(config.source, Path):
            self._logger.debug(
                'Reading timestamps from the file',
                file_path=str(config.source),
            )
            timestamps: list[datetime] = [
                to_naive(ts, self._timezone)
                for ts in self._read_timestamps_from_file(
                    self.resolve_path(config.source),
                )
            ]
        else:
            self._logger.debug('Reading timestamps from configuration')
            timestamps = [to_naive(ts, self._timezone) for ts in config.source]

        if not timestamps:
            msg = 'Timestamps sequence is empty'
            if isinstance(config.source, list):
                context = {}
            else:
                context = {'file_path': str(config.source)}

            raise PluginConfigurationError(
                msg,
                context=context,
            )

        self._timestamps: NDArray[datetime64] = array(
            timestamps,
            dtype='datetime64[us]',
        )

    def _read_timestamps_from_file(self, filename: Path) -> list[datetime]:
        """Read timestamps from specified file.

        Parameters
        ----------
        filename : Path
            Path to file with timestamps that are delimited with new
            line.

        Returns
        -------
        list[datetime]
            List of datetime objects.

        Raises
        ------
        PluginConfigurationError
            If cannot read content of the specified file or parse
            timestamps.

        """
        try:
            with filename.open() as f:
                return [
                    datetime.fromisoformat(line.strip())
                    for line in f.readlines()
                    if line.strip()
                ]
        except (OSError, ValueError) as e:
            msg = 'Failed to read timestamps from file'
            raise PluginConfigurationError(
                msg,
                context={
                    'file_path': str(filename),
                    'reason': str(e),
                },
            ) from None

    @override
    def _generate(
        self,
        size: int,
        *,
        skip_past: bool = True,
    ) -> Iterator[NDArray[datetime64]]:
        start = astype(  # type: ignore[attr-defined]
            self._timestamps[0],
            datetime,  # type: ignore[arg-type]
        ).replace(tzinfo=self._timezone)
        end = astype(  # type: ignore[attr-defined]
            self._timestamps[-1],
            datetime,  # type: ignore[arg-type]
        ).replace(tzinfo=self._timezone)
        self._logger.debug(
            'Generating in range',
            start_timestamp=start.isoformat(),
            end_timestamp=end.isoformat(),
        )

        if skip_past:
            timestamps = get_future_slice(
                timestamps=self._timestamps,
                after=now64(timezone=self._timezone),
            )
        else:
            timestamps = self._timestamps

        self._buffer.mv_push(timestamps)
        yield from self._buffer.read(size, partial=True)
