"""Adapters for protocols defined in `protocols` module."""

from collections.abc import Iterator
from typing import override

import numpy as np

from eventum.plugins.input.base.plugin import InputPlugin
from eventum.plugins.input.protocols import (
    IdentifiedTimestamps,
    SupportsIdentifiedTimestampsSizedIterate,
)


class IdentifiedTimestampsPluginAdapter(
    SupportsIdentifiedTimestampsSizedIterate,
):
    """Adapter for input plugin to follow
    `SupportsIdentifiedTimestampsSizedIterate` protocol.
    """

    def __init__(self, plugin: InputPlugin) -> None:
        """Initialize adapter.

        Parameters
        ----------
        plugin : InputPlugin
            Input plugin to adapt.

        """
        self._plugin = plugin

    @override
    def iterate(
        self,
        size: int,
        *,
        skip_past: bool = True,
    ) -> Iterator[IdentifiedTimestamps]:
        if size < 1:
            msg = 'Parameter `size` must be greater or equal to 1'
            raise ValueError(msg)

        for array in self._plugin.generate(size=size, skip_past=skip_past):
            array_with_id: IdentifiedTimestamps = np.empty(
                shape=array.size,
                dtype=[('timestamp', 'datetime64[us]'), ('id', 'uint16')],
            )
            array_with_id['timestamp'][:] = array
            array_with_id['id'][:] = self._plugin.id

            yield array_with_id
