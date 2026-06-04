"""Formatter discovery tools."""

from typing import Any

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from eventum.mcp.context import AuthoringContext
from eventum.mcp.errors import ToolFailure
from eventum.plugins.output.fields import (
    Format,
    JsonFormatterConfig,
    SimpleFormatterConfig,
    TemplateFormatterConfig,
)

_FORMAT_CONFIG: dict[Format, type[BaseModel]] = {
    Format.PLAIN: SimpleFormatterConfig,
    Format.JSON: JsonFormatterConfig,
    Format.JSON_BATCH: JsonFormatterConfig,
    Format.TEMPLATE: TemplateFormatterConfig,
    Format.TEMPLATE_BATCH: TemplateFormatterConfig,
    Format.EVENTUM_HTTP_INPUT: SimpleFormatterConfig,
}

_FORMAT_DESCRIPTIONS: dict[Format, str] = {
    Format.PLAIN: (
        'Raw event string passed through as-is, one string per event.'
    ),
    Format.JSON: ('Each event re-serialized as a JSON object.'),
    Format.JSON_BATCH: ('All events serialized into a single JSON array.'),
    Format.TEMPLATE: (
        'Each event rendered through a Jinja2 template; '
        'use for CSV, custom text, or any line-oriented format.'
    ),
    Format.TEMPLATE_BATCH: (
        'The entire batch rendered once through a Jinja2 template; '
        'use when the template must see all events together.'
    ),
    Format.EVENTUM_HTTP_INPUT: (
        'Request body format expected by the Eventum HTTP input plugin.'
    ),
}


def list_formatters(
    context: AuthoringContext,  # noqa: ARG001
) -> list[dict[str, Any]]:
    """Return metadata for all available output formatters.

    Parameters
    ----------
    context : AuthoringContext
        Authoring context (DI seam; unused at this layer).

    Returns
    -------
    list[dict[str, Any]]
        One entry per format: ``format`` (string value), ``description``
        (one-line semantic), and ``config_model`` (Pydantic model name).

    """
    return [
        {
            'format': fmt.value,
            'description': _FORMAT_DESCRIPTIONS[fmt],
            'config_model': _FORMAT_CONFIG[fmt].__name__,
        }
        for fmt in Format
    ]


def get_formatter_schema(
    context: AuthoringContext,  # noqa: ARG001
    format: str,
) -> dict[str, Any] | ToolFailure:
    """Return the JSON Schema of a formatter's config model.

    Parameters
    ----------
    context : AuthoringContext
        Authoring context (DI seam; unused at this layer).

    format : str
        Format value (e.g. ``'json'``, ``'template'``). Must be one of
        the values in ``eventum.plugins.output.fields.Format``.

    Returns
    -------
    dict[str, Any]
        JSON Schema dict for the formatter's config model.

    ToolFailure
        If ``format`` is not a known value. Does not raise.

    """
    try:
        fmt = Format(format)
    except ValueError:
        return ToolFailure(
            error=f'Unknown format: {format!r}',
            details={
                'format': format,
                'valid_formats': [f.value for f in Format],
            },
        )

    config_cls = _FORMAT_CONFIG[fmt]
    return config_cls.model_json_schema()


def register(
    mcp: FastMCP,
    context: AuthoringContext,
    *,
    transport: str,  # noqa: ARG001
) -> None:
    """Register formatter-discovery tools on the server."""

    @mcp.tool(name='list_formatters')
    def _list_formatters_tool() -> list[dict[str, Any]]:
        """Return metadata for all available output formatters.

        Returns
        -------
        list[dict[str, Any]]
            One entry per format: ``format`` (string value),
            ``description`` (one-line semantic), and ``config_model``
            (Pydantic model name).

        """
        return list_formatters(context)

    @mcp.tool(name='get_formatter_schema')
    def _get_formatter_schema_tool(
        format: str,
    ) -> dict[str, Any] | ToolFailure:
        """Return the JSON Schema of a formatter's config model.

        Use it to author a valid ``formatter`` block in an output plugin
        config.

        Parameters
        ----------
        format : str
            Format value (e.g. ``'json'``, ``'template'``), as returned
            by ``list_formatters``.

        Returns
        -------
        dict[str, Any] | ToolFailure
            The formatter config's JSON Schema, or a structured failure
            if the format is unknown. Does not raise.

        """
        return get_formatter_schema(context, format=format)
