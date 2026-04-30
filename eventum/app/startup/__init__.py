"""CRUD over the startup file.

The startup file is a YAML list of `StartupGeneratorParameters`
entries: per-generator id, path to its config, autostart flag, and
overrides over the default generation parameters. The file location
and the base directory for relative-path resolution are passed to
`Startup` at construction.

Storage convention: generator paths are stored absolute. Inputs may
carry relative paths; they are normalized against the configured
base directory before persistence.
"""

from eventum.app.startup.exceptions import (
    StartupConflictError,
    StartupError,
    StartupNotFoundError,
)
from eventum.app.startup.models import (
    StartupGeneratorParameters,
    StartupGeneratorParametersList,
)
from eventum.app.startup.service import Startup

__all__ = [
    'Startup',
    'StartupConflictError',
    'StartupError',
    'StartupGeneratorParameters',
    'StartupGeneratorParametersList',
    'StartupNotFoundError',
]
