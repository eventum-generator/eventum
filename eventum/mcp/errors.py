"""Translation of domain exceptions into safe MCP tool errors.

Domain ContextualErrors carry absolute paths and may carry resolved
secret values in their reason text; tools must expose only an
allow-listed, path-relativized payload to the agent.
"""

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from eventum.exceptions import ContextualError

# Context keys safe to expose to an external agent. Anything else is
# dropped. `file_path` is relativized to generators_dir (never
# absolute).
_ALLOWED_KEYS = frozenset({'file_path', 'reason', 'value', 'name'})

# Quoted absolute POSIX path token as produced by OSError str()
# (e.g. "No such file or directory: '/abs/path/x.yml'"). Captures the
# final component so only the basename is kept.
_QUOTED_ABS_PATH = re.compile(r"'/[^']*/([^/']+)'")

# Marker replacing redacted secret values inside reason text.
_REDACTED = '[redacted]'


def _scrub_reason(
    text: str,
    base: Path,
    redact_values: list[str],
) -> str:
    """Strip absolute paths and secret values from a reason string.

    The transforms, applied in order:

    1. Occurrences of ``base`` (the resolved generators_dir) are
       made relative: a leading ``str(base) + os.sep`` is dropped so
       embedded paths under the directory become relative, and a bare
       ``str(base)`` is reduced to ``'.'``.
    2. Other quoted absolute POSIX paths (as formatted by ``OSError``)
       are reduced to their final path component.
    3. Each non-empty value in ``redact_values`` is replaced with
       ``[redacted]``.

    Parameters
    ----------
    text : str
        Raw reason text from a ``ContextualError`` context.

    base : Path
        Resolved generators directory used to relativize paths.

    redact_values : list[str]
        Secret values to replace with ``[redacted]``.

    Returns
    -------
    str
        Reason text safe to forward to an agent.

    """
    base_str = str(base)
    text = text.replace(base_str + os.sep, '')
    text = text.replace(base_str, '.')

    text = _QUOTED_ABS_PATH.sub(r"'\1'", text)

    for value in redact_values:
        if value:
            text = text.replace(value, _REDACTED)

    return text


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
    redact_values: list[str] | None = None,
) -> ToolFailure:
    """Translate a domain ContextualError into an agent-safe failure.

    Parameters
    ----------
    error : ContextualError
        Domain exception to translate.

    generators_dir : Path
        Base directory used to relativize ``file_path`` context values.

    redact_values : list[str] | None, default None
        Secret values to replace with ``[redacted]`` in the ``reason``
        text. Callers running real configs (preview/validate) must
        pass the config's resolved ``${secrets.*}`` values here, since
        secret redaction applies only to values listed here.

    Returns
    -------
    ToolFailure
        Structured failure with an allow-listed, path-relativized
        ``details`` dict.

    """
    # The `reason` text can carry absolute filesystem paths (embedded
    # in OS error / validation strings) and resolved secret values;
    # both are scrubbed here (spec 7.1). Path stripping is automatic;
    # secret redaction needs `redact_values` from the caller.
    details = scrub_context(error.context, generators_dir)

    if 'reason' in details:
        details['reason'] = _scrub_reason(
            str(details['reason']),
            generators_dir.resolve(),
            redact_values or [],
        )

    return ToolFailure(error=str(error), details=details)
