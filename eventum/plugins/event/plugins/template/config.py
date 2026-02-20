"""Definition of template event plugin config."""

from enum import StrEnum
from pathlib import Path
from typing import Any, Literal, Self, override

from pydantic import (
    BaseModel,
    Field,
    RootModel,
    field_validator,
    model_validator,
)

from eventum.plugins.event.base.config import EventPluginConfig
from eventum.plugins.event.plugins.template.fsm.fields import Condition
from eventum.plugins.event.plugins.template.mixins import (
    TemplateAliasesUniquenessValidatorMixin,
    TemplateSingleItemElementsValidatorMixin,
)


class SampleType(StrEnum):
    """Types of sample."""

    ITEMS = 'items'
    CSV = 'csv'
    JSON = 'json'


class ItemsSampleConfig(BaseModel, frozen=True, extra='forbid'):
    """Configuration of sample of directly provided items.

    Attributes
    ----------
    type : Literal[SampleType.CSV]
        Discriminator field for sample configuration.

    source : tuple
        List of sample items.

    """

    type: Literal[SampleType.ITEMS]
    source: tuple = Field(min_length=1)


class CSVSampleConfig(BaseModel, frozen=True, extra='forbid'):
    """Configuration of csv sample.

    Attributes
    ----------
    type : Literal[SampleType.CSV]
        Discriminator field for sample configuration.

    header : bool, default=False
        Whether the provided csv sample includes header.

    delimiter : str, default=','
        Delimiter for csv values.

    source : Path
        Path to csv file.

    """

    type: Literal[SampleType.CSV]
    header: bool = False
    delimiter: str = Field(default=',', min_length=1)
    source: Path

    @field_validator('source')
    @classmethod
    def validate_csv_extension(cls, v: Path) -> Path:  # noqa: D102
        if v.suffix != '.csv':
            msg = 'CSV sample source must have .csv extension'
            raise ValueError(msg)
        return v


class JSONSampleConfig(BaseModel, frozen=True, extra='forbid'):
    """Configuration of json sample.

    Attributes
    ----------
    type : Literal[SampleType.JSON]
        Discriminator field for sample configuration.

    source : Path
        Path to json file.

    """

    type: Literal[SampleType.JSON]
    source: Path

    @field_validator('source')
    @classmethod
    def validate_json_extension(cls, v: Path) -> Path:  # noqa: D102
        if v.suffix != '.json':
            msg = 'JSON sample source must have .json extension'
            raise ValueError(msg)
        return v


SampleConfigModel = ItemsSampleConfig | CSVSampleConfig | JSONSampleConfig


class SampleConfig(RootModel, frozen=True):
    """Configuration of sample."""

    root: SampleConfigModel = Field(
        discriminator='type',
    )


class TemplatePickingMode(StrEnum):
    """Picking modes of templates.

    - `all` - render all templates at a time;
    - `any` - render one randomly chosen template;
    - `chance` - render one template depending on specified chances;
    - `spin` - cyclically render one template after another;
    - `fsm` - render template depending on current state;
    - `chain` - cyclically render templates by user defined chain;
    """

    ALL = 'all'
    ANY = 'any'
    CHANCE = 'chance'
    SPIN = 'spin'
    FSM = 'fsm'
    CHAIN = 'chain'


class TemplateConfigForGeneralModes(BaseModel, frozen=True, extra='forbid'):
    """Template configuration for general picking modes.

    Attributes
    ----------
    template : Path
        Path to template.

    """

    template: Path

    @field_validator('template')
    @classmethod
    def validate_template_path(cls, v: Path) -> Path:  # noqa: D102
        if v.is_absolute():
            msg = 'Template path must be relative'
            raise ValueError(msg)
        if v.suffix != '.jinja':
            msg = 'Template path must have .jinja extension'
            raise ValueError(msg)
        return v


class TemplateConfigForChanceMode(TemplateConfigForGeneralModes, frozen=True):
    """Template configuration for `chance` picking mode.

    Attributes
    ----------
    chance : float
        Proportional value of probability of rendering template.

    """

    chance: float = Field(gt=0.0)


class TemplateTransition(BaseModel, frozen=True, extra='forbid'):
    """Transition configuration for `fsm` picking mode.

    Attributes
    ----------
    to : str
        Name of target state for transition.

    when : Condition
        Condition for performing transition.

    """

    to: str = Field(min_length=1)
    when: Condition


class TemplateConfigForFSMMode(TemplateConfigForGeneralModes, frozen=True):
    """Template configuration for `fsm` picking mode.

    Attributes
    ----------
    transitions : list[TemplateTransition], default=[]
        Transition configurations.

    initial : bool, default=False
        Whether to define state as initial.

    """

    transitions: list[TemplateTransition] = Field(default_factory=list)
    initial: bool = False


class TemplateEventPluginConfigCommonFields(
    EventPluginConfig,
    frozen=True,
):
    """Configuration common fields for `template` event plugin.

    Attributes
    ----------
    params : dict[str, Any]
        Constant parameters passed to templates.

    sample : dict[str, SampleConfig]
        Samples passed to templates.

    """

    params: dict[str, Any] = Field(default_factory=dict)
    samples: dict[str, SampleConfig] = Field(default_factory=dict)

    def get_picking_common_fields(self) -> dict[str, Any]:
        """Get common fields used in templates picking.

        Returns
        -------
        dict[str, Any]
            Field names to their values mapping.

        """
        return {}


class TemplateEventPluginConfigForGeneralModes(
    TemplateSingleItemElementsValidatorMixin,
    TemplateAliasesUniquenessValidatorMixin,
    TemplateEventPluginConfigCommonFields,
    frozen=True,
):
    """Configuration for `template` event plugin for general picking
    modes.

    Attributes
    ----------
    mode : Literal[\
        TemplatePickingMode.ALL,\
        TemplatePickingMode.ANY,\
        TemplatePickingMode.SPIN\
    ]
        Template picking mode.

    templates : list[dict[str, TemplateConfigForGeneralModes]]
        List of template configurations.

    """

    mode: Literal[
        TemplatePickingMode.ALL,
        TemplatePickingMode.ANY,
        TemplatePickingMode.SPIN,
    ]
    templates: list[dict[str, TemplateConfigForGeneralModes]] = Field(
        min_length=1,
    )


class TemplateEventPluginConfigForChanceMode(
    TemplateSingleItemElementsValidatorMixin,
    TemplateAliasesUniquenessValidatorMixin,
    TemplateEventPluginConfigCommonFields,
    frozen=True,
):
    """Configuration for `template` event plugin for `chance` picking
    mode.

    Attributes
    ----------
    mode : Literal[TemplatePickingMode.CHANCE]
        Template picking mode.

    templates : list[dict[str, TemplateConfigForChanceMode]]
        List of template configurations.

    """

    mode: Literal[TemplatePickingMode.CHANCE]
    templates: list[dict[str, TemplateConfigForChanceMode]] = Field(
        min_length=1,
    )


class TemplateEventPluginConfigForFSMMode(
    TemplateSingleItemElementsValidatorMixin,
    TemplateAliasesUniquenessValidatorMixin,
    TemplateEventPluginConfigCommonFields,
    frozen=True,
):
    """Configuration for `template` event plugin for `fsm` picking mode.

    Attributes
    ----------
    mode : Literal[TemplatePickingMode.FSM]
        Template picking mode.

    templates : list[dict[str, TemplateConfigForFSMMode]]
        List of template configurations.

    """

    mode: Literal[TemplatePickingMode.FSM]
    templates: list[dict[str, TemplateConfigForFSMMode]] = Field(min_length=1)

    @field_validator('templates')
    @classmethod
    def validate_single_initial(  # noqa: D102
        cls,
        v: list[dict[str, TemplateConfigForFSMMode]],
    ) -> list[dict[str, TemplateConfigForFSMMode]]:
        initial_encountered = False
        for template_info in v:
            config = next(iter(template_info.values()))

            if config.initial and initial_encountered:
                msg = 'Only one template can be initial'
                raise ValueError(msg)

            if config.initial:
                initial_encountered = True

        return v


class TemplateEventPluginConfigForChainMode(
    TemplateSingleItemElementsValidatorMixin,
    TemplateAliasesUniquenessValidatorMixin,
    TemplateEventPluginConfigCommonFields,
    frozen=True,
):
    """Configuration for `template` event plugin for `chain` picking
    mode.

    Attributes
    ----------
    mode : Literal[TemplatePickingMode.CHAIN]
        Template picking mode.

    templates : list[dict[str, TemplateConfigForGeneralModes]]
        List of template configurations.

    """

    mode: Literal[TemplatePickingMode.CHAIN]
    chain: list[str] = Field(min_length=1)
    templates: list[dict[str, TemplateConfigForGeneralModes]] = Field(
        min_length=1,
    )

    @model_validator(mode='after')
    def validate_chain_aliases(self) -> Self:  # noqa: D102
        allowed_aliases = {
            next(iter(template_info.keys()))
            for template_info in self.templates
        }
        chain_aliases = set(self.chain)

        if not allowed_aliases.issuperset(chain_aliases):
            unknown_aliases = allowed_aliases - chain_aliases
            msg = f'Unknown template aliases in chain: {unknown_aliases} '
            raise ValueError(msg)

        return self

    @override
    def get_picking_common_fields(self) -> dict[str, Any]:
        fields = super().get_picking_common_fields()
        fields['chain'] = self.chain

        return fields


ConfigModel = (
    TemplateEventPluginConfigForGeneralModes
    | TemplateEventPluginConfigForChanceMode
    | TemplateEventPluginConfigForFSMMode
    | TemplateEventPluginConfigForChainMode
)


class TemplateEventPluginConfig(RootModel, frozen=True):
    """Configuration for `template` event plugin."""

    root: ConfigModel = Field(discriminator='mode')
