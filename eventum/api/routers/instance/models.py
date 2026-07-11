"""Models.

``InstanceInfo`` is defined in ``eventum.app.models.instance`` so it can
be shared with non-HTTP transports (e.g. the MCP service); it is
re-exported here as this router's response model.
"""

from eventum.app.models.instance import InstanceInfo

__all__ = ['InstanceInfo']
