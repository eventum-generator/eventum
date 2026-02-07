"""Pickers for template picking modes."""

import random
from abc import ABC, abstractmethod
from typing import Any, ClassVar, Generic, TypeVar, override

from eventum.plugins.event.plugins.template.config import (
    TemplateConfigForChanceMode,
    TemplateConfigForFSMMode,
    TemplateConfigForGeneralModes,
    TemplatePickingMode,
)
from eventum.plugins.event.plugins.template.context import EventContext

T = TypeVar('T', bound=TemplateConfigForGeneralModes)


class TemplatePicker(ABC, Generic[T]):
    """Base picker of templates.

    Other Parameters
    ----------------
    mode : TemplatePickingMode
        Picking mode to which to bind picker class.

    """

    _registered_pickers: ClassVar[
        dict[TemplatePickingMode, type['TemplatePicker[Any]']]
    ] = {}

    def __init_subclass__(
        cls,
        mode: TemplatePickingMode,
        **kwargs: Any,
    ) -> None:
        if mode in TemplatePicker._registered_pickers:
            registered_picker = TemplatePicker._registered_pickers[mode]
            msg = (
                f'Picker {registered_picker} is already registered '
                f'for mode `{mode}`'
            )
            raise ValueError(msg)

        TemplatePicker._registered_pickers[mode] = cls

        return super().__init_subclass__(**kwargs)

    def __init__(
        self,
        config: dict[str, T],
        common_config: dict[str, Any],
    ) -> None:
        """Initialize picker.

        Parameters
        ----------
        config : dict[str, T]
            Template aliases to configs mapping.

        common_config : dict
            Common parameter names to values mapping.

        Raises
        ------
        ValueError
            If some required parameter is missing in config.

        """
        self._config = config
        self._common_config = common_config
        self._aliases = tuple(self._config.keys())

    @abstractmethod
    def pick(self, context: EventContext) -> tuple[str, ...]:
        """Pick template.

        Parameters
        ----------
        context : EventContext
            Context of event producing.

        Returns
        -------
        tuple[str, ...]
            Aliases of picked templates.

        """
        ...

    @classmethod
    def get_picker(
        cls,
        picking_mode: TemplatePickingMode,
    ) -> type['TemplatePicker[Any]']:
        """Get appropriate picker for specified picking mode.

        Parameters
        ----------
        picking_mode : TemplatePickingMode
            Picking mode.

        Returns
        -------
        type['TemplatePicker[Any]']
            Picker class.

        Raises
        ------
        ValueError
            If no appropriate picker found for specified mode.

        """
        try:
            return cls._registered_pickers[picking_mode]
        except KeyError:
            msg = f'No picker found for mode `{picking_mode}`'
            raise ValueError(msg) from None


class AllTemplatePicker(
    TemplatePicker[TemplateConfigForGeneralModes],
    mode=TemplatePickingMode.ALL,
):
    """Picker of templates for `all` picking mode."""

    @override
    def __init__(
        self,
        config: dict[str, TemplateConfigForGeneralModes],
        common_config: dict[str, Any],
    ) -> None:
        super().__init__(config, common_config)

    @override
    def pick(self, context: EventContext) -> tuple[str, ...]:
        return self._aliases


class AnyTemplatePicker(
    TemplatePicker[TemplateConfigForGeneralModes],
    mode=TemplatePickingMode.ANY,
):
    """Picker of templates for `any` picking mode."""

    @override
    def __init__(
        self,
        config: dict[str, TemplateConfigForGeneralModes],
        common_config: dict[str, Any],
    ) -> None:
        super().__init__(config, common_config)

    @override
    def pick(self, context: EventContext) -> tuple[str, ...]:
        return (random.choice(self._aliases),)


class ChanceTemplatePicker(
    TemplatePicker[TemplateConfigForChanceMode],
    mode=TemplatePickingMode.CHANCE,
):
    """Picker of templates for `chance` picking mode."""

    @override
    def __init__(
        self,
        config: dict[str, TemplateConfigForChanceMode],
        common_config: dict[str, Any],
    ) -> None:
        super().__init__(config, common_config)
        self._chances = [conf.chance for conf in self._config.values()]

    @override
    def pick(self, context: EventContext) -> tuple[str, ...]:
        return tuple(
            random.choices(self._aliases, weights=self._chances, k=1),
        )


class SpinTemplatePicker(
    TemplatePicker[TemplateConfigForGeneralModes],
    mode=TemplatePickingMode.SPIN,
):
    """Picker of templates for `spin` picking mode."""

    @override
    def __init__(
        self,
        config: dict[str, TemplateConfigForGeneralModes],
        common_config: dict[str, Any],
    ) -> None:
        super().__init__(config, common_config)
        self._spin_index = 0

    @override
    def pick(self, context: EventContext) -> tuple[str, ...]:
        alias = self._aliases[self._spin_index]

        self._spin_index += 1
        if self._spin_index == len(self._aliases):
            self._spin_index = 0

        return (alias,)


class FSMTemplatePicker(
    TemplatePicker[TemplateConfigForFSMMode],
    mode=TemplatePickingMode.FSM,
):
    """Picker of templates for `fsm` picking mode."""

    @override
    def __init__(
        self,
        config: dict[str, TemplateConfigForFSMMode],
        common_config: dict[str, Any],
    ) -> None:
        super().__init__(config, common_config)
        self._state = self._get_initial_state()
        self._initial_pick = True

    def _get_initial_state(self) -> str:
        """Get alias of initial state.

        Returns
        -------
        str
            Alias of state.

        Raises
        ------
        RuntimeError
            If no initial state found.

        """
        for alias, conf in self._config.items():
            if conf.initial:
                return alias

        msg = 'No initial state found'
        raise RuntimeError(msg)

    def _check_transition(self, context: EventContext) -> None:
        """Check condition of current state and perform transition to
        next state if it is true.

        Parameters
        ----------
        context : EventContext
            Context of event producing.

        """
        transitions = self._config[self._state].transitions

        if not transitions:
            return

        for transition in transitions:
            if transition.when.check(context):
                self._state = transition.to
                break

    @override
    def pick(self, context: EventContext) -> tuple[str, ...]:
        if self._initial_pick:
            self._initial_pick = False
        else:
            self._check_transition(context)

        return (self._state,)


class ChainTemplatePicker(
    TemplatePicker[TemplateConfigForGeneralModes],
    mode=TemplatePickingMode.CHAIN,
):
    """Picker of templates for `chain` picking mode."""

    @override
    def __init__(
        self,
        config: dict[str, TemplateConfigForGeneralModes],
        common_config: dict[str, Any],
    ) -> None:
        super().__init__(config, common_config)
        try:
            self._chain = common_config['chain']
        except KeyError as e:
            msg = f'Common config parameter `{e}` is missing'
            raise ValueError(msg) from None

        self._chain_index = 0

    @override
    def pick(self, context: EventContext) -> tuple[str, ...]:
        alias = self._chain[self._chain_index]

        self._chain_index += 1
        if self._chain_index == len(self._chain):
            self._chain_index = 0

        return (alias,)


def get_picker_class(
    picking_mode: TemplatePickingMode,
) -> type[TemplatePicker[Any]]:
    """Return specific picker class depending on picking mode.

    Parameters
    ----------
    picking_mode : TemplatePickingMode
        Picking mode.

    Returns
    -------
    type['TemplatePicker[Any]']
        Picker class.

    Raises
    ------
    ValueError
        If no appropriate picker found for specified mode.

    """
    return TemplatePicker.get_picker(picking_mode)
