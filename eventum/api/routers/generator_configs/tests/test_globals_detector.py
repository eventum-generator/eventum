"""Tests for AST-based globals detector."""

from eventum.api.routers.generator_configs.globals_detector import (
    detect_globals_usage,
)


def test_detect_set():
    template = '{%- do globals.set("active_users", users) -%}'
    result = detect_globals_usage(template, 'test.j2')
    assert len(result.writes) == 1
    assert result.writes[0].key == 'active_users'
    assert result.writes[0].path == 'test.j2'


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


def test_detect_unsupported_file():
    """A file that is neither a template nor a script is skipped."""
    result = detect_globals_usage('globals.set("k", 1)', 'notes.txt')
    assert len(result.writes) == 0
    assert len(result.reads) == 0
    assert len(result.warnings) == 0


def test_detect_script_set_and_get_through_bound_name():
    script = (
        'def produce(params):\n'
        "    state = params['globals']\n"
        "    state.set('pool', [1])\n"
        "    return str(state.get('counter', 0))\n"
    )
    result = detect_globals_usage(script, 'scripts/produce.py')

    assert [(w.key, w.path) for w in result.writes] == [
        ('pool', 'scripts/produce.py')
    ]
    assert [r.key for r in result.reads] == ['counter']
    assert len(result.warnings) == 0


def test_detect_script_set_on_params_directly():
    script = (
        'def produce(params):\n'
        "    params['globals'].set('pool', [1])\n"
        "    return params['globals'].get('counter')\n"
    )
    result = detect_globals_usage(script, 'produce.py')

    assert [w.key for w in result.writes] == ['pool']
    assert [r.key for r in result.reads] == ['counter']


def test_detect_script_annotated_binding():
    script = (
        'def produce(params):\n'
        "    state: object = params['globals']\n"
        "    return str(state['status'])\n"
    )
    result = detect_globals_usage(script, 'produce.py')

    assert [r.key for r in result.reads] == ['status']


def test_detect_script_getitem():
    script = (
        'def produce(params):\n'
        "    return str(params['globals']['blocked_ips'])\n"
    )
    result = detect_globals_usage(script, 'produce.py')

    assert [r.key for r in result.reads] == ['blocked_ips']


def test_detect_script_dynamic_key_warning():
    script = (
        'def produce(params):\n'
        "    state = params['globals']\n"
        '    state.set(params["tags"][0], 1)\n'
    )
    result = detect_globals_usage(script, 'produce.py')

    assert [w.type for w in result.warnings] == ['dynamic_key']
    assert len(result.writes) == 0


def test_detect_script_update_warning():
    script = "def produce(params):\n    params['globals'].update({'a': 1})\n"
    result = detect_globals_usage(script, 'produce.py')

    assert [w.type for w in result.warnings] == ['update_call']


def test_detect_script_ignores_unrelated_state():
    script = (
        'CACHE = {}\n'
        '\n'
        'def produce(params):\n'
        "    CACHE['not_a_global'] = 1\n"
        "    other = params['other']\n"
        "    other.set('nope', 1)\n"
        "    return str(params['timestamp'])\n"
    )
    result = detect_globals_usage(script, 'produce.py')

    assert len(result.writes) == 0
    assert len(result.reads) == 0
    assert len(result.warnings) == 0


def test_detect_script_with_syntax_error():
    """Invalid Python should return empty usage, not raise."""
    result = detect_globals_usage('def produce(params:', 'broken.py')

    assert len(result.writes) == 0
    assert len(result.reads) == 0
    assert len(result.warnings) == 0
