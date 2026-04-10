# type: ignore
from datetime import datetime

import pytest
from jinja2 import DictLoader

from eventum.plugins.event.exceptions import (
    PluginExhaustedError,
    PluginProduceError,
)
from eventum.plugins.event.plugins.template.config import (
    TemplateConfigForGeneralModes,
    TemplateEventPluginConfig,
    TemplateEventPluginConfigForGeneralModes,
    TemplatePickingMode,
)
from eventum.plugins.event.plugins.template.plugin import (
    TemplateEventPlugin,
)

PRODUCE_PARAMS = {
    'tags': (),
    'timestamp': datetime.now().astimezone(),
}


def _make_plugin(
    templates: dict[str, str],
    mode: TemplatePickingMode = TemplatePickingMode.ALL,
    params: dict | None = None,
) -> TemplateEventPlugin:
    """Create a plugin with DictLoader templates."""
    template_configs = [
        {alias: TemplateConfigForGeneralModes(template=f'{alias}.jinja')}
        for alias in templates
    ]
    return TemplateEventPlugin(
        config=TemplateEventPluginConfig(
            root=TemplateEventPluginConfigForGeneralModes(
                params=params or {},
                samples={},
                mode=mode,
                templates=template_configs,
            )
        ),
        params={
            'id': 1,
            'templates_loader': DictLoader(
                mapping={
                    f'{alias}.jinja': body for alias, body in templates.items()
                }
            ),
        },
    )


class TestDispatchDrop:
    def test_drop_returns_empty(self):
        plugin = _make_plugin(
            templates={'t': '{% do dispatch.drop() %}'},
            mode=TemplatePickingMode.ANY,
        )
        events = plugin.produce(params=PRODUCE_PARAMS)
        assert events == []

    def test_drop_increments_dropped_counter(self):
        plugin = _make_plugin(
            templates={'t': '{% do dispatch.drop() %}'},
            mode=TemplatePickingMode.ANY,
        )
        plugin.produce(params=PRODUCE_PARAMS)
        assert plugin.dropped == 1

    def test_drop_in_all_mode_discards_all(self):
        """In ALL mode, drop in second template discards
        first template's output too.
        """
        plugin = _make_plugin(
            templates={
                'a': 'rendered',
                'b': '{% do dispatch.drop() %}',
            },
            mode=TemplatePickingMode.ALL,
        )
        events = plugin.produce(params=PRODUCE_PARAMS)
        assert events == []


class TestDispatchExhaust:
    def test_exhaust_raises_exhausted(self):
        plugin = _make_plugin(
            templates={'t': '{% do dispatch.exhaust() %}'},
            mode=TemplatePickingMode.ANY,
        )
        with pytest.raises(PluginExhaustedError):
            plugin.produce(params=PRODUCE_PARAMS)


class TestDispatchNext:
    def test_next_triggers_repick(self):
        plugin = _make_plugin(
            templates={
                't': (
                    '{%- if locals.get("repicked") -%}'
                    'ok'
                    '{%- else -%}'
                    '{%- do locals.set("repicked", true) -%}'
                    '{%- do dispatch.next() -%}'
                    '{%- endif -%}'
                ),
            },
            mode=TemplatePickingMode.SPIN,
        )
        events = plugin.produce(params=PRODUCE_PARAMS)
        assert events == ['ok']

    def test_next_max_repicks_exceeded(self):
        plugin = _make_plugin(
            templates={
                't': '{% do dispatch.next(max_repicks=2) %}',
            },
            mode=TemplatePickingMode.SPIN,
        )
        with pytest.raises(PluginProduceError):
            plugin.produce(params=PRODUCE_PARAMS)

    def test_next_invalid_max_repicks(self):
        plugin = _make_plugin(
            templates={
                't': '{% do dispatch.next(max_repicks=0) %}',
            },
            mode=TemplatePickingMode.SPIN,
        )
        with pytest.raises(PluginProduceError):
            plugin.produce(params=PRODUCE_PARAMS)

    def test_next_updates_locals_for_picker(self):
        """Verify event_context['locals'] is updated before re-pick."""
        plugin = _make_plugin(
            templates={
                't': (
                    '{%- if locals.get("attempt") -%}'
                    'done'
                    '{%- else -%}'
                    '{%- do locals.set("attempt", true) -%}'
                    '{%- do dispatch.next() -%}'
                    '{%- endif -%}'
                ),
            },
            mode=TemplatePickingMode.SPIN,
        )
        events = plugin.produce(params=PRODUCE_PARAMS)
        assert events == ['done']
        assert plugin._event_context['locals'].get('attempt') is True


class TestDispatchStatePersistence:
    def test_state_persists_on_drop(self):
        plugin = _make_plugin(
            templates={
                't': (
                    '{%- do shared.set("marker", "persisted") -%}'
                    '{%- do dispatch.drop() -%}'
                ),
            },
            mode=TemplatePickingMode.ANY,
        )
        plugin.produce(params=PRODUCE_PARAMS)
        assert plugin._shared_state.get('marker') == 'persisted'
