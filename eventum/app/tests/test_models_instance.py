"""Tests for instance info model."""

import platform
import socket
import sys
import sysconfig

import pytest

import eventum
from eventum.app.models.instance import InstanceInfo

# Fields whose value describes the interpreter or the machine the app
# runs on. Baking any of them into the schema as a default leaks the
# exporter's environment into the published OpenAPI document and makes
# the export unrepeatable.
ENVIRONMENT_FIELDS = (
    'python_version',
    'python_implementation',
    'python_compiler',
    'python_free_threaded',
    'python_gil_enabled',
    'platform',
    'host_name',
    'host_ip_v4',
    'boot_timestamp',
)


def test_schema_holds_no_environment_defaults():
    properties = InstanceInfo.model_json_schema()['properties']

    for field in ENVIRONMENT_FIELDS:
        assert 'default' not in properties[field], field


def test_schema_keeps_app_version_default():
    properties = InstanceInfo.model_json_schema()['properties']

    assert properties['app_version']['default'] == eventum.__version__


def test_environment_fields_are_not_required():
    schema = InstanceInfo.model_json_schema()

    assert not set(ENVIRONMENT_FIELDS) & set(schema.get('required', []))


def test_environment_fields_are_resolved_on_creation():
    info = InstanceInfo()

    assert info.python_version == platform.python_version()
    assert info.host_name == socket.gethostname()
    assert info.boot_timestamp > 0


def test_gil_fields_reflect_the_running_interpreter():
    info = InstanceInfo()

    assert info.python_free_threaded == bool(
        sysconfig.get_config_var('Py_GIL_DISABLED')
    )
    assert info.python_gil_enabled == sys._is_gil_enabled()


def test_gil_state_is_read_on_every_construction(
    monkeypatch: pytest.MonkeyPatch,
):
    # On a free threaded build the GIL can come back after startup, so a
    # poll of a freshly built model has to report the state at that
    # moment, not the one captured when the model was defined.
    monkeypatch.setattr(sys, '_is_gil_enabled', lambda: True)
    assert InstanceInfo().python_gil_enabled

    monkeypatch.setattr(sys, '_is_gil_enabled', lambda: False)
    assert not InstanceInfo().python_gil_enabled
