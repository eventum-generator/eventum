"""LRU cache with eviction callback."""

from collections import OrderedDict
from collections.abc import Callable, Hashable


class LRUCache[K: Hashable, V](OrderedDict[K, V]):
    """Least-recently-used cache with eviction callback.

    When the cache exceeds ``maxsize``, the least-recently-used entry
    is evicted and ``on_evict`` is called with the evicted key and value.

    Parameters
    ----------
    maxsize : int
        Maximum number of entries to keep.

    on_evict : Callable[[K, V], object] | None
        Optional callback invoked with ``(key, value)`` when an entry
        is evicted.

    Raises
    ------
    ValueError
        If ``maxsize`` is less than 1.

    """

    def __init__(
        self,
        maxsize: int,
        on_evict: Callable[[K, V], object] | None = None,
    ) -> None:
        """Initialize LRU cache.

        Parameters
        ----------
        maxsize : int
            Maximum number of entries to keep.

        on_evict : Callable[[K, V], object] | None
            Optional callback invoked with ``(key, value)`` when an
            entry is evicted.

        Raises
        ------
        ValueError
            If ``maxsize`` is less than 1.

        """
        super().__init__()

        if maxsize < 1:
            msg = 'Parameter `maxsize` must be greater or equal to 1'
            raise ValueError(msg)

        self._maxsize = maxsize
        self._on_evict = on_evict

    @property
    def maxsize(self) -> int:
        """Maximum number of entries."""
        return self._maxsize

    def __getitem__(self, key: K) -> V:
        self.move_to_end(key)
        return super().__getitem__(key)

    def __setitem__(self, key: K, value: V) -> None:
        if key in self:
            self.move_to_end(key)

        super().__setitem__(key, value)

        if len(self) > self._maxsize:
            evicted_key, evicted_value = self.popitem(last=False)

            if self._on_evict is not None:
                self._on_evict(evicted_key, evicted_value)
