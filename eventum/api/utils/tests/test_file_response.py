"""Tests for file response utils."""

import pytest

from eventum.api.utils.file_response import build_file_headers

# 'sobytiya.log' spelled in Cyrillic
NON_ASCII_NAME = 'события.log'


def test_plain_name_uses_quoted_parameter():
    headers = build_file_headers('events.ndjson')

    assert (
        headers['Content-Disposition']
        == 'attachment; filename="events.ndjson"'
    )


def test_name_with_space_stays_in_quoted_parameter():
    headers = build_file_headers('sample data.csv')

    assert (
        headers['Content-Disposition']
        == 'attachment; filename="sample data.csv"'
    )


def test_non_ascii_name_ships_in_both_forms():
    headers = build_file_headers(NON_ASCII_NAME)

    assert headers['Content-Disposition'] == (
        'attachment; filename=".log"; '
        "filename*=utf-8''%D1%81%D0%BE%D0%B1%D1%8B%D1%82%D0%B8%D1%8F.log"
    )


@pytest.mark.parametrize(
    'name',
    [
        'quote".log',
        'back\\slash.log',
        'break\r\ninjected: header',
        'null\x00byte.log',
        'nested/path.log',
    ],
)
def test_header_carries_no_control_or_quoting_character(name):
    disposition = build_file_headers(name)['Content-Disposition']

    assert '\r' not in disposition
    assert '\n' not in disposition
    assert '\x00' not in disposition
    assert disposition.count('"') == 2
    assert disposition.startswith('attachment; filename="')


def test_name_left_with_nothing_falls_back():
    headers = build_file_headers('///')

    assert headers['Content-Disposition'] == 'attachment; filename="download"'


def test_non_ascii_name_with_no_ascii_left_falls_back():
    headers = build_file_headers('события')

    assert headers['Content-Disposition'] == (
        'attachment; filename="download"; '
        "filename*=utf-8''%D1%81%D0%BE%D0%B1%D1%8B%D1%82%D0%B8%D1%8F"
    )


def test_sniffing_is_forbidden():
    assert build_file_headers('events.log')['X-Content-Type-Options'] == (
        'nosniff'
    )


def test_file_shown_in_place_carries_no_disposition():
    headers = build_file_headers(None)

    assert 'Content-Disposition' not in headers
    # Whatever the file holds, the browser is told not to look for a
    # type of its own in it.
    assert headers['X-Content-Type-Options'] == 'nosniff'
