"""Unit tests for API-layer type relaxation (api_types module).

Tests validate that ``relax_model`` correctly transforms plugin config
models so every non-string field also accepts ``PlaceholderString``
values (``${params.*}`` / ``${secrets.*}``), while rejecting invalid
strings and preserving constraint validation for real values.
"""

from typing import Literal

import pytest
from pydantic import BaseModel, Field, ValidationError

from eventum.api.routers.generator_configs.api_types import (
    relax_model,
)
from eventum.plugins.loader import (
    load_event_plugin,
    load_input_plugin,
    load_output_plugin,
)

PH = '${params.x}'
SECRET = '${secrets.key}'


# ── helpers ──────────────────────────────────────────────────────────


def _relaxed(plugin_type: str, name: str) -> type[BaseModel]:
    loader = {
        'input': load_input_plugin,
        'event': load_event_plugin,
        'output': load_output_plugin,
    }[plugin_type]
    return relax_model(loader(name).config_cls)


def _valid(cls: type[BaseModel], data: dict) -> BaseModel:
    """Validate data and return the model instance."""
    return cls.model_validate(data)


def _rejects(cls: type[BaseModel], data: dict) -> None:
    """Assert that data is rejected."""
    with pytest.raises(ValidationError):
        cls.model_validate(data)


# ── opensearch (bool, int+Ge, list[HttpUrl], Path|None, HttpUrl|None,
#                nested model, discriminated union) ───────────────────

OS_BASE = {
    'hosts': ['https://localhost:9200'],
    'username': 'admin',
    'password': 'admin',
    'index': 'events',
    'formatter': {'format': 'plain'},
}


@pytest.fixture
def opensearch():
    return _relaxed('output', 'opensearch')


class TestOpensearchPlaceholders:
    """Opensearch config covers many type patterns."""

    def test_bool_placeholder(self, opensearch):
        _valid(opensearch, {**OS_BASE, 'verify': PH})

    def test_bool_real_value(self, opensearch):
        _valid(opensearch, {**OS_BASE, 'verify': True})

    def test_int_with_ge_placeholder(self, opensearch):
        _valid(opensearch, {**OS_BASE, 'connect_timeout': PH})

    def test_int_with_ge_valid(self, opensearch):
        _valid(opensearch, {**OS_BASE, 'connect_timeout': 5})

    def test_int_with_ge_below_constraint_rejected(self, opensearch):
        _rejects(opensearch, {**OS_BASE, 'connect_timeout': 0})

    def test_list_elements_placeholder(self, opensearch):
        _valid(opensearch, {
            **OS_BASE,
            'hosts': ['https://node1:9200', PH],
        })

    def test_list_all_elements_placeholder(self, opensearch):
        _valid(opensearch, {
            **OS_BASE,
            'hosts': [PH, '${params.host2}'],
        })

    def test_list_entire_field_placeholder(self, opensearch):
        _valid(opensearch, {**OS_BASE, 'hosts': PH})

    def test_nested_model_placeholder(self, opensearch):
        _valid(opensearch, {**OS_BASE, 'formatter': PH})

    def test_json_formatter_placeholder_indent(self, opensearch):
        _valid(opensearch, {
            **OS_BASE,
            'formatter': {'format': 'json', 'indent': PH},
        })

    def test_template_formatter_placeholder_path(self, opensearch):
        _valid(opensearch, {
            **OS_BASE,
            'formatter': {'format': 'template', 'template': PH},
        })

    def test_optional_path_placeholder(self, opensearch):
        _valid(opensearch, {**OS_BASE, 'ca_cert': PH})

    def test_optional_path_none(self, opensearch):
        _valid(opensearch, {**OS_BASE, 'ca_cert': None})

    def test_optional_path_real_value(self, opensearch):
        _valid(opensearch, {**OS_BASE, 'ca_cert': '/etc/ssl/ca.pem'})

    def test_optional_url_placeholder(self, opensearch):
        _valid(opensearch, {**OS_BASE, 'proxy_url': PH})

    def test_all_required_as_placeholders(self, opensearch):
        _valid(opensearch, {
            'hosts': [PH],
            'username': SECRET,
            'password': SECRET,
            'index': PH,
            'formatter': PH,
        })


# ── cron (int+Gt, tuple, TypeAlias Union|None) ──────────────────────


@pytest.fixture
def cron():
    return _relaxed('input', 'cron')


class TestCronPlaceholders:
    """Cron config covers int+Gt, tuple, TypeAlias in Union."""

    def test_int_with_gt_placeholder(self, cron):
        _valid(cron, {'expression': '* * * * *', 'count': PH})

    def test_int_with_gt_valid(self, cron):
        _valid(cron, {'expression': '* * * * *', 'count': 5})

    def test_int_with_gt_at_boundary_rejected(self, cron):
        _rejects(cron, {'expression': '* * * * *', 'count': 0})

    def test_tuple_placeholder(self, cron):
        _valid(cron, {
            'expression': '* * * * *', 'count': 1, 'tags': PH,
        })

    def test_tuple_real_value(self, cron):
        _valid(cron, {
            'expression': '* * * * *', 'count': 1, 'tags': ('a', 'b'),
        })

    def test_type_alias_union_none_placeholder(self, cron):
        _valid(cron, {
            'expression': '* * * * *', 'count': 1, 'start': PH,
        })

    def test_type_alias_union_none_value(self, cron):
        _valid(cron, {
            'expression': '* * * * *',
            'count': 1,
            'start': '2026-01-01T00:00:00',
        })

    def test_type_alias_union_none_null(self, cron):
        _valid(cron, {
            'expression': '* * * * *', 'count': 1, 'start': None,
        })


# ── http input (int+Ge+Le, str+MinLen) ──────────────────────────────


@pytest.fixture
def http_input():
    return _relaxed('input', 'http')


class TestHttpInputPlaceholders:
    """HTTP input covers multiple constraints (Ge + Le) on port."""

    def test_port_placeholder(self, http_input):
        _valid(http_input, {'host': '0.0.0.0', 'port': PH})

    def test_port_valid(self, http_input):
        _valid(http_input, {'host': '0.0.0.0', 'port': 8080})

    def test_port_below_ge_rejected(self, http_input):
        _rejects(http_input, {'host': '0.0.0.0', 'port': -1})

    def test_port_above_le_rejected(self, http_input):
        _rejects(http_input, {'host': '0.0.0.0', 'port': 70000})


# ── timer (float+Ge) ────────────────────────────────────────────────


@pytest.fixture
def timer():
    return _relaxed('input', 'timer')


class TestTimerPlaceholders:
    """Timer covers float with Ge constraint."""

    def test_float_ge_placeholder(self, timer):
        _valid(timer, {'seconds': PH, 'count': 1})

    def test_float_ge_valid(self, timer):
        _valid(timer, {'seconds': 0.5, 'count': 1})

    def test_float_ge_negative_rejected(self, timer):
        _rejects(timer, {'seconds': -1.0, 'count': 1})


# ── clickhouse (ClickHouseDsn, Literal, TypeAlias StrEnum) ──────────


@pytest.fixture
def clickhouse():
    return _relaxed('output', 'clickhouse')


CH_BASE = {
    'host': 'localhost',
    'table': 'events',
    'formatter': {'format': 'plain'},
}


class TestClickhousePlaceholders:
    """ClickHouse covers special Pydantic URL types and TypeAliases."""

    def test_dsn_placeholder(self, clickhouse):
        _valid(clickhouse, {**CH_BASE, 'dsn': PH})

    def test_literal_placeholder(self, clickhouse):
        _valid(clickhouse, {**CH_BASE, 'protocol': PH})

    def test_type_alias_enum_placeholder(self, clickhouse):
        _valid(clickhouse, {**CH_BASE, 'input_format': PH})


# ── file output (TypeAlias Encoding, Literal write_mode) ────────────


@pytest.fixture
def file_output():
    return _relaxed('output', 'file')


class TestFileOutputPlaceholders:
    """File output covers Encoding TypeAlias and Literal."""

    def test_encoding_alias_placeholder(self, file_output):
        _valid(file_output, {
            'path': 'out.log',
            'formatter': {'format': 'plain'},
            'encoding': PH,
        })

    def test_encoding_alias_real_value(self, file_output):
        _valid(file_output, {
            'path': 'out.log',
            'formatter': {'format': 'plain'},
            'encoding': 'utf_8',
        })

    def test_write_mode_literal_placeholder(self, file_output):
        _valid(file_output, {
            'path': 'out.log',
            'formatter': {'format': 'plain'},
            'write_mode': PH,
        })


# ── replay event (Path) ─────────────────────────────────────────────


@pytest.fixture
def replay():
    return _relaxed('event', 'replay')


class TestReplayPlaceholders:
    """Replay covers Path field."""

    def test_path_placeholder(self, replay):
        _valid(replay, {'path': PH})

    def test_path_real_value(self, replay):
        _valid(replay, {'path': '/data/events.log'})


# ── timestamps input (Union[list[datetime], Path]) ──────────────────


@pytest.fixture
def timestamps():
    return _relaxed('input', 'timestamps')


class TestTimestampsPlaceholders:
    """Timestamps covers Union[list, Path] field."""

    def test_source_placeholder(self, timestamps):
        _valid(timestamps, {'source': PH})

    def test_source_path(self, timestamps):
        _valid(timestamps, {'source': '/data/ts.txt'})


# ── placeholder string validation ───────────────────────────────────


class TestPlaceholderValidation:
    """PlaceholderString rejects non-placeholder strings."""

    def test_params_placeholder_accepted(self, opensearch):
        _valid(opensearch, {**OS_BASE, 'verify': '${params.verify}'})

    def test_secrets_placeholder_accepted(self, opensearch):
        _valid(opensearch, {
            **OS_BASE,
            'password': '${secrets.password}',
        })

    def test_invalid_namespace_rejected(self, opensearch):
        _rejects(opensearch, {
            **OS_BASE,
            'connect_timeout': '${invalid.x}',
        })

    def test_random_string_rejected(self, opensearch):
        _rejects(opensearch, {
            **OS_BASE,
            'connect_timeout': 'not_a_placeholder',
        })

    def test_empty_string_in_non_str_field_rejected(self, opensearch):
        _rejects(opensearch, {**OS_BASE, 'verify': ''})

    def test_partial_placeholder_rejected(self, opensearch):
        _rejects(opensearch, {
            **OS_BASE,
            'connect_timeout': '${params}',
        })


# ── relax_model caching ─────────────────────────────────────────────


class TestRelaxModelCaching:
    """Verify that relax_model returns the same object for the same
    input class (caching works)."""

    def test_same_class_returns_same_result(self):
        cls = load_output_plugin('opensearch').config_cls
        r1 = relax_model(cls)
        r2 = relax_model(cls)
        assert r1 is r2

    def test_different_classes_return_different_results(self):
        os_cls = load_output_plugin('opensearch').config_cls
        ch_cls = load_output_plugin('clickhouse').config_cls
        assert relax_model(os_cls) is not relax_model(ch_cls)


# ── relax_model with synthetic models ────────────────────────────────


class TestRelaxModelSynthetic:
    """Test relax_model with small synthetic Pydantic models to
    isolate specific type patterns."""

    def test_int_field_accepts_placeholder(self):
        class M(BaseModel):
            x: int

        relaxed = relax_model(M)
        assert _valid(relaxed, {'x': PH})
        assert _valid(relaxed, {'x': 42})

    def test_str_field_unchanged(self):
        class M(BaseModel):
            x: str

        relaxed = relax_model(M)
        assert _valid(relaxed, {'x': 'any_string'})
        assert _valid(relaxed, {'x': PH})

    def test_optional_int_placeholder(self):
        class M(BaseModel):
            x: int | None = None

        relaxed = relax_model(M)
        assert _valid(relaxed, {'x': PH})
        assert _valid(relaxed, {'x': 42})
        assert _valid(relaxed, {'x': None})

    def test_int_ge_constraint_scoped(self):
        class M(BaseModel):
            x: int = Field(ge=1)

        relaxed = relax_model(M)
        assert _valid(relaxed, {'x': PH})
        assert _valid(relaxed, {'x': 5})
        _rejects(relaxed, {'x': 0})

    def test_int_ge_le_both_constraints(self):
        class M(BaseModel):
            x: int = Field(ge=0, le=100)

        relaxed = relax_model(M)
        assert _valid(relaxed, {'x': PH})
        assert _valid(relaxed, {'x': 50})
        _rejects(relaxed, {'x': -1})
        _rejects(relaxed, {'x': 101})

    def test_nested_model_placeholder(self):
        class Inner(BaseModel):
            val: int

        class Outer(BaseModel):
            inner: Inner

        relaxed = relax_model(Outer)
        assert _valid(relaxed, {'inner': PH})
        assert _valid(relaxed, {'inner': {'val': 1}})
        assert _valid(relaxed, {'inner': {'val': PH}})

    def test_list_of_int_placeholder(self):
        class M(BaseModel):
            xs: list[int]

        relaxed = relax_model(M)
        assert _valid(relaxed, {'xs': [1, PH, 3]})
        assert _valid(relaxed, {'xs': PH})

    def test_dict_field_unchanged(self):
        class M(BaseModel):
            d: dict[str, int]

        relaxed = relax_model(M)
        assert _valid(relaxed, {'d': {'a': 1}})

    def test_literal_placeholder(self):
        class M(BaseModel):
            mode: Literal['a', 'b']

        relaxed = relax_model(M)
        assert _valid(relaxed, {'mode': PH})
        assert _valid(relaxed, {'mode': 'a'})
        _rejects(relaxed, {'mode': 'c'})

    def test_default_preserved(self):
        class M(BaseModel):
            x: int = 42

        relaxed = relax_model(M)
        m = _valid(relaxed, {})
        assert m.x == 42  # type: ignore[union-attr]

    def test_default_none_preserved(self):
        class M(BaseModel):
            x: int | None = None

        relaxed = relax_model(M)
        m = _valid(relaxed, {})
        assert m.x is None
