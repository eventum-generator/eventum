"""FastMCP server factory.

The only FastMCP-aware module besides the stdio CLI entry. Registers
tools bound to an injected context; later phases register live-only
tools when the context carries a generator manager.
"""

from typing import Any

from mcp.server.fastmcp import FastMCP

from eventum import __version__ as _eventum_version
from eventum.mcp.context import AuthoringContext
from eventum.mcp.errors import ToolFailure
from eventum.mcp.tools import discovery
from eventum.mcp.tools import formatters as fmt_tools
from eventum.mcp.tools import preview as preview_tools
from eventum.mcp.tools import samples as sample_tools
from eventum.mcp.tools import workspace_files as ws_tools

_INSTRUCTIONS = (
    'Eventum MCP server. Author and inspect synthetic data generators: '
    'discover plugins and their config schemas, and validate and preview '
    'generators before running them.'
)


# C901: complexity is the count of flat tool wrappers, not branching
# logic. If more tools land (e.g. Plan 3 live-management), refactor to
# per-module register(mcp, context) helpers rather than growing this
# function or its noqa list.
def build_server(context: AuthoringContext) -> FastMCP:  # noqa: C901
    """Build a FastMCP server with tools bound to the given context.

    Parameters
    ----------
    context : AuthoringContext
        Authoring context injected into each tool at registration time.

    Returns
    -------
    FastMCP
        Configured server with plugin discovery, formatter discovery,
        sample introspection, workspace file tools, and validate/preview
        tools registered.

    """
    mcp = FastMCP('eventum', instructions=_INSTRUCTIONS)
    mcp._mcp_server.version = _eventum_version  # noqa: SLF001

    @mcp.tool()
    def list_plugins(
        kind: discovery.Kind | None = None,
    ) -> dict[str, list[str]]:
        """List registered plugin names grouped by kind.

        Parameters
        ----------
        kind : 'input' | 'event' | 'output', optional
            Restrict to one kind. Omit to get all three.

        Returns
        -------
        dict[str, list[str]]
            Maps each kind to a sorted list of plugin names.

        """
        return discovery.list_plugins(context, kind=kind)

    @mcp.tool()
    def get_plugin_schema(
        kind: discovery.Kind,
        name: str,
    ) -> dict[str, Any] | ToolFailure:
        """Return the JSON Schema of a plugin's config model.

        Use it to author a valid config block for the plugin.

        Parameters
        ----------
        kind : 'input' | 'event' | 'output'
            Plugin kind.

        name : str
            Plugin name, as returned by ``list_plugins``.

        Returns
        -------
        dict[str, Any] | ToolFailure
            The plugin config's JSON Schema, or a structured failure
            (error plus kind and name) if the plugin is unknown. Does
            not raise.

        """
        return discovery.get_plugin_schema(context, kind=kind, name=name)

    @mcp.tool()
    def list_formatters() -> list[dict[str, Any]]:
        """Return metadata for all available output formatters.

        Returns
        -------
        list[dict[str, Any]]
            One entry per format: ``format`` (string value),
            ``description`` (one-line semantic), and ``config_model``
            (Pydantic model name).

        """
        return fmt_tools.list_formatters(context)

    @mcp.tool()
    def get_formatter_schema(format: str) -> dict[str, Any] | ToolFailure:
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
        return fmt_tools.get_formatter_schema(context, format=format)

    @mcp.tool()
    def describe_sample(
        name: str,
        relative_path: str,
    ) -> dict[str, Any] | ToolFailure:
        """Describe a CSV or JSON sample file in a generator directory.

        Use it to learn a sample's column names so templates can
        reference them via ``samples.<name>.<column>``.

        Parameters
        ----------
        name : str
            Generator directory name.

        relative_path : str
            Path to the sample file relative to the generator directory
            (e.g. ``'samples/cities.csv'``).

        Returns
        -------
        dict[str, Any] | ToolFailure
            ``type``, ``columns``, ``row_count``, and ``example_rows``
            for the sample, or a structured failure if the path is
            invalid, missing, unsupported, or malformed. Does not raise.

        """
        return sample_tools.describe_sample(
            context,
            name=name,
            relative_path=relative_path,
        )

    @mcp.tool()
    def list_generators() -> list[str]:
        """List generator directory names in the generators directory.

        Returns
        -------
        list[str]
            Sorted list of generator names (immediate subdirectories
            containing a ``generator.yml`` file). Empty if the
            generators directory does not exist.

        """
        return ws_tools.list_generators(context)

    @mcp.tool()
    def list_generator_files(name: str) -> list[str] | ToolFailure:
        """List files in a generator directory.

        Only files with allowed extensions (``.yml``, ``.yaml``,
        ``.jinja``, ``.csv``, ``.json``) are included.

        Parameters
        ----------
        name : str
            Generator directory name, as returned by
            ``list_generators``.

        Returns
        -------
        list[str] | ToolFailure
            Sorted POSIX-relative paths inside the generator directory,
            or a structured failure if the name is invalid or the
            directory does not exist. Does not raise.

        """
        return ws_tools.list_generator_files(context, name)

    @mcp.tool()
    def read_generator_file(
        name: str,
        relative_path: str,
    ) -> str | ToolFailure:
        """Return the text content of a file in a generator directory.

        Parameters
        ----------
        name : str
            Generator directory name.

        relative_path : str
            Path to the file relative to the generator directory
            (e.g. ``'templates/event.jinja'``).

        Returns
        -------
        str | ToolFailure
            File contents, or a structured failure if the path is
            invalid, the extension is not allowed, or the file does not
            exist. Does not raise.

        """
        return ws_tools.read_generator_file(context, name, relative_path)

    @mcp.tool()
    def write_generator_file(
        name: str,
        relative_path: str,
        content: str,
    ) -> dict[str, Any] | ToolFailure:
        """Write text content to a file in a generator directory.

        Creates parent directories as needed. Fails immediately when
        the server is read-only without touching the filesystem.

        Parameters
        ----------
        name : str
            Generator directory name.

        relative_path : str
            Path to the file relative to the generator directory
            (e.g. ``'templates/event.jinja'``).

        content : str
            Text to write.

        Returns
        -------
        dict[str, Any] | ToolFailure
            ``{'written': relative_path}`` on success, or a structured
            failure if the server is read-only, the path is invalid, the
            extension is not allowed, or the write fails. Does not raise.

        """
        return ws_tools.write_generator_file(
            context, name, relative_path, content
        )

    @mcp.tool()
    async def validate_generator(
        name: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any] | ToolFailure:
        """Validate a saved generator by loading and initialising every plugin.

        Parameters
        ----------
        name : str
            Generator directory name, as returned by ``list_generators``.

        params : dict[str, Any] | None, default None
            Parameter substitutions for ``${params.*}`` tokens.

        Returns
        -------
        dict[str, Any] | ToolFailure
            ``{'valid': True}`` on success, or a structured failure if
            the config is invalid or a plugin cannot be initialised. Does
            not raise.

        """
        return await preview_tools.validate_generator(
            context, name, params=params
        )

    @mcp.tool()
    async def preview_timestamps(
        name: str,
        size: int = 100,
        skip_past: bool = True,  # noqa: FBT001, FBT002
        span: str | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any] | ToolFailure:
        """Generate a histogram of input timestamps for a saved generator.

        Parameters
        ----------
        name : str
            Generator directory name.

        size : int, default 100
            Maximum number of timestamps to generate.

        skip_past : bool, default True
            Whether to skip timestamps in the past. Pass ``false`` for
            generators with a static date range in the past.

        span : str | None, default None
            Histogram bucket width. ``null`` triggers auto-span
            selection. Duration parsing is not yet implemented; omit
            this parameter for now.

        params : dict[str, Any] | None, default None
            Parameter substitutions for ``${params.*}`` tokens.

        Returns
        -------
        dict[str, Any] | ToolFailure
            Histogram with ``total``, ``span_edges``, ``span_counts``,
            ``first``, ``last``, and ``timestamps`` (ISO 8601 strings),
            or a structured failure. Does not raise.

        """
        return await preview_tools.preview_timestamps(
            context,
            name,
            size,
            skip_past=skip_past,
            span=span,
            params=params,
        )

    @mcp.tool()
    async def preview_events(
        name: str,
        count: int = 10,
        params: dict[str, Any] | None = None,
        skip_past: bool = True,  # noqa: FBT001, FBT002
    ) -> dict[str, Any] | ToolFailure:
        """Produce sample events from a saved generator.

        Parameters
        ----------
        name : str
            Generator directory name.

        count : int, default 10
            Maximum number of events to produce.

        params : dict[str, Any] | None, default None
            Parameter substitutions for ``${params.*}`` tokens.

        skip_past : bool, default True
            Whether to skip timestamps in the past. Pass ``false`` for
            generators with a static date range in the past.

        Returns
        -------
        dict[str, Any] | ToolFailure
            ``events`` (list of strings), ``errors`` (list of per-index
            dicts), and ``exhausted`` (bool), or a structured failure.
            Does not raise.

        """
        return await preview_tools.preview_events(
            context,
            name,
            count,
            params=params,
            skip_past=skip_past,
        )

    return mcp
