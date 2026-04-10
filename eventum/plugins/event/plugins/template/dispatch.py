"""Dispatch API for controlling event flow from templates."""

from typing import Never


class DispatchSignal(Exception):  # noqa: N818
    """Base signal for dispatch operations.

    Not raised directly -- use subclasses.
    """


class DispatchDropSignal(DispatchSignal):
    """Signal to drop the current event."""


class DispatchNextSignal(DispatchSignal):
    """Signal to discard rendered output and re-pick templates.

    Attributes
    ----------
    max_repicks : int
        Maximum number of re-pick iterations allowed.

    """

    def __init__(self, max_repicks: int) -> None:
        """Initialize signal with maximum re-pick count."""
        super().__init__()
        self.max_repicks = max_repicks


class DispatchExhaustSignal(DispatchSignal):
    """Signal that generation is complete."""


class Dispatcher:
    """Template dispatch API for controlling event flow.

    Injected into the Jinja2 environment as the ``dispatch``
    global. All methods raise :class:`DispatchSignal` subclasses
    and never return.
    """

    def drop(self) -> Never:
        """Drop the current event.

        Discards all rendered output for this timestamp.
        Remaining templates are not rendered. ``produce()``
        returns an empty list.
        """
        raise DispatchDropSignal

    def next(self, max_repicks: int = 64) -> Never:
        """Restart produce with a fresh pick.

        Discards all rendered output from this produce call and
        triggers a new pick. The picker decides what to render
        next based on its own logic.

        Parameters
        ----------
        max_repicks : int
            Maximum re-pick iterations. Raises
            ``PluginProduceError`` if exceeded. Default: 64.

        """
        if max_repicks < 1:
            msg = 'max_repicks must be >= 1'
            raise ValueError(msg)
        raise DispatchNextSignal(max_repicks=max_repicks)

    def exhaust(self) -> Never:
        """Signal that generation is complete.

        No more events will be produced. The generator shuts
        down gracefully.
        """
        raise DispatchExhaustSignal
