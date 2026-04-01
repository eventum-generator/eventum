"""Tests for Jinja2 AST-based globals detector."""

from eventum.api.routers.generator_configs.globals_detector import (
    detect_globals_usage,
)


def test_detect_set():
    template = '{%- do globals.set("active_users", users) -%}'
    result = detect_globals_usage(template, 'test.j2')
    assert len(result.writes) == 1
    assert result.writes[0].key == 'active_users'
    assert result.writes[0].template == 'test.j2'


def test_detect_get():
    template = '{%- set users = globals.get("active_users", []) -%}'
    result = detect_globals_usage(template, 'test.j2')
    assert len(result.reads) == 1
    assert result.reads[0].key == 'active_users'


def test_detect_getitem():
    template = '{{ globals["blocked_ips"] }}'
    result = detect_globals_usage(template, 'test.j2')
    assert len(result.reads) == 1
    assert result.reads[0].key == 'blocked_ips'


def test_detect_update_warning():
    template = '{%- do globals.update(new_data) -%}'
    result = detect_globals_usage(template, 'test.j2')
    assert len(result.warnings) == 1
    assert result.warnings[0].type == 'update_call'


def test_detect_dynamic_key_warning():
    template = '{%- do globals.set(key_var, value) -%}'
    result = detect_globals_usage(template, 'test.j2')
    assert len(result.warnings) == 1
    assert result.warnings[0].type == 'dynamic_key'


def test_detect_multiple_operations():
    template = (
        '{%- do globals.set("pool", items) -%}\n'
        '{%- set x = globals.get("counter", 0) -%}\n'
        '{{ globals["status"] }}\n'
    )
    result = detect_globals_usage(template, 'multi.j2')
    assert len(result.writes) == 1
    assert len(result.reads) == 2
    assert {r.key for r in result.reads} == {'counter', 'status'}


def test_detect_no_globals():
    template = '{{ user.name }} - {{ timestamp }}'
    result = detect_globals_usage(template, 'plain.j2')
    assert len(result.writes) == 0
    assert len(result.reads) == 0
    assert len(result.warnings) == 0


def test_detect_invalid_template():
    """Invalid Jinja2 syntax should return empty usage, not raise."""
    template = '{%- this is not valid jinja2 -%}'
    result = detect_globals_usage(template, 'broken.j2')
    assert len(result.writes) == 0
    assert len(result.reads) == 0
    assert len(result.warnings) == 0
