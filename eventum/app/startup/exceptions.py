"""Exceptions raised by the startup package."""

from eventum.exceptions import ContextualError


class StartupError(ContextualError):
    """Startup file cannot be read, parsed, validated, or written.

    Direct instances cover low-level failures (filesystem, YAML,
    schema validation) and carry `file_path` (str) in `context`,
    plus `reason` (str) when the cause has a textual description.
    Subclasses signal entry-level failures and have their own
    context shape (see their docstrings).
    """


class StartupNotFoundError(StartupError):
    """Generator with the requested id is not in the startup file."""


class StartupConflictError(StartupError):
    """Generator with the same id is already in the startup file."""


class ScenarioNotFoundError(StartupError):
    """Referenced scenario, or a generator's membership in it, is absent.

    Carries `name` (str, the scenario) in `context`, plus `value`
    (str, the generator id) when the failure is about one generator's
    membership rather than the scenario as a whole.
    """


class ScenarioConflictError(StartupError):
    """Requested scenario name is already in use.

    Carries `name` (str, the scenario) in `context`, plus `value`
    (str, the generator id) when the conflict is about one generator
    already carrying the tag.
    """
