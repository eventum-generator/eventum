"""Custom handlers for logging system."""

import logging
from collections.abc import Callable, Hashable
from typing import override

from eventum.utils.lru_cache import LRUCache


class RoutingHandler(logging.Handler):
    """Handler that routes logs to different handlers based on value of
    specific log record attribute.
    """

    def __init__(
        self,
        attribute: str,
        handler_factory: Callable[[Hashable], logging.Handler],
        default_handler: logging.Handler,
        formatter: logging.Formatter,
        lru_size: int = 1024,
    ) -> None:
        """Initialize routing handler.

        Parameters
        ----------
        attribute : str
            Name of log record attribute to use for routing.

        handler_factory : Callable[[Hashable], logging.Handler]
            Factory for creating new handlers, new handler is created
            using factory for each unique value of specified log record
            attribute, attribute value is passed to factory function as
            single argument.

        default_handler : logging.Handler
            Handler that is used when log record attribute is missing,
            unhashable or any error occurs during usage of created
            handler.

        formatter: logging.Formatter
            Formatter that will be used for created handlers.

        lru_size : int, default=1024
            Number of dynamically created handlers to keep in lru cache.

        Raises
        ------
        ValueError
            If `lru_size` is less than 1.

        Notes
        -----
        The default handler is used when attribute value is unhashable
        or error occurred during creating new handler using provided
        factory.

        Provided formatter is used only for handlers created by
        `handler_factory`, but not for `default_handler`.

        """
        if lru_size < 1:
            msg = 'Parameter `lru_size` must be greater or equal to 1'
            raise ValueError(msg)

        super().__init__()

        self._attribute = attribute
        self._handler_factory = handler_factory
        self._default_handler = default_handler
        self._formatter = formatter

        self._handlers: LRUCache[str, logging.Handler] = LRUCache(
            maxsize=lru_size,
            on_evict=lambda _, handler: handler.close(),
        )

    @override
    def emit(self, record: logging.LogRecord) -> None:
        attr_value = getattr(record, self._attribute, None)

        if attr_value is None:
            self._default_handler.emit(record)
            return

        try:
            if attr_value in self._handlers:
                self._handlers[attr_value].emit(record)
            else:
                handler = self._handler_factory(attr_value)
                handler.setFormatter(self._formatter)
                self._handlers[attr_value] = handler

                handler.emit(record)
        except Exception:  # noqa: BLE001
            self._default_handler.emit(record)

    @override
    def close(self) -> None:
        self._default_handler.close()
        for handler in self._handlers.values():
            handler.close()

        super().close()
