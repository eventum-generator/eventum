"""Tests for dotted keys expansion."""

from typing import Any

import pytest

from eventum.utils.dotted_keys import DottedKeyError, expand_dotted_keys


def test_expands_dotted_key_at_root() -> None:
    """Dotted key at the root expands to a nested mapping."""
    assert expand_dotted_keys({'a.b': 1}) == {'a': {'b': 1}}


def test_expands_dotted_key_inside_nested_mapping() -> None:
    """Dotted key inside a nested mapping expands."""
    data = {'server': {'mcp.enabled': True}}
    expected = {'server': {'mcp': {'enabled': True}}}
    assert expand_dotted_keys(data) == expected


def test_expands_multi_segment_key() -> None:
    """Key with several dots expands to a chain of mappings."""
    data = {'a.b.c.d': 1}
    expected = {'a': {'b': {'c': {'d': 1}}}}
    assert expand_dotted_keys(data) == expected


def test_merges_mixed_spellings() -> None:
    """Dotted and nested spellings of one section deep-merge."""
    data = {
        'server': {
            'mcp.enabled': True,
            'mcp': {'path': '/mcp'},
            'host': 'localhost',
        },
    }
    expected = {
        'server': {
            'mcp': {'enabled': True, 'path': '/mcp'},
            'host': 'localhost',
        },
    }
    assert expand_dotted_keys(data) == expected


def test_merges_sibling_dotted_keys() -> None:
    """Sibling dotted keys sharing a prefix merge into one mapping."""
    data = {'a.b': 1, 'a.c': 2}
    assert expand_dotted_keys(data) == {'a': {'b': 1, 'c': 2}}


def test_recurses_into_list_items() -> None:
    """Mappings inside lists are expanded."""
    data = {'output': [{'stdout.formatter.format': 'plain'}]}
    expected = {'output': [{'stdout': {'formatter': {'format': 'plain'}}}]}
    assert expand_dotted_keys(data) == expected


def test_root_list_items_expanded() -> None:
    """Items of a root-level list are expanded."""
    data = [{'a.b': 1}, {'c': 2}]
    assert expand_dotted_keys(data) == [{'a': {'b': 1}}, {'c': 2}]


def test_non_string_keys_untouched() -> None:
    """Non-string keys are kept as is, their values still expand."""
    data = {1: {'a.b': 1}, None: 2}
    expected = {1: {'a': {'b': 1}}, None: 2}
    assert expand_dotted_keys(data) == expected


def test_keys_with_empty_segments_untouched() -> None:
    """Keys with empty path segments are not split."""
    data = {'a.': 1, '.b': 2, 'c..d': 3, '.': 4}
    assert expand_dotted_keys(data) == data


def test_preserves_explicit_empty_mapping() -> None:
    """Explicit empty mapping survives expansion."""
    assert expand_dotted_keys({'a.b': {}}) == {'a': {'b': {}}}


def test_empty_mapping_merges_with_sibling() -> None:
    """Empty mapping merges into a non-empty sibling spelling."""
    data = {'a.b': {}, 'a': {'b': {'c': 1}}}
    assert expand_dotted_keys(data) == {'a': {'b': {'c': 1}}}


@pytest.mark.parametrize(
    'value',
    [None, 1, 3.14, True, 'a.b', [], {}],
)
def test_scalars_and_empty_containers_pass_through(value: Any) -> None:
    """Scalar values and empty containers pass through unchanged."""
    assert expand_dotted_keys(value) == value


def test_input_not_mutated() -> None:
    """Expansion returns new structures and keeps the input intact."""
    data = {'a.b': {'c.d': 1}, 'e': [{'f.g': 2}]}
    expand_dotted_keys(data)
    assert data == {'a.b': {'c.d': 1}, 'e': [{'f.g': 2}]}


def test_conflict_same_leaf_two_paths() -> None:
    """Two spellings writing the same leaf raise with the path."""
    data = {'a.b': 1, 'a': {'b': 2}}
    with pytest.raises(DottedKeyError) as exc:
        expand_dotted_keys(data)

    assert '`a.b`' in str(exc.value)


def test_conflict_path_through_non_mapping() -> None:
    """Dotted path through a non-mapping raises with the path."""
    data = {'a': 5, 'a.b': 1}
    with pytest.raises(DottedKeyError) as exc:
        expand_dotted_keys(data)

    assert '`a`' in str(exc.value)


def test_conflict_path_includes_list_index() -> None:
    """Conflict inside a list item reports the indexed path."""
    data = {
        'output': [{'stdout.format': 'plain', 'stdout': {'format': 'json'}}],
    }
    with pytest.raises(DottedKeyError) as exc:
        expand_dotted_keys(data)

    assert '`output[0].stdout.format`' in str(exc.value)


def test_conflict_under_nested_mapping_reports_full_path() -> None:
    """Conflict below the root reports the full key path."""
    data = {'server': {'mcp.enabled': True, 'mcp': {'enabled': False}}}
    with pytest.raises(DottedKeyError) as exc:
        expand_dotted_keys(data)

    assert '`server.mcp.enabled`' in str(exc.value)
