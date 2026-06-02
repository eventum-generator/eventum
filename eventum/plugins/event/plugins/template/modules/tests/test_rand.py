import datetime as dt
import ipaddress
import uuid
from string import (
    ascii_letters,
    ascii_lowercase,
    ascii_uppercase,
    digits,
    punctuation,
)

import pytest

from eventum.plugins.event.plugins.template.modules import rand


# ---- General Random Functions ----
def test_shuffle():
    items = [1, 2, 3, 4, 5]
    shuffled = rand.shuffle(items)
    assert sorted(shuffled) == sorted(items)

    text = 'abcdef'
    shuffled_text = rand.shuffle(text)
    assert sorted(shuffled_text) == sorted(text)


def test_choice():
    items = ['a', 'b', 'c']
    assert rand.choice(items) in items

    with pytest.raises(IndexError):
        rand.choice([])


def test_choices():
    items = ['x', 'y', 'z']
    results = rand.choices(items, 5)
    assert len(results) == 5
    assert all(item in items for item in results)


def test_weighted_choice():
    items = ['apple', 'banana', 'cherry']
    weights = [0.1, 0.2, 0.7]
    result = rand.weighted_choice(items, weights)
    assert result in items


def test_weighted_choice_dict():
    mapping = {'apple': 0.1, 'banana': 0.2, 'cherry': 0.7}
    result = rand.weighted_choice(mapping)
    assert result in mapping


def test_weighted_choices():
    items = ['red', 'green', 'blue']
    weights = [0.5, 0.3, 0.2]
    results = rand.weighted_choices(items, weights, 5)
    assert len(results) == 5
    assert all(item in items for item in results)


def test_weighted_choices_dict():
    mapping = {'red': 0.5, 'green': 0.3, 'blue': 0.2}
    results = rand.weighted_choices(mapping, 5)
    assert len(results) == 5
    assert all(item in mapping for item in results)


def test_chance():
    assert rand.chance(0.5) in [True, False]


# ---- Number Namespace ----
def test_number_integer():
    value = rand.number.integer(1, 10)
    assert 1 <= value <= 10


def test_number_floating():
    value = rand.number.floating(1.5, 5.5)
    assert 1.5 <= value <= 5.5


def test_number_gauss():
    value = rand.number.gauss(0, 1)
    assert isinstance(value, float)


def test_number_lognormal():
    value = rand.number.lognormal(0, 1)
    assert isinstance(value, float)
    assert value > 0


def test_number_exponential():
    value = rand.number.exponential(1.0)
    assert isinstance(value, float)
    assert value > 0


def test_number_pareto():
    value = rand.number.pareto(2.0)
    assert isinstance(value, float)
    assert value >= 1.0

    value = rand.number.pareto(2.0, xmin=5.0)
    assert value >= 5.0


def test_number_triangular():
    value = rand.number.triangular(0.0, 10.0, 5.0)
    assert isinstance(value, float)
    assert 0.0 <= value <= 10.0


def test_number_clamp():
    assert rand.number.clamp(5.0, 0.0, 10.0) == 5.0
    assert rand.number.clamp(-1.0, 0.0, 10.0) == 0.0
    assert rand.number.clamp(15.0, 0.0, 10.0) == 10.0


# ---- String Namespace ----
def test_string_letters_lowercase():
    result = rand.string.letters_lowercase(10)
    assert len(result) == 10
    assert all(c in ascii_lowercase for c in result)


def test_string_letters_uppercase():
    result = rand.string.letters_uppercase(10)
    assert len(result) == 10
    assert all(c in ascii_uppercase for c in result)


def test_string_letters():
    result = rand.string.letters(10)
    assert len(result) == 10
    assert all(c in ascii_letters for c in result)


def test_string_digits():
    result = rand.string.digits(5)
    assert len(result) == 5
    assert all(c in digits for c in result)


def test_string_punctuation():
    result = rand.string.punctuation(5)
    assert len(result) == 5
    assert all(c in punctuation for c in result)


def test_string_hex():
    result = rand.string.hex(8)
    assert len(result) == 8
    assert all(c in '0123456789abcdef' for c in result)


# ---- String Pattern ----
def test_string_pattern_empty():
    assert rand.string.pattern('') == ''


def test_string_pattern_literal_only():
    assert rand.string.pattern('hello') == 'hello'


def test_string_pattern_lowercase_letter():
    result = rand.string.pattern('%a')
    assert len(result) == 1
    assert result in ascii_lowercase


def test_string_pattern_uppercase_letter():
    result = rand.string.pattern('%A')
    assert len(result) == 1
    assert result in ascii_uppercase


def test_string_pattern_any_letter():
    result = rand.string.pattern('%l{20}')
    assert len(result) == 20
    assert all(c in ascii_letters for c in result)


def test_string_pattern_digit():
    result = rand.string.pattern('%d{10}')
    assert len(result) == 10
    assert all(c in digits for c in result)


def test_string_pattern_non_zero_digit():
    result = rand.string.pattern('%n{100}')
    assert len(result) == 100
    assert all(c in '123456789' for c in result)


def test_string_pattern_hex_lower():
    result = rand.string.pattern('%h{16}')
    assert len(result) == 16
    assert all(c in '0123456789abcdef' for c in result)


def test_string_pattern_hex_upper():
    result = rand.string.pattern('%H{16}')
    assert len(result) == 16
    assert all(c in '0123456789ABCDEF' for c in result)


def test_string_pattern_punctuation():
    result = rand.string.pattern('%p{10}')
    assert len(result) == 10
    assert all(c in punctuation for c in result)


def test_string_pattern_word():
    result = rand.string.pattern('%w{30}')
    assert len(result) == 30
    assert all(c in ascii_letters + digits for c in result)


def test_string_pattern_escaped_percent():
    assert rand.string.pattern('%%') == '%'


def test_string_pattern_escaped_percent_repeated():
    assert rand.string.pattern('%%{4}') == '%%%%'


def test_string_pattern_mixed():
    result = rand.string.pattern('ID-%A{2}%d{4}')
    assert len(result) == 9
    assert result.startswith('ID-')
    assert all(c in ascii_uppercase for c in result[3:5])
    assert all(c in digits for c in result[5:])


def test_string_pattern_zero_count():
    assert rand.string.pattern('a%d{0}b') == 'ab'


def test_string_pattern_literal_braces():
    result = rand.string.pattern('{3}')
    assert result == '{3}'


def test_string_pattern_literal_braces_after_text():
    result = rand.string.pattern('size={5}')
    assert result == 'size={5}'


def test_string_pattern_no_repeat_emits_one():
    result = rand.string.pattern('%a%A%d')
    assert len(result) == 3
    assert result[0] in ascii_lowercase
    assert result[1] in ascii_uppercase
    assert result[2] in digits


def test_string_pattern_trailing_percent_raises():
    with pytest.raises(ValueError, match='trailing'):
        rand.string.pattern('abc%')


def test_string_pattern_unknown_specifier_raises():
    with pytest.raises(ValueError, match='unknown format specifier'):
        rand.string.pattern('%z')


def test_string_pattern_unclosed_brace_raises():
    with pytest.raises(ValueError, match='unclosed'):
        rand.string.pattern('%a{5')


def test_string_pattern_non_numeric_count_raises():
    with pytest.raises(ValueError, match='invalid repeat count'):
        rand.string.pattern('%a{abc}')


def test_string_pattern_negative_count_raises():
    with pytest.raises(ValueError, match='invalid repeat count'):
        rand.string.pattern('%a{-3}')


def test_string_pattern_empty_count_raises():
    with pytest.raises(ValueError, match='invalid repeat count'):
        rand.string.pattern('%a{}')


# ---- Network Namespace ----
def test_ip_v4():
    ip = rand.network.ip_v4()
    assert isinstance(ipaddress.ip_address(ip), ipaddress.IPv4Address)


def test_ip_v4_private():
    private_nets = [
        ipaddress.IPv4Network('10.0.0.0/8'),
        ipaddress.IPv4Network('172.16.0.0/12'),
        ipaddress.IPv4Network('192.168.0.0/16'),
    ]
    seen_nets: set[int] = set()
    for _ in range(200):
        ip = rand.network.ip_v4_private()
        addr = ipaddress.IPv4Address(ip)
        matched = next(
            (i for i, net in enumerate(private_nets) if addr in net),
            None,
        )
        assert matched is not None, f'{ip} not in any RFC 1918 range'
        seen_nets.add(matched)
    assert seen_nets == {0, 1, 2}, (
        f'expected all three ranges to be sampled, got {seen_nets}'
    )


def test_ip_v4_private_a():
    ip = rand.network.ip_v4_private_a()
    assert ip.startswith('10.')


def test_ip_v4_private_b():
    ip = rand.network.ip_v4_private_b()
    assert ip.startswith('172.') and 16 <= int(ip.split('.')[1]) <= 31


def test_ip_v4_private_c():
    ip = rand.network.ip_v4_private_c()
    assert ip.startswith('192.168.')


def test_ip_v4_in_subnet():
    net = ipaddress.IPv4Network('192.168.1.0/24')
    for _ in range(100):
        ip = rand.network.ip_v4_in_subnet('192.168.1.0/24')
        addr = ipaddress.IPv4Address(ip)
        assert addr in net
        assert addr != net.network_address
        assert addr != net.broadcast_address


def test_ip_v4_in_subnet_slash_31():
    ip = rand.network.ip_v4_in_subnet('10.0.0.0/31')
    assert ip in ('10.0.0.0', '10.0.0.1')


def test_ip_v4_in_subnet_slash_32():
    ip = rand.network.ip_v4_in_subnet('10.0.0.5/32')
    assert ip == '10.0.0.5'


def test_ip_v4_in_subnet_slash_0():
    ip = rand.network.ip_v4_in_subnet('0.0.0.0/0')
    ipaddress.IPv4Address(ip)


def test_ip_v4_in_subnet_invalid_cidr():
    with pytest.raises(ValueError):
        rand.network.ip_v4_in_subnet('not-a-cidr')


def test_ip_v4_public():
    ip = rand.network.ip_v4_public()
    assert isinstance(ipaddress.ip_address(ip), ipaddress.IPv4Address)


def test_ip_v6():
    ip = rand.network.ip_v6()
    assert isinstance(ipaddress.ip_address(ip), ipaddress.IPv6Address)


def test_ip_v6_global():
    ip = rand.network.ip_v6_global()
    assert ipaddress.IPv6Address(ip) in ipaddress.IPv6Network('2000::/3')


def test_ip_v6_link_local():
    ip = rand.network.ip_v6_link_local()
    assert ipaddress.IPv6Address(ip) in ipaddress.IPv6Network('fe80::/10')


def test_ip_v6_ula():
    ip = rand.network.ip_v6_ula()
    assert ipaddress.IPv6Address(ip) in ipaddress.IPv6Network('fc00::/7')


def test_mac():
    mac = rand.network.mac()
    assert len(mac.split(':')) == 6
    assert all(0 <= int(x, 16) <= 255 for x in mac.split(':'))


# ---- Crypto Namespace ----
def test_uuid4():
    assert isinstance(uuid.UUID(rand.crypto.uuid4()), uuid.UUID)


def test_md5():
    result = rand.crypto.md5()
    assert len(result) == 32
    assert all(c in '0123456789abcdef' for c in result)


def test_sha1():
    result = rand.crypto.sha1()
    assert len(result) == 40
    assert all(c in '0123456789abcdef' for c in result)


def test_sha256():
    result = rand.crypto.sha256()
    assert len(result) == 64
    assert all(c in '0123456789abcdef' for c in result)


# ---- Datetime Namespace ----
def test_timestamp():
    start = dt.datetime.fromisoformat('2022-01-01T00:00:00')
    end = dt.datetime.fromisoformat('2023-01-01T00:00:00')
    ts = rand.datetime.timestamp(start, end)

    assert start <= ts <= end
