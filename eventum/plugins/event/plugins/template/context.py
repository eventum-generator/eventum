"""Context of event producing."""

from datetime import datetime
from typing import TypedDict

from eventum.plugins.event.state import State


class BaseEventContext(TypedDict):
    """Base event context."""


class EventTimestampContext(BaseEventContext):
    """Context for event producing containing timestamp info.

    Attributes
    ----------
    timestamp : datetime
        Timestamp of event.

    """

    timestamp: datetime


class EventTagsContext(BaseEventContext):
    """Context for event producing containing tags info.

    Attributes
    ----------
    tags : tuple[str, ...]
        Tags from input plugin that generated timestamp.

    """

    tags: tuple[str, ...]


class EventStateContext(BaseEventContext):
    """Context for event producing containing state info.

    Attributes
    ----------
    locals : State
        Local state of template.

    shared : State
        Shared state of templates.

    globals : State
        Global state shared with all generators in the process.

    """

    locals: State
    shared: State
    globals: State


class EventContext(EventTimestampContext, EventTagsContext, EventStateContext):
    """Context for event producing.

    Notes
    -----
    To see attributes description check base classes.

    """
