"""Formatters for output events."""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import (
    Any,
    ClassVar,
    Generic,
    Required,
    TypedDict,
    TypeVar,
    override,
)

import msgspec
from jinja2 import (
    BaseLoader,
    Environment,
    FileSystemLoader,
    Template,
    TemplateError,
    TemplateNotFound,
)

from eventum.plugins.output.exceptions import FormatError
from eventum.plugins.output.fields import (
    BaseFormatterConfig,
    Format,
    JsonFormatterConfig,
    SimpleFormatterConfig,
    TemplateFormatterConfig,
)


@dataclass(frozen=True, slots=True)
class FormattingResult:
    """Resulting data of formatting.

    Parameters
    ----------
    events : list[str]
        List of formatted events, number of events can be the same as
        original or not due to formatting errors of specific events
        from the entire provided list or reduction behavior of specific
        formatters which take multiple events and produce for example
        one aggregated event.

    formatted_count : int
        Number of successfully formatted events, this field is helpful
        for tracking number of successfully formatted events with taking
        into account possible events aggregation.

    errors : list[FormatError]
        List with formatting errors of specific events or entire
        sequence of events (for specific aggregating formatters).

    """

    events: list[str]
    formatted_count: int
    errors: list[FormatError]


T = TypeVar('T', bound=BaseFormatterConfig)


class FormatterParams(TypedDict):
    """Parameters for formatter.

    Attributes
    ----------
    base_path : Required[Path]
        Base path for all relative paths in formatter configs.

    """

    base_path: Required[Path]


class Formatter(ABC, Generic[T]):
    """Base formatter.

    Other Parameters
    ----------------
    format : Format
        Format to which to bind formatter class.

    """

    _registered_formatters: ClassVar[dict[Format, type[Formatter[Any]]]] = {}

    def __init_subclass__(cls, format: Format, **kwargs: Any) -> None:
        if format in Formatter._registered_formatters:
            registered_formatter = Formatter._registered_formatters[format]
            msg = (
                f'Formatter {registered_formatter} is already registered '
                f'for format `{format}`'
            )
            raise ValueError(msg)

        Formatter._registered_formatters[format] = cls

        return super().__init_subclass__(**kwargs)

    def __init__(self, config: T, params: FormatterParams) -> None:
        """Initialize formatter.

        Parameters
        ----------
        config : T
            Formatter config.

        params : FormatterParams
            Formatter params.

        Raises
        ------
        ValueError
            If any error occurs during formatter initialization for
            parameters specified in provided config.

        """
        self._config = config
        self._params = params

    @abstractmethod
    def format_events(self, events: Sequence[str]) -> FormattingResult:
        """Format events.

        Parameters
        ----------
        events : Sequence[str]
            Events to format.

        Returns
        -------
        FormattingResult
            Result of events formatting.

        """
        ...

    @classmethod
    def get_formatter(cls, format: Format) -> type[Formatter[Any]]:
        """Get appropriate formatter for specified format.

        Parameters
        ----------
        format : Format
            Format.

        Returns
        -------
        type['Formatter[Any]']
            Formatter.

        Raises
        ------
        ValueError
            If no appropriate formatter found for format.

        """
        try:
            return cls._registered_formatters[format]
        except KeyError:
            msg = f'No formatter found for format `{format}`'
            raise ValueError(msg) from None


class PlainFormatter(Formatter[SimpleFormatterConfig], format=Format.PLAIN):
    """Formatter that preserves original format of events."""

    @override
    def __init__(
        self,
        config: SimpleFormatterConfig,
        params: FormatterParams,
    ) -> None:
        super().__init__(config, params)

    @override
    def format_events(self, events: Sequence[str]) -> FormattingResult:
        return FormattingResult(
            events=list(events),
            formatted_count=len(events),
            errors=[],
        )


class JsonFormatter(Formatter[JsonFormatterConfig], format=Format.JSON):
    """Formatter that formats events as JSON."""

    @override
    def __init__(
        self,
        config: JsonFormatterConfig,
        params: FormatterParams,
    ) -> None:
        super().__init__(config, params)

    @override
    def format_events(self, events: Sequence[str]) -> FormattingResult:
        formatted_events: list[str] = []
        errors: list[FormatError] = []

        for event in events:
            try:
                formatted_events.append(
                    msgspec.json.format(event, indent=self._config.indent),
                )
            except msgspec.DecodeError as e:
                errors.append(FormatError(str(e), original_event=event))

        return FormattingResult(
            events=formatted_events,
            formatted_count=len(formatted_events),
            errors=errors,
        )


class JsonBatchFormatter(
    Formatter[JsonFormatterConfig],
    format=Format.JSON_BATCH,
):
    """Formatter that formats events into a single JSON list."""

    @override
    def __init__(
        self,
        config: JsonFormatterConfig,
        params: FormatterParams,
    ) -> None:
        super().__init__(config, params)

    @override
    def format_events(self, events: Sequence[str]) -> FormattingResult:
        validated_events: list[str] = []
        errors: list[FormatError] = []

        for event in events:
            try:
                validated_events.append(msgspec.json.format(event, indent=-1))
            except msgspec.DecodeError as e:
                errors.append(FormatError(str(e), original_event=event))

        event = msgspec.json.format(
            f'[{",".join(validated_events)}]',
            indent=self._config.indent,
        )

        return FormattingResult(
            events=[event],
            formatted_count=len(validated_events),
            errors=errors,
        )


def _load_template_from_string(template: str) -> Template:
    """Load template from string.

    Parameters
    ----------
    template : str
        Template source.

    Returns
    -------
    Template
        Loaded template.

    Raises
    ------
    ValueError
        If template cannot be loaded.

    """
    env = Environment(loader=BaseLoader())

    try:
        return env.from_string(template)
    except TemplateError as e:
        msg = f'Cannot load template: {e}'
        raise ValueError(msg) from e


def _load_template_from_file(base_dir: Path, template_path: Path) -> Template:
    """Load template from file.

    Parameters
    ----------
    base_dir : Path
        Base dir for resolving relative template path.

    template_path : Path
        Relative path to file with template source.

    Returns
    -------
    Template
        Loaded template.

    Raises
    ------
    ValueError
        If `base_dir` is relative or `template_path` is absolute.

    ValueError
        If template is not found or cannot be loaded.

    """
    if not base_dir.is_absolute():
        msg = 'Base dir must be absolute'
        raise ValueError(msg)

    if template_path.is_absolute():
        msg = 'Template path must be relative'
        raise ValueError(msg)

    env = Environment(
        loader=FileSystemLoader(searchpath=base_dir),
    )
    try:
        return env.get_template(template_path.as_posix())
    except TemplateNotFound:
        msg = 'Template is not found'
        raise ValueError(msg) from None
    except TemplateError as e:
        msg = f'Cannot load template: {e}'
        raise ValueError(msg) from e


class TemplateFormatter(
    Formatter[TemplateFormatterConfig],
    format=Format.TEMPLATE,
):
    """Formatter that formats events using user defined template."""

    @override
    def __init__(
        self,
        config: TemplateFormatterConfig,
        params: FormatterParams,
    ) -> None:
        super().__init__(config, params)

        if config.template_path is not None:
            self._template = _load_template_from_file(
                base_dir=params['base_path'],
                template_path=config.template_path,
            )
        elif config.template is not None:
            self._template = _load_template_from_string(config.template)
        else:
            msg = 'Template or template path must be provided'
            raise ValueError(msg)

    @override
    def format_events(self, events: Sequence[str]) -> FormattingResult:
        formatted_events: list[str] = []
        errors: list[FormatError] = []

        for event in events:
            try:
                formatted_events.append(self._template.render(event=event))
            except Exception as e:  # noqa: BLE001
                errors.append(
                    FormatError(
                        (
                            f'Failed to render template: '
                            f'{e.__class__.__name__}: {e}',
                        ),
                        original_event=event,
                    ),
                )

        return FormattingResult(
            events=formatted_events,
            formatted_count=len(formatted_events),
            errors=errors,
        )


class TemplateBatchFormatter(
    Formatter[TemplateFormatterConfig],
    format=Format.TEMPLATE_BATCH,
):
    """Formatter that formats events into a single event using user
    defined template.
    """

    @override
    def __init__(
        self,
        config: TemplateFormatterConfig,
        params: FormatterParams,
    ) -> None:
        super().__init__(config, params)

        if config.template_path is not None:
            self._template = _load_template_from_file(
                base_dir=params['base_path'],
                template_path=config.template_path,
            )
        elif config.template is not None:
            self._template = _load_template_from_string(config.template)
        else:
            msg = 'Template or template path must be provided'
            raise ValueError(msg)

    @override
    def format_events(self, events: Sequence[str]) -> FormattingResult:
        formatted_events: list[str] = []
        errors: list[FormatError] = []

        try:
            formatted_events.append(self._template.render(events=events))
        except Exception as e:  # noqa: BLE001
            errors.append(
                FormatError(
                    f'Failed render template: {e.__class__.__name__}: {e}',
                ),
            )

        return FormattingResult(
            events=formatted_events,
            formatted_count=len(events),
            errors=errors,
        )


class EventumHttpInputFormatter(
    Formatter[SimpleFormatterConfig],
    format=Format.EVENTUM_HTTP_INPUT,
):
    """Formatter that formats events into request body for Eventum HTTP
    input plugin.
    """

    @override
    def __init__(
        self,
        config: SimpleFormatterConfig,
        params: FormatterParams,
    ) -> None:
        super().__init__(config, params)

    @override
    def format_events(self, events: Sequence[str]) -> FormattingResult:
        return FormattingResult(
            events=[f'{{"count": {len(events)}}}'],
            formatted_count=len(events),
            errors=[],
        )


def get_formatter_class(format: Format) -> type[Formatter[Any]]:
    """Return specific formatter class depending on format.

    Parameters
    ----------
    format : Format
        Format.

    Returns
    -------
    type[Formatter[Any]]
        Formatter class.

    Raises
    ------
    ValueError
        If no appropriate formatter found for specified format.

    """
    return Formatter.get_formatter(format)
