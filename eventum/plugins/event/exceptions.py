"""Event plugin exceptions."""

from eventum.plugins.exceptions import PluginError


class PluginProduceSignal(Exception):  # noqa: N818
    """Base for non-error control flow signals from event plugins."""


class PluginExhaustedError(PluginProduceSignal):
    """No more events can be produced by event plugin."""


class PluginEventDroppedError(PluginProduceSignal):
    """Event was intentionally dropped by event plugin."""


class PluginProduceError(PluginError):
    """Event cannot be produced."""
