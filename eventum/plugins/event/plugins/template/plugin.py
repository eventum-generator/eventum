"""Definition of template event plugin."""

from collections.abc import MutableMapping
from copy import copy
from threading import RLock
from typing import Any, NotRequired, override

from jinja2 import (
    BaseLoader,
    Environment,
    FileSystemLoader,
    Template,
    TemplateError,
    TemplateNotFound,
    TemplateSyntaxError,
)

from eventum.plugins.event.base.plugin import (
    EventPlugin,
    EventPluginParams,
    ProduceParams,
)
from eventum.plugins.event.exceptions import PluginProduceError
from eventum.plugins.event.plugins.template import modules
from eventum.plugins.event.plugins.template.config import (
    TemplateConfigForGeneralModes,
    TemplateEventPluginConfig,
)
from eventum.plugins.event.plugins.template.context import EventContext
from eventum.plugins.event.plugins.template.module_provider import (
    ModuleProvider,
)
from eventum.plugins.event.plugins.template.sample_reader import (
    SampleLoadError,
    SamplesReader,
)
from eventum.plugins.event.plugins.template.state import (
    MultiThreadState,
    SingleThreadState,
)
from eventum.plugins.event.plugins.template.subprocess_runner import (
    SubprocessRunner,
)
from eventum.plugins.event.plugins.template.template_pickers import (
    TemplatePicker,
    get_picker_class,
)
from eventum.plugins.exceptions import PluginConfigurationError
from eventum.utils.traceback_utils import shorten_traceback


class TemplateEventPluginParams(EventPluginParams):
    """Parameters for template event plugin.

    Attributes
    ----------
    templates_loader : BaseLoader
        Templates loader, if `None` is provided then default
        (FileSystemLoader) loader is used

    """

    templates_loader: NotRequired[BaseLoader]


class TemplateEventPlugin(
    EventPlugin[TemplateEventPluginConfig, TemplateEventPluginParams],
):
    """Event plugin for producing events using templates."""

    _JINJA_EXTENSIONS = ('jinja2.ext.do', 'jinja2.ext.loopcontrols')

    _GLOBAL_STATE = MultiThreadState(lock=RLock())

    @override
    def __init__(
        self,
        config: TemplateEventPluginConfig,
        params: TemplateEventPluginParams,
    ) -> None:
        super().__init__(config, params)

        self._logger.debug(
            'Using specified jinja extension',
            value=list(TemplateEventPlugin._JINJA_EXTENSIONS),
        )

        self._logger.debug('Loading samples')
        self._sample_reader = self._load_samples()

        self._logger.debug(
            'Initializing module provider with modules from package',
            package_name=modules.__name__,
        )
        self._module_provider = ModuleProvider(modules.__name__)

        self._logger.debug('Initializing subprocess runner')
        self._subprocess_runner = SubprocessRunner()

        self._logger.debug('Initializing shared state')
        self._shared_state = SingleThreadState()

        self._logger.debug('Connecting to global state')
        self._global_state = TemplateEventPlugin._GLOBAL_STATE

        loader = params.get('templates_loader', None)
        if loader is None:
            searchpath = str(self._base_path)
            self._logger.debug(
                (
                    'Templates loader is not provided in params, '
                    'default loader will be used with specified search path'
                ),
                path=searchpath,
            )
            loader = FileSystemLoader(searchpath)

        self._logger.debug('Initializing jinja environment')
        self._env = self._initialize_environment(
            loader=loader,
        )

        self._logger.debug('Preparing template configs')
        self._template_configs = self._get_template_configs_as_dict()

        self._logger.debug('Initializing local states of templates')
        self._template_states = {
            alias: SingleThreadState() for alias in self._template_configs
        }

        self._logger.debug('Loading templates')
        self._templates = self._load_templates()

        self._logger.debug('Initializing template picker')
        self._template_picker = self._initialize_template_picker()

        self._logger.debug('Initializing initial event context')
        # Context is created here for performance reasons (to not
        # recreate it in each call of _produce method).
        # Omitted values are filled at event producing.
        self._event_context = EventContext(
            timestamp=...,  # type: ignore[typeddict-item]
            tags=...,  # type: ignore[typeddict-item]
            locals=next(iter(self._template_states.values())),
            shared=self._shared_state,
            globals=self._global_state,
        )

    def _load_samples(self) -> SamplesReader:
        """Initialize samples reader with loading samples.

        Returns
        -------
        SampleReader
            Sample reader.

        Raises
        ------
        PluginConfigurationError
            If error occurs during sample loading.

        """
        try:
            return SamplesReader(
                config=self._config.root.samples,
                base_path=self._base_path,  # type: ignore[arg-type]
            )
        except SampleLoadError as e:
            raise PluginConfigurationError(
                str(e),
                context=e.context,
            ) from None

    def _initialize_environment(self, loader: BaseLoader) -> Environment:
        """Initialize jinja environment.

        Parameters
        ----------
        loader : BaseLoader
            Loader to use in environment.

        Returns
        -------
        Environment
            Initialized environment.

        """
        self._logger.debug(
            'Creating environment with provided loader and extensions',
        )
        env = Environment(
            loader=loader,
            extensions=TemplateEventPlugin._JINJA_EXTENSIONS,
        )

        self._logger.debug('Settings environment globals')
        env.globals['params'] = self._config.root.params
        env.globals['samples'] = self._sample_reader
        env.globals['module'] = self._module_provider
        env.globals['subprocess'] = self._subprocess_runner
        env.globals['shared'] = self._shared_state
        env.globals['globals'] = self._global_state

        return env

    def _load_templates(self) -> dict[str, Template]:
        """Load templates.

        Returns
        -------
        dict[str, Template]
            Aliases to templates mapping.

        Raises
        ------
        PluginConfigurationError
            If error occurs during template loading.

        """
        return {
            alias: self._load_template(
                # even on windows jinja requires forward slashes
                # when loading templates, so we use as_posix here
                name=conf.template.as_posix(),
                globals={'locals': self._template_states[alias]},
            )
            for alias, conf in self._template_configs.items()
        }

    def _get_template_configs_as_dict(
        self,
    ) -> dict[str, TemplateConfigForGeneralModes]:
        """Get template configs as dict.

        Returns
        -------
        dict[str, TemplateConfigForGeneralModes]
            Mapping with template configurations in values and their
            aliases in keys.

        """
        templates: dict[str, TemplateConfigForGeneralModes] = {}

        for template_item in self._config.root.templates:
            template_alias, template_conf = next(iter(template_item.items()))
            templates[template_alias] = template_conf

        return templates

    def _load_template(
        self,
        name: str,
        globals: MutableMapping[str, Any] | None = None,
    ) -> Template:
        """Load template using current environment.

        Parameters
        ----------
        name : str
            Name of the template to load.

        globals : MutableMapping[str, Any] | None, default=None
            Parameter `globals` of `Environment.get_template` method.

        Returns
        -------
        Template
            Loaded template.

        Raises
        ------
        PluginConfigurationError
            If template cannot be loaded.

        """
        try:
            return self._env.get_template(name, globals=globals)
        except TemplateNotFound:
            msg = 'Failed to load template'
            raise PluginConfigurationError(
                msg,
                context={
                    'reason': 'Template is not found',
                    'file_name': name,
                },
            ) from None
        except TemplateSyntaxError as e:
            msg = 'Failed to load template'
            raise PluginConfigurationError(
                msg,
                context={
                    'reason': f'Bad syntax in template: {e} (line {e.lineno})',
                    'file_name': name,
                },
            ) from e
        except TemplateError as e:
            msg = 'Failed to load template'
            raise PluginConfigurationError(
                msg,
                context={
                    'reason': f'Template error: {e}',
                    'file_name': name,
                },
            ) from e

    def _initialize_template_picker(self) -> TemplatePicker:
        """Initialize appropriate template picker.

        Returns
        -------
        TemplatePicker
            Template picker.

        Raises
        ------
        PluginConfigurationError
            If error occurs during picker initialization.

        """
        try:
            Picker = get_picker_class(self._config.root.mode)  # noqa: N806

            return Picker(
                config=self._template_configs,
                common_config=self._config.root.get_picking_common_fields(),
            )
        except ValueError as e:
            msg = 'Failed to configure template picker'
            raise PluginConfigurationError(
                msg,
                context={'reason': str(e)},
            ) from None

    @override
    def _produce(self, params: ProduceParams) -> list[str]:
        self._event_context['timestamp'] = params['timestamp']
        self._event_context['tags'] = params['tags']

        picked_aliases = self._template_picker.pick(self._event_context)

        if not picked_aliases:
            return []

        rendered: list[str] = []
        for alias in picked_aliases:
            template = self._templates[alias]

            try:
                event = template.render(
                    locals=self._template_states[alias],
                    vars=self._template_configs[alias].vars,
                    **params,
                )
            except Exception as e:
                msg = 'Failed to render template'
                raise PluginProduceError(
                    msg,
                    context={
                        'reason': str(e),
                        'traceback': shorten_traceback(
                            e,
                            key_phrase='rewrite_traceback_stack(source=source)',
                            start_position='after',
                        ),
                        'template_alias': alias,
                    },
                ) from e
            rendered.append(event)

        # use local state of last rendered template for next calls
        locals = self._template_states[picked_aliases[-1]]
        self._event_context['locals'] = locals

        return rendered

    @property
    def local_states(self) -> dict[str, SingleThreadState]:
        """Local states of templates."""
        return copy(self._template_states)

    @property
    def shared_state(self) -> SingleThreadState:
        """Shared state of templates."""
        return self._shared_state

    @property
    def global_state(self) -> MultiThreadState:
        """Global state of templates."""
        return self._global_state

    @property
    def subprocess_runner(self) -> SubprocessRunner:
        """Subprocess runner."""
        return self._subprocess_runner
