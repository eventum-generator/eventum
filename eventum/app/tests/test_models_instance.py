"""Tests for instance info model."""

import platform
import socket

import eventum
from eventum.app.models.instance import InstanceInfo

# Fields whose value describes the machine the app runs on. Baking any
# of them into the schema as a default leaks the exporter's environment
# into the published OpenAPI document and makes the export unrepeatable.
ENVIRONMENT_FIELDS = (
    'python_version',
    'python_implementation',
    'python_compiler',
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
