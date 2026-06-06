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

# Any absolute POSIX path in free log text - quoted, double-quoted, or
# bare - reduced to its final component. Broader than _QUOTED_ABS_PATH
# (which targets quoted OSError paths in structured tool errors): log
# lines carry unquoted paths too, e.g. traceback frames.
_ABS_PATH = re.compile(r"(^|[\s'\"=(,:])/(?:[\w.\-]+/)+([\w.\-]+)")

# Marker replacing redacted secret values inside reason text.
_REDACTED = '[redacted]'


def _redact(text: str, redact_values: list[str]) -> str:
    """Replace each non-empty secret value with the redaction marker.

    Run before path relativization so a secret whose value is itself a
    path is redacted whole, not first reduced to a leaking basename.
    """
    for value in redact_values:
        if value:
            text = text.replace(value, _REDACTED)
    return text


def _scrub_reason(
    text: str,
    base: Path,
    redact_values: list[str],
) -> str:
    """Strip absolute paths and secret values from a reason string.

    The transforms, applied in order:

    1. Each non-empty value in ``redact_values`` is replaced with
       ``[redacted]`` - before any path stripping, so a secret whose
       value is itself a path is redacted whole rather than reduced to
       a leaking basename.
    2. Occurrences of ``base`` (the resolved generators_dir) are made
       relative: a leading ``str(base) + os.sep`` is dropped so
       embedded paths under the directory become relative, and a bare
       ``str(base)`` is reduced to ``'.'``.
    3. Other quoted absolute POSIX paths (as formatted by ``OSError``)
       are reduced to their final path component.

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
    text = _redact(text, redact_values)

    base_str = str(base)
    text = text.replace(base_str + os.sep, '')
    text = text.replace(base_str, '.')

    return _QUOTED_ABS_PATH.sub(r"'\1'", text)


@dataclass(frozen=True)
class ToolFailure:
    """Structured, agent-safe error returned by an MCP tool."""

    error: str
    details: dict[str, Any] = field(default_factory=dict)


def scrub_context(
    context: dict[str, Any],
    generators_dir: Path,
    redact_values: list[str] | None = None,
) -> dict[str, Any]:
    """Allow-list context keys, relativize paths, scrub reason text.

    Keys not in ``_ALLOWED_KEYS`` are dropped. ``file_path`` values
    are relativized to ``generators_dir``; if the path falls outside
    that directory, only the final component is kept. A ``reason``
    value is run through ``_scrub_reason`` so absolute paths embedded
    in OS error / validation strings are stripped and any value in
    ``redact_values`` is replaced with ``[redacted]``.

    This is the single scrub point for both error routes: direct
    per-event use (``preview_events``) and ``to_tool_error``.

    Parameters
    ----------
    context : dict[str, Any]
        Raw context dict from a ``ContextualError``.

    generators_dir : Path
        Base directory used to relativize paths.

    redact_values : list[str] | None, default None
        Secret values to replace with ``[redacted]`` in ``reason``.
        Secret redaction applies only to values listed here; callers
        running real configs must pass the config's resolved
        ``${secrets.*}`` values.

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

    if 'reason' in out:
        out['reason'] = _scrub_reason(
            str(out['reason']),
            base,
            redact_values or [],
        )

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
    # `reason` scrubbing (absolute paths + secret redaction, spec 7.1)
    # happens inside `scrub_context`, the single scrub point shared with
    # the direct per-event route. The top-level message is also scrubbed
    # here: domain rules keep it a static string, but scrubbing it too is
    # cheap defense-in-depth against a stray path/secret in the message.
    base = generators_dir.resolve()
    return ToolFailure(
        error=_scrub_reason(str(error), base, redact_values or []),
        details=scrub_context(error.context, generators_dir, redact_values),
    )


def scrub_log_line(
    line: str,
    generators_dir: Path,
    logs_dir: Path,
    redact_values: list[str],
) -> str:
    """Strip absolute paths and secret values from one log line.

    Redacts the listed secret values first (so a path-shaped secret is
    redacted whole), then relativizes the generators and logs
    directories and reduces any other absolute path to its final
    component. Used by the log-reading tool; a log line is free-form
    text, so this is a best-effort scrub over the listed secret values,
    not a guarantee that every conceivable secret encoding is caught.

    Parameters
    ----------
    line : str
        Raw log line.

    generators_dir : Path
        Generators directory to relativize.

    logs_dir : Path
        Logs directory to relativize.

    redact_values : list[str]
        Secret values to replace with ``[redacted]``.

    Returns
    -------
    str
        Log line safe to forward to an agent.

    """
    line = _redact(line, redact_values)

    for base in (generators_dir, logs_dir):
        base_str = str(base.resolve())
        line = line.replace(base_str + os.sep, '')
        line = line.replace(base_str, '.')

    return _ABS_PATH.sub(r'\1\2', line)
