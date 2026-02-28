import pytest

from eventum.utils.lru_cache import LRUCache


class TestInit:
    def test_creates_empty_cache(self):
        cache: LRUCache[str, int] = LRUCache(maxsize=3)
        assert len(cache) == 0

    def test_maxsize_property(self):
        cache: LRUCache[str, int] = LRUCache(maxsize=5)
        assert cache.maxsize == 5

    def test_maxsize_zero_raises(self):
        with pytest.raises(ValueError, match='maxsize'):
            LRUCache(maxsize=0)

    def test_maxsize_negative_raises(self):
        with pytest.raises(ValueError, match='maxsize'):
            LRUCache(maxsize=-1)


class TestGetSet:
    def test_set_and_get(self):
        cache: LRUCache[str, int] = LRUCache(maxsize=3)
        cache['a'] = 1
        assert cache['a'] == 1

    def test_get_missing_key_raises(self):
        cache: LRUCache[str, int] = LRUCache(maxsize=3)
        with pytest.raises(KeyError):
            cache['missing']

    def test_overwrite_value(self):
        cache: LRUCache[str, int] = LRUCache(maxsize=3)
        cache['a'] = 1
        cache['a'] = 2
        assert cache['a'] == 2
        assert len(cache) == 1


class TestEviction:
    def test_evicts_lru_entry(self):
        cache: LRUCache[str, int] = LRUCache(maxsize=2)
        cache['a'] = 1
        cache['b'] = 2
        cache['c'] = 3

        assert 'a' not in cache
        assert cache['b'] == 2
        assert cache['c'] == 3

    def test_get_refreshes_order(self):
        cache: LRUCache[str, int] = LRUCache(maxsize=2)
        cache['a'] = 1
        cache['b'] = 2

        # access 'a' to make it recently used
        _ = cache['a']

        cache['c'] = 3

        # 'b' should be evicted, not 'a'
        assert 'b' not in cache
        assert cache['a'] == 1
        assert cache['c'] == 3

    def test_set_existing_refreshes_order(self):
        cache: LRUCache[str, int] = LRUCache(maxsize=2)
        cache['a'] = 1
        cache['b'] = 2

        # overwrite 'a' to refresh it
        cache['a'] = 10

        cache['c'] = 3

        # 'b' should be evicted, not 'a'
        assert 'b' not in cache
        assert cache['a'] == 10
        assert cache['c'] == 3

    def test_maxsize_one(self):
        cache: LRUCache[str, int] = LRUCache(maxsize=1)
        cache['a'] = 1
        cache['b'] = 2

        assert 'a' not in cache
        assert cache['b'] == 2
        assert len(cache) == 1


class TestEvictionCallback:
    def test_callback_called_on_eviction(self):
        evicted: list[tuple[str, int]] = []
        cache: LRUCache[str, int] = LRUCache(
            maxsize=2,
            on_evict=lambda k, v: evicted.append((k, v)),
        )
        cache['a'] = 1
        cache['b'] = 2
        cache['c'] = 3

        assert evicted == [('a', 1)]

    def test_callback_not_called_without_eviction(self):
        evicted: list[tuple[str, int]] = []
        cache: LRUCache[str, int] = LRUCache(
            maxsize=3,
            on_evict=lambda k, v: evicted.append((k, v)),
        )
        cache['a'] = 1
        cache['b'] = 2

        assert evicted == []

    def test_multiple_evictions(self):
        evicted: list[tuple[str, int]] = []
        cache: LRUCache[str, int] = LRUCache(
            maxsize=1,
            on_evict=lambda k, v: evicted.append((k, v)),
        )
        cache['a'] = 1
        cache['b'] = 2
        cache['c'] = 3

        assert evicted == [('a', 1), ('b', 2)]
        assert list(cache.keys()) == ['c']

    def test_no_callback_by_default(self):
        cache: LRUCache[str, int] = LRUCache(maxsize=1)
        cache['a'] = 1
        cache['b'] = 2  # evicts 'a' — no error without callback

        assert list(cache.keys()) == ['b']


class TestContains:
    def test_contains_existing(self):
        cache: LRUCache[str, int] = LRUCache(maxsize=3)
        cache['a'] = 1
        assert 'a' in cache

    def test_not_contains_missing(self):
        cache: LRUCache[str, int] = LRUCache(maxsize=3)
        assert 'a' not in cache

    def test_not_contains_after_eviction(self):
        cache: LRUCache[str, int] = LRUCache(maxsize=1)
        cache['a'] = 1
        cache['b'] = 2
        assert 'a' not in cache
