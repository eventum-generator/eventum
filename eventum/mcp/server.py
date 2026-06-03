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
from eventum.mcp.tools import samples as sample_tools
from eventum.mcp.tools import workspace_files as ws_tools

_INSTRUCTIONS = (
    'Eventum MCP server. Author and inspect synthetic data generators: '
    'discover plugins and their config schemas, and (in later tools) '
    'validate and preview generators before running them.'
)


def build_server(context: AuthoringContext) -> FastMCP:
    """Build a FastMCP server with tools bound to the given context.

    Parameters
    ----------
    context : AuthoringContext
        Authoring context injected into each tool at registration time.

    Returns
    -------
    FastMCP
        Configured server with plugin discovery, formatter discovery,
        sample introspection, and workspace file tools registered.

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

    return mcp
