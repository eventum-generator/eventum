from pathlib import Path

import pytest

from eventum.plugins.event.plugins.template.config import (
    TemplateConfigForChanceMode,
    TemplateConfigForFSMMode,
    TemplateConfigForGeneralModes,
    TemplatePickingMode,
    TemplateTransition,
)
from eventum.plugins.event.plugins.template.fsm.fields import Eq
from eventum.plugins.event.plugins.template.state import SingleThreadState
from eventum.plugins.event.plugins.template.template_pickers import (
    AllTemplatePicker,
    AnyTemplatePicker,
    ChainTemplatePicker,
    ChanceTemplatePicker,
    FSMTemplatePicker,
    SpinTemplatePicker,
    get_picker_class,
)


@pytest.mark.parametrize(
    'picker_class, picking_mode',
    [
        (AllTemplatePicker, TemplatePickingMode.ALL),
        (AnyTemplatePicker, TemplatePickingMode.ANY),
        (ChanceTemplatePicker, TemplatePickingMode.CHANCE),
        (SpinTemplatePicker, TemplatePickingMode.SPIN),
        (FSMTemplatePicker, TemplatePickingMode.FSM),
        (ChainTemplatePicker, TemplatePickingMode.CHAIN),
    ],
)
def test_get_picker_class(picker_class, picking_mode):
    assert get_picker_class(picking_mode) == picker_class


def test_get_picker_class_unexistent():
    with pytest.raises(ValueError):
        get_picker_class('what picker?')  # type: ignore


def test_all_template_picker():
    config = {
        'template1': TemplateConfigForGeneralModes(
            template=Path('test1.jinja')
        ),
        'template2': TemplateConfigForGeneralModes(
            template=Path('test2.jinja')
        ),
    }
    picker = AllTemplatePicker(config, {})

    assert picker.pick({}) == ('template1', 'template2')  # type: ignore


def test_any_template_picker():
    config = {
        'template1': TemplateConfigForGeneralModes(
            template=Path('test1.jinja')
        ),
        'template2': TemplateConfigForGeneralModes(
            template=Path('test2.jinja')
        ),
    }
    picker = AnyTemplatePicker(config, {})

    picked_templates = picker.pick({})  # type: ignore

    assert len(picked_templates) == 1
    assert picked_templates[0] in ('template1', 'template2')


def test_chance_template_picker():
    config = {
        'template1': TemplateConfigForChanceMode(
            template=Path('test1.jinja'), chance=0.2
        ),
        'template2': TemplateConfigForChanceMode(
            template=Path('test2.jinja'), chance=0.8
        ),
    }
    picker = ChanceTemplatePicker(config, {})

    picked_templates = picker.pick({})  # type: ignore

    assert len(picked_templates) == 1
    assert picked_templates[0] in ('template1', 'template2')


def test_spin_template_picker():
    config = {
        'template1': TemplateConfigForGeneralModes(
            template=Path('test1.jinja')
        ),
        'template2': TemplateConfigForGeneralModes(
            template=Path('test2.jinja')
        ),
        'template3': TemplateConfigForGeneralModes(
            template=Path('test3.jinja')
        ),
    }
    picker = SpinTemplatePicker(config, {})

    assert picker.pick({}) == ('template1',)  # type: ignore
    assert picker.pick({}) == ('template2',)  # type: ignore
    assert picker.pick({}) == ('template3',)  # type: ignore
    assert picker.pick({}) == ('template1',)  # type: ignore


def test_fsm_template_picker():
    config = {
        'template1': TemplateConfigForFSMMode(
            template=Path('test1.jinja'),
            initial=True,
            transitions=[
                TemplateTransition(
                    to='template2', when=Eq(eq={'shared.some_flag': True})
                )
            ],
        ),
        'template2': TemplateConfigForFSMMode(
            template=Path('test2.jinja'),
            initial=False,
            transitions=[
                TemplateTransition(
                    to='template1', when=Eq(eq={'shared.some_flag': False})
                )
            ],
        ),
    }
    picker = FSMTemplatePicker(config, {})
    state = SingleThreadState({'some_flag': False})

    assert picker.pick({'shared': state}) == ('template1',)  # type: ignore
    assert picker.pick({'shared': state}) == ('template1',)  # type: ignore
    state.set('some_flag', True)

    assert picker.pick({'shared': state}) == ('template2',)  # type: ignore
    assert picker.pick({'shared': state}) == ('template2',)  # type: ignore

    state.set('some_flag', False)

    assert picker.pick({'shared': state}) == ('template1',)  # type: ignore
    assert picker.pick({'shared': state}) == ('template1',)  # type: ignore


def test_chain_template_picker():
    config = {
        'template1': TemplateConfigForGeneralModes(
            template=Path('test1.jinja')
        ),
        'template2': TemplateConfigForGeneralModes(
            template=Path('test2.jinja')
        ),
        'template3': TemplateConfigForGeneralModes(
            template=Path('test3.jinja')
        ),
    }
    picker = ChainTemplatePicker(
        config=config,
        common_config={
            'chain': [
                'template1',
                'template1',
                'template3',
                'template2',
                'template1',
            ]
        },
    )

    assert picker.pick({}) == ('template1',)  # type: ignore
    assert picker.pick({}) == ('template1',)  # type: ignore
    assert picker.pick({}) == ('template3',)  # type: ignore
    assert picker.pick({}) == ('template2',)  # type: ignore
    assert picker.pick({}) == ('template1',)  # type: ignore
    assert picker.pick({}) == ('template1',)  # type: ignore
    assert picker.pick({}) == ('template1',)  # type: ignore
    assert picker.pick({}) == ('template3',)  # type: ignore
