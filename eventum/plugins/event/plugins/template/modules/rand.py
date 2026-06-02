"""Rand module."""

import datetime as dt
import functools
import ipaddress
import random
import uuid
from collections.abc import Mapping, Sequence
from string import (
    ascii_letters,
    ascii_lowercase,
    ascii_uppercase,
    digits,
    punctuation,
)
from typing import TypeVar, overload

T = TypeVar('T')

_HEX_LOWER = digits + 'abcdef'
_HEX_UPPER = digits + 'ABCDEF'
_WORD = ascii_letters + digits
_NON_ZERO_DIGITS = '123456789'

_PATTERN_CHARSETS: dict[str, str] = {
    'a': ascii_lowercase,
    'A': ascii_uppercase,
    'l': ascii_letters,
    'd': digits,
    'n': _NON_ZERO_DIGITS,
    'h': _HEX_LOWER,
    'H': _HEX_UPPER,
    'p': punctuation,
    'w': _WORD,
}

# OUI prefixes per vendor. Each value is a tuple of 3-byte prefixes
# expressed in lowercase colon notation. Source: public IEEE OUI
# assignments, sampled to give a few prefixes per vendor.
_VENDOR_OUIS: dict[str, tuple[str, ...]] = {
    'apple': ('00:03:93', '00:1f:f3', '04:0c:ce', '6c:96:cf', 'f0:b4:79'),
    'aruba': ('00:0b:86', '00:1a:1e', '20:4c:03', '94:b4:0f'),
    'broadcom': ('00:0a:f7', '00:10:18', '00:1b:e9', 'd4:01:29'),
    'cisco': ('00:00:0c', '00:01:42', '00:1b:54', '00:24:97', 'a4:6c:2a'),
    'dell': ('00:14:22', '18:03:73', '34:17:eb', 'b0:83:fe', 'f8:db:88'),
    'fortinet': ('00:09:0f', '04:d5:90', '90:6c:ac', 'e0:23:ff'),
    'hp': ('00:01:e6', '00:08:83', '00:0e:7f', '3c:d9:2b', '94:18:82'),
    'huawei': ('00:18:82', '00:1e:10', '04:25:c5', '20:f3:a3', '38:bc:01'),
    'ibm': ('00:01:e1', '00:09:6b', '00:14:5e', '00:17:ef', '00:21:5e'),
    'intel': ('00:03:47', '00:07:e9', '00:13:02', 'a0:36:9f', 'e8:b1:fc'),
    'juniper': ('00:05:85', '00:12:1e', '00:14:f6', '00:17:cb', '00:1f:12'),
    'lenovo': ('00:21:cc', '54:e1:ad', 'a0:51:0b', 'cc:07:e4', 'e8:6f:38'),
    'microsoft': ('00:03:ff', '00:15:5d', '00:50:f2', '28:18:78', '60:45:bd'),
    'mikrotik': ('00:0c:42', '4c:5e:0c', '6c:3b:6b', 'b8:69:f4'),
    'netgear': ('00:09:5b', '00:14:6c', '00:1b:2f', '20:e5:2a', '4c:60:de'),
    'paloalto': ('00:1b:17', 'b4:0c:25'),
    'samsung': ('00:07:ab', '00:23:39', '08:08:c2', '34:23:ba', 'f0:08:f1'),
    'tplink': ('00:1d:0f', '14:cc:20', '50:c7:bf', '98:da:c4', 'd8:0d:17'),
    'ubiquiti': ('00:15:6d', '04:18:d6', '24:5a:4c', '74:ac:b9', 'fc:ec:da'),
    'vmware': ('00:05:69', '00:0c:29', '00:1c:14', '00:50:56'),
}


@functools.lru_cache(maxsize=256)
def _parse_oui(oui: str) -> tuple[int, int, int]:
    """Parse a 3-byte OUI prefix into a tuple of integers.

    Accepts ``aa:bb:cc`` and ``aa-bb-cc`` (case-insensitive). Each
    octet must be exactly two hex digits. Raises ``ValueError`` for
    any other shape. Cached because callers may invoke ``mac()`` on
    the hot path with the same prefix repeatedly.
    """
    parts = oui.replace('-', ':').split(':')
    if len(parts) != 3 or not all(len(p) == 2 for p in parts):  # noqa: PLR2004
        msg = f'invalid OUI prefix: {oui!r}'
        raise ValueError(msg)
    try:
        a, b, c = (int(p, 16) for p in parts)
    except ValueError:
        msg = f'invalid OUI prefix: {oui!r}'
        raise ValueError(msg) from None
    return a, b, c


def _parse_brace_count(format_string: str, start: int) -> tuple[int, int]:
    """Parse a ``{N}`` block at `start` (the ``{`` position).

    Returns ``(count, next_index)``. Raises ``ValueError`` for an
    unclosed brace or a non-numeric count.
    """
    end = format_string.find('}', start + 1)
    if end == -1:
        msg = "unclosed '{' in pattern"
        raise ValueError(msg)
    count_str = format_string[start + 1 : end]
    if not count_str.isdigit():
        msg = f'invalid repeat count: {count_str!r}'
        raise ValueError(msg)
    return int(count_str), end + 1


@functools.lru_cache(maxsize=256)
def _compile_pattern(format_string: str) -> tuple[tuple, ...]:
    """Parse a pattern string into a tuple of tokens.

    Each token is either ``('lit', text)`` for verbatim text or
    ``('spec', charset, count)`` for a random-character segment.
    Results are cached so repeated calls with the same pattern
    skip re-parsing.
    """
    tokens: list[tuple] = []
    literal_buf: list[str] = []
    i = 0
    n = len(format_string)

    while i < n:
        c = format_string[i]
        if c != '%':
            literal_buf.append(c)
            i += 1
            continue

        i += 1
        if i >= n:
            msg = (
                "incomplete format specifier at end of pattern (trailing '%')"
            )
            raise ValueError(msg)

        spec = format_string[i]
        i += 1

        count = 1
        if i < n and format_string[i] == '{':
            count, i = _parse_brace_count(format_string, i)

        if spec == '%':
            literal_buf.append('%' * count)
            continue

        charset = _PATTERN_CHARSETS.get(spec)
        if charset is None:
            msg = f'unknown format specifier: %{spec}'
            raise ValueError(msg)

        if literal_buf:
            tokens.append(('lit', ''.join(literal_buf)))
            literal_buf.clear()
        tokens.append(('spec', charset, count))

    if literal_buf:
        tokens.append(('lit', ''.join(literal_buf)))

    return tuple(tokens)


def shuffle(items: Sequence[T]) -> list[T] | str:
    """Shuffle sequence elements."""
    seq = list(items)
    random.shuffle(seq)

    if isinstance(items, str):
        return ''.join(seq)  # type: ignore[arg-type]
    return seq


def choice(items: Sequence[T]) -> T:
    """Return random item from non empty sequence."""
    return random.choice(items)


def choices(items: Sequence[T], n: int) -> list[T]:
    """Return `n` random items from non empty sequence."""
    return random.choices(items, k=n)


@overload
def weighted_choice(
    items: Mapping[T, float],
) -> T: ...


@overload
def weighted_choice(
    items: Sequence[T],
    weights: Sequence[float],
) -> T: ...


def weighted_choice(
    items: Sequence[T] | Mapping[T, float],
    weights: Sequence[float] | None = None,
) -> T:
    """Return random item from non empty sequence with `weights`
    probability.

    Also accepts a dict mapping items to their weights::

        weighted_choice({'a': 70, 'b': 20, 'c': 10})
    """
    if isinstance(items, Mapping):
        return random.choices(
            list(items.keys()),
            weights=list(items.values()),
            k=1,
        ).pop()
    return random.choices(items, weights=weights, k=1).pop()


@overload
def weighted_choices(
    items: Mapping[T, float],
    weights: int,
) -> list[T]: ...


@overload
def weighted_choices(
    items: Sequence[T],
    weights: Sequence[float],
    n: int = ...,
) -> list[T]: ...


def weighted_choices(
    items: Sequence[T] | Mapping[T, float],
    weights: Sequence[float] | int,
    n: int | None = None,
) -> list[T]:
    """Return `n` random items from non empty sequence with `weights`
    probability.

    Also accepts a dict mapping items to their weights, with
    ``n`` as the second argument::

        weighted_choices({'a': 70, 'b': 20, 'c': 10}, 5)
    """
    if isinstance(items, Mapping) and isinstance(weights, int):
        return random.choices(
            list(items.keys()),
            weights=list(items.values()),
            k=weights,
        )
    if (
        not isinstance(items, Mapping)
        and not isinstance(weights, int)
        and n is not None
    ):
        return random.choices(items, weights=weights, k=n)
    msg = 'expected (dict, n) or (items, weights, n)'
    raise TypeError(msg)


def chance(prob: float) -> bool:
    """Return `True` with the given probability `prob` (0.0 to 1.0)."""
    if prob <= 0:
        return False

    if prob >= 1:
        return True

    return random.random() < prob


class number:  # noqa: N801
    """Namespace for generating random numbers."""

    @staticmethod
    def integer(a: int, b: int) -> int:
        """Return random integer in range [a, b]."""
        return random.randint(a, b)

    @staticmethod
    def floating(a: float, b: float) -> float:
        """Return random floating point number in range [a, b]."""
        return random.uniform(a, b)

    @staticmethod
    def gauss(mu: float, sigma: float) -> float:
        """Return random floating point number with Gaussian
        distribution.
        """
        return random.gauss(mu, sigma)

    @staticmethod
    def lognormal(mu: float, sigma: float) -> float:
        """Return random floating point number with log-normal
        distribution (always positive, right-skewed).
        """
        return random.lognormvariate(mu, sigma)

    @staticmethod
    def exponential(lambd: float) -> float:
        """Return random floating point number with exponential
        distribution. `lambd` is the rate parameter (1 / mean).
        """
        return random.expovariate(lambd)

    @staticmethod
    def pareto(alpha: float, xmin: float = 1.0) -> float:
        """Return random floating point number with Pareto
        distribution (heavy-tailed, values >= `xmin`).
        """
        return xmin * random.paretovariate(alpha)

    @staticmethod
    def triangular(
        low: float,
        high: float,
        mode: float,
    ) -> float:
        """Return random floating point number with triangular
        distribution in [`low`, `high`] peaking at `mode`.
        """
        return random.triangular(low, high, mode)

    @staticmethod
    def clamp(
        value: float,
        min_val: float,
        max_val: float,
    ) -> float:
        """Clamp `value` to the range [`min_val`, `max_val`]."""
        return max(min_val, min(max_val, value))


class string:  # noqa: N801
    """Namespace for generating random strings."""

    @staticmethod
    def letters_lowercase(size: int) -> str:
        """Return string of specified `size` that contains random ASCII
        lowercase letters.
        """
        return ''.join(random.choices(ascii_lowercase, k=size))

    @staticmethod
    def letters_uppercase(size: int) -> str:
        """Return string of specified `size` that contains random ASCII
        uppercase letters.
        """
        return ''.join(random.choices(ascii_uppercase, k=size))

    @staticmethod
    def letters(size: int) -> str:
        """Return string of specified `size` that contains random ASCII
        letters.
        """
        return ''.join(random.choices(ascii_letters, k=size))

    @staticmethod
    def digits(size: int) -> str:
        """Return string of specified `size` that contains random digit
        characters.
        """
        return ''.join(random.choices(digits, k=size))

    @staticmethod
    def punctuation(size: int) -> str:
        """Return string of specified `size` that contains random ASCII
        punctuation characters.
        """
        return ''.join(random.choices(punctuation, k=size))

    @staticmethod
    def hex(size: int) -> str:
        """Return string of specified `size` that contains random hex
        characters.
        """
        return ''.join(random.choices(_HEX_LOWER, k=size))

    @staticmethod
    def pattern(format_string: str) -> str:
        """Return random string built from a printf-like pattern.

        Format specifiers:

        - ``%a`` lowercase letter (a-z)
        - ``%A`` uppercase letter (A-Z)
        - ``%l`` any letter (a-zA-Z)
        - ``%d`` digit (0-9)
        - ``%n`` non-zero digit (1-9)
        - ``%h`` lowercase hex (0-9a-f)
        - ``%H`` uppercase hex (0-9A-F)
        - ``%p`` ASCII punctuation
        - ``%w`` word character (a-zA-Z0-9)
        - ``%%`` literal ``%``

        Append ``{N}`` to a specifier to emit ``N`` random characters
        from its set instead of one. Other characters in the pattern
        are emitted as-is.

        Example::

            pattern('%A{3}-%d{4}')  # 'ABC-1234'
        """
        parts: list[str] = []
        for token in _compile_pattern(format_string):
            if token[0] == 'lit':
                parts.append(token[1])
            else:
                _, charset, count = token
                parts.append(''.join(random.choices(charset, k=count)))
        return ''.join(parts)


class network:  # noqa: N801
    """Namespace for generating random network entities."""

    @staticmethod
    def ip_v4() -> str:
        """Return random IPv4 address."""
        return '.'.join(str(random.randint(0, 255)) for _ in range(4))

    @staticmethod
    def ip_v4_private_a() -> str:
        """Return random private IPv4 address of Class A."""
        ipv4_int = random.randint(
            int(ipaddress.IPv4Address('10.0.0.0')),
            int(ipaddress.IPv4Address('10.255.255.255')),
        )
        return str(ipaddress.IPv4Address(ipv4_int))

    @staticmethod
    def ip_v4_private_b() -> str:
        """Return random private IPv4 address of Class B."""
        ipv4_int = random.randint(
            int(ipaddress.IPv4Address('172.16.0.0')),
            int(ipaddress.IPv4Address('172.31.255.255')),
        )
        return str(ipaddress.IPv4Address(ipv4_int))

    @staticmethod
    def ip_v4_private_c() -> str:
        """Return random private IPv4 address of Class C."""
        ipv4_int = random.randint(
            int(ipaddress.IPv4Address('192.168.0.0')),
            int(ipaddress.IPv4Address('192.168.255.255')),
        )
        return str(ipaddress.IPv4Address(ipv4_int))

    @staticmethod
    def ip_v4_public() -> str:
        """Return random public IPv4 address."""
        public_ranges = [
            ('1.0.0.0', '9.255.255.255'),
            ('11.0.0.0', '100.63.255.255'),
            ('100.128.0.0', '126.255.255.255'),
            ('128.0.0.0', '169.253.255.255'),
            ('169.255.0.0', '172.15.255.255'),
            ('172.32.0.0', '191.255.255.255'),
            ('192.0.1.0', '192.0.1.255'),
            ('192.0.3.0', '192.88.98.255'),
            ('192.88.100.0', '192.167.255.255'),
            ('192.169.0.0', '198.17.255.255'),
            ('198.20.0.0', '198.51.99.255'),
            ('198.51.101.0', '203.0.112.255'),
            ('203.0.114.0', '223.255.255.255'),
        ]

        start, end = random.choices(
            population=public_ranges,
            weights=[5, 8, 6, 7, 4, 9, 3, 4, 5, 6, 4, 6, 8],
            k=1,
        ).pop()
        ipv4_int = random.randint(
            int(ipaddress.IPv4Address(start)),
            int(ipaddress.IPv4Address(end)),
        )
        return str(ipaddress.IPv4Address(ipv4_int))

    @staticmethod
    def ip_v4_in_subnet(cidr: str) -> str:
        """Return random IPv4 host address within the given CIDR subnet."""
        net = ipaddress.IPv4Network(cidr, strict=False)
        prefix = net.prefixlen

        if prefix == 32:  # noqa: PLR2004
            return str(net.network_address)

        if prefix == 31:  # noqa: PLR2004
            return str(
                random.choice(
                    [net.network_address, net.broadcast_address],
                )
            )

        offset = random.randint(1, net.num_addresses - 2)
        return str(net.network_address + offset)

    @staticmethod
    def ip_v6() -> str:
        """Return random IPv6 address."""
        return str(ipaddress.IPv6Address(random.getrandbits(128)))

    @staticmethod
    def ip_v6_global() -> str:
        """Return random global unicast IPv6 address (2000::/3)."""
        net = ipaddress.IPv6Network('2000::/3')
        offset = random.randint(0, net.num_addresses - 1)
        return str(ipaddress.IPv6Address(int(net.network_address) + offset))

    @staticmethod
    def ip_v6_link_local() -> str:
        """Return random link-local IPv6 address (fe80::/10)."""
        net = ipaddress.IPv6Network('fe80::/10')
        offset = random.randint(0, net.num_addresses - 1)
        return str(ipaddress.IPv6Address(int(net.network_address) + offset))

    @staticmethod
    def ip_v6_ula() -> str:
        """Return random unique local IPv6 address (fc00::/7)."""
        net = ipaddress.IPv6Network('fc00::/7')
        offset = random.randint(0, net.num_addresses - 1)
        return str(ipaddress.IPv6Address(int(net.network_address) + offset))

    @staticmethod
    def mac(
        *,
        oui: str | None = None,
        vendor: str | None = None,
    ) -> str:
        """Return random MAC address.

        Without arguments, all six bytes are random. With `oui`, the
        given 3-byte prefix is reused and only the last three bytes
        vary; `oui` accepts ``aa:bb:cc`` or ``aa-bb-cc``. With
        `vendor`, the prefix is picked at random from a built-in OUI
        table for that vendor (case-insensitive lookup). Pass at
        most one of `oui` or `vendor`.

        Raises ``ValueError`` for an invalid `oui`, an unknown
        `vendor`, or both arguments at once.
        """
        if oui is not None and vendor is not None:
            msg = "'oui' and 'vendor' are mutually exclusive"
            raise ValueError(msg)

        if vendor is not None:
            ouis = _VENDOR_OUIS.get(vendor.lower())
            if ouis is None:
                msg = f'unknown vendor: {vendor!r}'
                raise ValueError(msg)
            oui = random.choice(ouis)

        if oui is not None:
            prefix = _parse_oui(oui)
            suffix = (random.randint(0, 0xFF) for _ in range(3))
            octets = (*prefix, *suffix)
        else:
            octets = tuple(random.randint(0, 0xFF) for _ in range(6))

        return ':'.join(f'{x:02x}' for x in octets)


class crypto:  # noqa: N801
    """Namespace for generating random cryptographic entities."""

    @staticmethod
    def uuid4() -> str:
        """Return universally unique identifier of version 4."""
        return str(uuid.uuid4())

    @staticmethod
    def md5() -> str:
        """Return random MD5 hash."""
        return f'{random.getrandbits(128):032x}'

    @staticmethod
    def sha256() -> str:
        """Return random SHA-256 hash."""
        return f'{random.getrandbits(256):064x}'


class datetime:  # noqa: N801
    """Namespace for generating random dates."""

    @staticmethod
    def timestamp(start: dt.datetime, end: dt.datetime) -> dt.datetime:
        """Return random timestamp in range [start; end]."""
        delta_seconds = (end - start).total_seconds()

        return start + dt.timedelta(seconds=random.uniform(0, delta_seconds))
