"""Tests for startup utility functions."""

from eventum.api.routers.startup.utils import move_key_to_first_position


def test_move_existing_key():
    d = {'b': 2, 'a': 1, 'c': 3}
    result = move_key_to_first_position(d, 'a')
    keys = list(result.keys())
    assert keys[0] == 'a'
    assert result['a'] == 1


def test_move_missing_key():
    d = {'b': 2, 'a': 1}
    result = move_key_to_first_position(d, 'z')
    assert result == {'b': 2, 'a': 1}


def test_move_preserves_all_values():
    d = {'x': 10, 'y': 20, 'z': 30}
    result = move_key_to_first_position(d, 'z')
    assert set(result.values()) == {10, 20, 30}
    assert len(result) == 3
