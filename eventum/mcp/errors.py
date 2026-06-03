"""Translation of domain exceptions into safe MCP tool errors.

Domain ContextualErrors carry absolute paths and may carry resolved
secret values in their reason text; tools must expose only an
allow-listed, path-relativized payload to the agent.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from eventum.exceptions import ContextualError

# Context keys safe to expose to an external agent. Anything else is
# dropped. `file_path` is relativized to generators_dir (never
# absolute).
_ALLOWED_KEYS = frozenset({'file_path', 'reason', 'value', 'name'})


@dataclass(frozen=True)
class ToolFailure:
    """Structured, agent-safe error returned by an MCP tool."""

    error: str
    details: dict[str, Any] = field(default_factory=dict)


def scrub_context(
    context: dict[str, Any],
    generators_dir: Path,
) -> dict[str, Any]:
    """Allow-list context keys and relativize any absolute path.

    Keys not in ``_ALLOWED_KEYS`` are dropped. ``file_path`` values
    are relativized to ``generators_dir``; if the path falls outside
    that directory, only the final component is kept.

    Parameters
    ----------
    context : dict[str, Any]
        Raw context dict from a ``ContextualError``.

    generators_dir : Path
        Base directory used to relativize ``file_path`` values.

    Returns
    -------
    dict[str, Any]
        Scrubbed context safe to forward to an agent.

    """
    out: dict[str, Any] = {}
    base = generators_dir.resolve()

    for key, value in context.items():
        if key not in _ALLOWED_KEYS:
            continue

        if key == 'file_path':
            try:
                rel = Path(str(value)).resolve().relative_to(base)
                out[key] = str(rel)
            except ValueError:
                out[key] = Path(str(value)).name
        else:
            out[key] = value

    return out


def to_tool_error(
    error: ContextualError,
    generators_dir: Path,
) -> ToolFailure:
    """Translate a domain ContextualError into an agent-safe failure.

    Parameters
    ----------
    error : ContextualError
        Domain exception to translate.

    generators_dir : Path
        Base directory used to relativize ``file_path`` context values.

    Returns
    -------
    ToolFailure
        Structured failure with an allow-listed, path-relativized
        ``details`` dict.

    """
    # TODO(2B): `reason` is forwarded verbatim and can leak: (a) secret  # noqa: TD003, E501
    # values from resolved ${secrets.*}, and (b) absolute filesystem
    # paths embedded in OS error / validation reason strings (e.g.
    # "[Errno 2] ...: '/abs/path/generator.yml'"). Once validate/preview
    # is wired, 2B should scrub `reason` text for both (spec 7.1).
    return ToolFailure(
        error=str(error),
        details=scrub_context(error.context, generators_dir),
    )
