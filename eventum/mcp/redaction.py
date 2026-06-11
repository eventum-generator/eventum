"""Resolve a config's own secret values for redaction.

Shared by the tools that return config-derived text to the agent
(preview, validate, and log reading). Each resolves the ``${secrets.*}``
a specific generator config references, so those values can be scrubbed
from the output - scoped to that one config rather than reading every
secret in the keyring.
"""

import contextlib
from pathlib import Path

from eventum.core.config_loader import extract_secrets
from eventum.security.manage import get_secret


def read_config_secret_values(cfg_path: Path) -> list[str]:
    """Return resolved values for the secrets a config references.

    Reads the raw config text, extracts the ``${secrets.*}`` names, and
    resolves each with ``get_secret``. Secrets that cannot be resolved
    (missing, keyring error) are skipped - this is best-effort
    redaction; a value that was never substituted cannot appear in the
    output anyway.

    Parameters
    ----------
    cfg_path : Path
        Absolute path to a generator config file.

    Returns
    -------
    list[str]
        Resolved secret values to redact. Empty if the file cannot be
        read or references no secrets.

    """
    try:
        text = cfg_path.read_text()
    except OSError:
        return []

    names = extract_secrets(text)
    values: list[str] = []

    for name in names:
        with contextlib.suppress(ValueError, OSError):
            values.append(get_secret(name))

    return values
