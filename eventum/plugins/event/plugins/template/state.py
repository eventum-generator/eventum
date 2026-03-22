"""States that provide preserving and sharing template variables across
template renders, different templates and generators.
"""

from abc import ABC, abstractmethod
from copy import copy
from threading import RLock
from typing import Any, override


class State(ABC):
    """Base key-value state."""

    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """Get value from state.

        Parameters
        ----------
        key : str
            Key of the value to get.

        default : Any, default=None
            Default value to return if there is no value in state with
            specified key.

        Returns
        -------
        Any
            Value from the state, or default value if there is no value
            in state with specified key.

        """
        ...

    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        """Set value to state.

        Parameters
        ----------
        key : str
            Key of the value to set.

        value : Any
            Value to set.

        """
        ...

    @abstractmethod
    def update(self, m: dict[str, Any], /) -> None:
        """Update state with new values.

        Parameters
        ----------
        m: dict[str, Any]
            Values to update state with.

        """

    @abstractmethod
    def pop(self, key: str, default: Any = None) -> Any:
        """Remove and return value from state.

        Parameters
        ----------
        key : str
            Key of the value to remove.

        default : Any, default=None
            Default value to return if there is no value in state with
            specified key.

        Returns
        -------
        Any
            Removed value, or default value if there is no value in state
            with specified key.

        """
        ...

    @abstractmethod
    def clear(self) -> None:
        """Clear state."""
        ...

    @abstractmethod
    def as_dict(self) -> dict[str, Any]:
        """Get dictionary representation of state."""
        ...

    @abstractmethod
    def __getitem__(self, key: Any) -> Any: ...


class SingleThreadState(State):
    """Key-value state for single thread."""

    def __init__(self, initial: dict[str, Any] | None = None) -> None:
        """Initialize state.

        Parameters
        ----------
        initial : dict[str, Any] | None = None
            Initial state.

        """
        self._state: dict[str, Any] = initial or {}

    @override
    def get(self, key: str, default: Any | None = None) -> Any:
        return self._state.get(key, default)

    @override
    def set(self, key: str, value: Any) -> None:
        self._state[key] = value

    @override
    def update(self, m: dict[str, Any], /) -> None:
        self._state.update(m)

    @override
    def pop(self, key: str, default: Any = None) -> Any:
        return self._state.pop(key, default)

    @override
    def clear(self) -> None:
        self._state.clear()

    @override
    def as_dict(self) -> dict[str, Any]:
        return copy(self._state)

    @override
    def __getitem__(self, key: Any) -> Any:
        return self.get(key)


class MultiThreadState(State):
    """Thread-safe key-value state."""

    def __init__(
        self,
        lock: RLock,
        initial: dict[str, Any] | None = None,
    ) -> None:
        """Initialize state.

        Parameters
        ----------
        lock: RLock
            Lock to use for inclusive access.

        initial : dict[str, Any] | None = None
            Initial state.

        """
        self._lock = lock

        self._state: dict[str, Any] = initial or {}
        self._state_to_update: dict[str, Any] = {}

    @override
    def get(self, key: str, default: Any | None = None) -> Any:
        with self._lock:
            return self._state.get(key, default)

    @override
    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._state[key] = value

    @override
    def update(self, m: dict[str, Any], /) -> None:
        with self._lock:
            self._state.update(m)

    def pop(self, key: str, default: Any = None) -> Any:
        """Remove and return value from state.

        Parameters
        ----------
        key : str
            Key of the value to remove.

        default : Any, default=None
            Default value to return if there is no value in state with
            specified key.

        Returns
        -------
        Any
            Removed value, or default value if there is no value in state
            with specified key.

        """
        with self._lock:
            return self._state.pop(key, default)

    @override
    def clear(self) -> None:
        with self._lock:
            self._state.clear()

    @override
    def as_dict(self) -> dict[str, Any]:
        with self._lock:
            return copy(self._state)

    def acquire(self) -> None:
        """Acquire state lock."""
        self._lock.acquire()

    def release(self) -> None:
        """Release state lock."""
        self._lock.release()

    @override
    def __getitem__(self, key: Any) -> Any:
        with self._lock:
            return self.get(key)
