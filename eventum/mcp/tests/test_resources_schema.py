"""Tests for the generator-schema resource."""

import json

from eventum.mcp.resources.schema import render_generator_schema


def test_render_generator_schema_is_valid_json() -> None:
    """The resource renders parseable JSON Schema for an object."""
    schema = json.loads(render_generator_schema())
    assert schema['type'] == 'object'


def test_render_generator_schema_has_envelope_fields() -> None:
    """The schema exposes the input/event/output envelope."""
    schema = json.loads(render_generator_schema())
    props = schema['properties']
    assert 'input' in props
    assert 'event' in props
    assert 'output' in props
