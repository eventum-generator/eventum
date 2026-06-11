"""Expansion of dot-separated mapping keys in parsed YAML data."""

from typing import Any


class DottedKeyError(ValueError):
    """Conflict during expansion of dot-separated mapping keys.

    Raised when two spellings of the same key path produce
    conflicting values: the same leaf is written more than once
    (e.g. `a.b: 1` together with `a: {b: 2}`) or a dotted path
    traverses a key that holds a non-mapping value (e.g. `a: 5`
    together with `a.b: 1`). The message contains the offending
    key path.
    """


def expand_dotted_keys(value: Any) -> Any:
    """Expand dot-separated mapping keys into nested mappings.

    Every string key containing a dot is treated as a path of
    nested mapping keys: `{'a.b': 1}` becomes `{'a': {'b': 1}}`.
    Expansion is applied recursively to mapping values and list
    items, so dotted keys work at any depth of the structure.
    Entries spelled differently but sharing a path prefix are
    deep-merged: `{'a.b': 1, 'a': {'c': 2}}` becomes
    `{'a': {'b': 1, 'c': 2}}`.

    Non-string keys and string keys with empty path segments
    (e.g. `'a.'` or `'.b'`) are kept as is. Scalar values are
    returned unchanged and explicit empty mappings are preserved.
    The input is not mutated: expanded mappings and lists are new
    objects.

    Parameters
    ----------
    value : Any
        Parsed YAML data to expand.

    Returns
    -------
    Any
        Expanded data.

    Raises
    ------
    DottedKeyError
        If two spellings produce conflicting values for the same
        key path.

    """
    return _expand(value, path='')


def _join_key(path: str, key: Any) -> str:
    """Append a mapping key segment to a path."""
    if not path:
        return str(key)
    return f'{path}.{key}'


def _join_index(path: str, index: int) -> str:
    """Append a list index segment to a path."""
    return f'{path}[{index}]'


def _split_key(key: Any) -> list[Any]:
    """Split a key on dots if it is an expandable string key."""
    if not isinstance(key, str) or '.' not in key:
        return [key]

    parts = key.split('.')
    if any(not part for part in parts):
        return [key]

    return parts


def _expand(value: Any, path: str) -> Any:
    """Recursively expand a parsed YAML node."""
    if isinstance(value, dict):
        result: dict[Any, Any] = {}

        for key, item in value.items():
            parts = _split_key(key)

            leaf_path = path
            for part in parts:
                leaf_path = _join_key(leaf_path, part)

            entry: Any = _expand(item, leaf_path)
            for part in reversed(parts[1:]):
                entry = {part: entry}

            head = parts[0]
            if head in result:
                result[head] = _merge(
                    result[head],
                    entry,
                    _join_key(path, head),
                )
            else:
                result[head] = entry

        return result

    if isinstance(value, list):
        return [
            _expand(item, _join_index(path, index))
            for index, item in enumerate(value)
        ]

    return value


def _merge(existing: Any, incoming: Any, path: str) -> Any:
    """Deep-merge two expanded values, raising on conflicts."""
    if isinstance(existing, dict) and isinstance(incoming, dict):
        merged = dict(existing)

        for key, value in incoming.items():
            if key in merged:
                merged[key] = _merge(
                    merged[key],
                    value,
                    _join_key(path, key),
                )
            else:
                merged[key] = value

        return merged

    msg = f'Conflicting values for key `{path}`'
    raise DottedKeyError(msg)
