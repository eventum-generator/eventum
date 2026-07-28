"""Functions for generator configuration loading."""

import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import structlog
import yaml
from jinja2 import BaseLoader, Environment, TemplateSyntaxError
from pydantic import ValidationError

from eventum.core.config import GeneratorConfig
from eventum.exceptions import ContextualError
from eventum.security.manage import get_secret
from eventum.utils.validation_prettier import prettify_validation_errors

logger = structlog.stdlib.get_logger()

TOKEN_PATTERN = re.compile(pattern=r'\${\s*?(\S*?)\s*?}')

_MISSING = object()


class ConfigurationLoadError(ContextualError):
    """Error during loading generator configuration."""


def _strip_yaml_comments(content: str) -> str:
    """Strip full-line YAML comments from content.

    Parameters
    ----------
    content : str
        Raw YAML content.

    Returns
    -------
    str
        Content with full-line comments replaced by empty lines.

    """
    lines: list[str] = []

    for line in content.splitlines():
        if line.lstrip().startswith('#'):
            lines.append('')
        else:
            lines.append(line)

    return '\n'.join(lines)


def _extract_tokens(content: str, prefix: str | None = None) -> list[str]:
    """Extract tokens enclosed within `${}` from the given content.

    Parameters
    ----------
    content : str
        Content to search for tokens.

    prefix : str | None, default=None
        Prefix to filter tokens (the part before the first dot), if not
        provided, all tokens will be extracted.

    Returns
    -------
    list[str]
        List of extracted tokens.

    """
    matches: list[str] = re.findall(pattern=TOKEN_PATTERN, string=content)

    if not matches:
        return []

    if prefix is None:
        return matches

    tokens: list[str] = []
    for match in matches:
        parts = match.split('.', maxsplit=1)

        if len(parts) == 2 and parts[0] == prefix:  # noqa: PLR2004
            tokens.append(match)

    return tokens


def extract_params(content: str) -> list[str]:
    """Extract param names from configuration content.

    Parameters
    ----------
    content : str
        Content of configuration.

    Returns
    -------
    list[str]
        List of extracted param names.

    """
    tokens = _extract_tokens(content, prefix='params')

    if not tokens:
        return []

    params: list[str] = []
    for token in tokens:
        _, name = token.split('.', maxsplit=1)
        params.append(name)

    return params


def extract_secrets(content: str) -> list[str]:
    """Extract secret names from configuration content.

    Parameters
    ----------
    content : str
        Content of configuration.

    Returns
    -------
    list[str]
        List of extracted secret names.

    """
    tokens = _extract_tokens(content, prefix='secrets')

    if not tokens:
        return []

    secrets: list[str] = []
    for token in tokens:
        _, name = token.split('.', maxsplit=1)
        secrets.append(name)

    return secrets


def _resolve_param(name: str, provided_params: dict[str, Any]) -> Any:
    """Get param value addressed by the name used in a token.

    The name addresses either a param spelled exactly like it, or a
    path of nested param names.

    Parameters
    ----------
    name : str
        Param name used in substitution.

    provided_params : dict[str, Any]
        Params provided by user.

    Returns
    -------
    Any
        Param value, or `_MISSING` if the name addresses no value.

    """
    if name in provided_params:
        return provided_params[name]

    value: Any = provided_params
    for part in name.split('.'):
        if not isinstance(value, dict) or part not in value:
            return _MISSING

        value = value[part]

    return value


def _set_token_value(
    context: dict[str, Any],
    name: str,
    value: Any,
) -> None:
    """Put value into rendering context under the path of the name.

    Parameters
    ----------
    context : dict[str, Any]
        Rendering context to fill.

    name : str
        Name used in substitution, its parts address nesting levels.

    value : Any
        Value to put.

    Raises
    ------
    ValueError
        If the path is already occupied by the value of another name.

    """
    msg = f'Name `{name}` overlaps with another used name'

    *parts, leaf = name.split('.')

    node = context
    for part in parts:
        child = node.setdefault(part, {})

        if isinstance(child, dict):
            node = child
            continue

        raise ValueError(msg)

    occupied = node.get(leaf, _MISSING)
    if occupied is not _MISSING and occupied != value:
        raise ValueError(msg)

    node[leaf] = value


def _prepare_params(
    used_params: Iterable[str],
    provided_params: dict[str, Any],
) -> dict[str, Any]:
    """Prepare params for config substitution by getting it from
    provided params.

    Parameters
    ----------
    used_params : Iterable[str]
        Param names used in substitution.

    provided_params : dict[str, Any]
        Params provided by user.

    Returns
    -------
    dict[str, Any]
        Params prepared for substitution.

    Raises
    ------
    ValueError
        If some parameters are missing or their names overlap.

    """
    rendering_params: dict[str, Any] = {}
    missing_params: set[str] = set()

    for param in sorted(set(used_params)):
        value = _resolve_param(param, provided_params)

        if value is _MISSING:
            missing_params.add(param)
            continue

        _set_token_value(rendering_params, param, value)

    if missing_params:
        msg = f'Parameters {missing_params} are missing'
        raise ValueError(msg)

    return rendering_params


def _prepare_secrets(used_secrets: Iterable[str]) -> dict[str, Any]:
    """Prepare secrets for config substitution by getting it from
    secrets storage.

    Parameters
    ----------
    used_secrets : Iterable[str]
        Secret names used in substitution.

    Returns
    -------
    dict[str, Any]
        Secrets prepared for substitution.

    Raises
    ------
    ValueError
        If some secrets are missing, cannot be read from keyring or
        their names overlap.

    """
    rendering_secrets: dict[str, Any] = {}

    for secret in sorted(set(used_secrets)):
        try:
            value = get_secret(secret)
        except (OSError, ValueError) as e:
            msg = f'Cannot obtain secret `{secret}`: {e}'
            raise ValueError(msg) from None

        _set_token_value(rendering_secrets, secret, value)

    return rendering_secrets


def _substitute_tokens(
    params: dict[str, Any],
    secrets: dict[str, Any],
    content: str,
) -> str:
    """Substitute tokens to content of configuration.

    Parameters
    ----------
    params : dict[str, Any]
        Params.

    secrets : dict[str, Any]
        Secrets.

    content : str
        Content of configuration.

    Returns
    -------
    str
        Content of configuration with substituted tokens.

    Raises
    ------
    ValueError
        If any error occurs during tokens substitution.

    """
    rendering_kwargs = {
        'params': params,
        'secrets': secrets,
    }
    env = Environment(
        loader=BaseLoader(),
        variable_start_string='${',
        variable_end_string='}',
    )
    try:
        template = env.from_string(content)
        return template.render(rendering_kwargs)
    except TemplateSyntaxError as e:
        msg = (
            f'Tokens substitution structure is malformed: {e} '
            f'(line {e.lineno})'
        )
        raise ValueError(msg) from e
    except Exception as e:
        raise ValueError(str(e)) from e


def load(path: Path, params: dict[str, Any]) -> GeneratorConfig:
    """Load generator configuration from the file on specified path.

    Parameters
    ----------
    path : Path
        Configuration path.

    params : dict[str, Any]
        Parameters to substitute in configuration content.

    Returns
    -------
    GeneratorConfig
        Loaded generator configuration.

    Raises
    ------
    ConfigurationLoadError
        If configuration cannot be loaded.

    """
    logger.debug('Reading file', file_path=str(path))
    try:
        with path.open() as f:
            content = f.read()
    except OSError as e:
        msg = 'Failed to read configuration file'
        raise ConfigurationLoadError(
            msg,
            context={'reason': str(e), 'file_path': str(path)},
        ) from None

    active_content = _strip_yaml_comments(content)

    logger.debug('Extracting params used in config file')
    extracted_params = extract_params(active_content)
    logger.debug('Params is extracted', value=extracted_params)

    logger.debug('Preparing param values')
    try:
        rendering_params = _prepare_params(
            used_params=extracted_params,
            provided_params=params,
        )
    except ValueError as e:
        msg = 'Failed to obtain params used in configuration'
        raise ConfigurationLoadError(
            msg,
            context={'reason': str(e), 'file_path': str(path)},
        ) from None

    logger.debug('Extracting secrets used in config file')
    extracted_secrets = extract_secrets(active_content)
    logger.debug('Secrets is extracted', value=extracted_secrets)

    logger.debug('Preparing secret values')
    try:
        rendering_secrets = _prepare_secrets(
            used_secrets=extracted_secrets,
        )
    except ValueError as e:
        msg = 'Failed to obtain secrets used in configuration'
        raise ConfigurationLoadError(
            msg,
            context={'reason': str(e), 'file_path': str(path)},
        ) from None

    logger.debug('Substituting params and secrets to config')
    try:
        substituted_content = _substitute_tokens(
            params=rendering_params,
            secrets=rendering_secrets,
            content=content,
        )
    except ValueError as e:
        msg = 'Failed to substitute tokens to configuration'
        raise ConfigurationLoadError(
            msg,
            context={
                'reason': str(e),
                'file_path': str(path),
            },
        ) from None

    logger.debug('Parsing yaml content of config')
    try:
        config_data = yaml.load(substituted_content, yaml.SafeLoader)
    except yaml.error.YAMLError as e:
        msg = 'Failed to parse configuration YAML content'
        raise ConfigurationLoadError(
            msg,
            context={
                'reason': str(e),
                'file_path': str(path),
            },
        ) from None

    logger.debug('Validating config')
    try:
        return GeneratorConfig.model_validate(config_data)
    except ValidationError as e:
        msg = 'Invalid configuration'
        raise ConfigurationLoadError(
            msg,
            context={
                'reason': prettify_validation_errors(e.errors()),
                'file_path': str(path),
            },
        ) from None
