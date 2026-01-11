"""Exceptions."""

from eventum.exceptions import ContextualError


class ServiceBuildingError(ContextualError):
    """Error during building service."""
