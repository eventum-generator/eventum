"""Sample introspection tool."""

from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from eventum.app import workspace
from eventum.app.workspace import WorkspaceError
from eventum.exceptions import ContextualError
from eventum.mcp.context import AuthoringContext
from eventum.mcp.errors import ToolFailure, to_tool_error
from eventum.mcp.observability import observe_failure
from eventum.plugins.event.plugins.template.config import (
    CSVSampleConfig,
    JSONSampleConfig,
    SampleConfig,
    SampleConfigModel,
    SampleType,
)
from eventum.plugins.event.plugins.template.sample_reader import (
    SamplesReader,
)

_EXAMPLE_ROWS_LIMIT = 5
_KEY = 'sample'


def describe_sample(
    context: AuthoringContext,
    name: str,
    relative_path: str,
) -> dict[str, Any] | ToolFailure:
    """Return introspection metadata for a sample file.

    Parameters
    ----------
    context : AuthoringContext
        Authoring context supplying the generators directory.

    name : str
        Generator directory name.

    relative_path : str
        Path to the sample file relative to the generator directory
        (e.g. ``'samples/cities.csv'``).

    Returns
    -------
    dict[str, Any]
        ``type`` (``'csv'`` or ``'json'``), ``columns`` (list of
        column names), ``row_count`` (int), and ``example_rows``
        (first up to 5 rows as lists of values).

    ToolFailure
        If the path escapes the generator directory, the file does not
        exist, the file type is unsupported, or the sample is malformed.
        Never raises; does not leak absolute paths.

    """
    rel = Path(relative_path)

    try:
        path = workspace.resolve_generator_file(
            context.generators_dir, name, rel
        )
    except WorkspaceError as e:
        return to_tool_error(e, context.generators_dir)

    if not path.is_file():
        return ToolFailure(
            error='Sample file not found',
            details={'file_path': relative_path},
        )

    suffix = rel.suffix.lower()

    cfg: SampleConfigModel

    if suffix == '.csv':
        sample_type = 'csv'
        # header=True so the first row is treated as column names.
        cfg = CSVSampleConfig(
            type=SampleType.CSV,
            source=path,
            header=True,
        )
    elif suffix == '.json':
        sample_type = 'json'
        cfg = JSONSampleConfig(type=SampleType.JSON, source=path)
    else:
        return ToolFailure(
            error='Unsupported sample type',
            details={'file_path': relative_path},
        )

    # base_path is unused when source is absolute (confirmed in
    # _load_csv_sample / _load_json_sample); pass the file's parent.
    sample_config = SampleConfig(root=cfg)

    try:
        reader = SamplesReader(
            {_KEY: sample_config},
            base_path=path.parent,
        )
        sample = reader[_KEY]
    except ContextualError as e:
        # Routed through to_tool_error: allow-listed + path-relativized
        # (Task 5 also scrubs the reason text here).
        return to_tool_error(e, context.generators_dir)
    except Exception:  # noqa: BLE001 - no raw exception/path may escape
        return ToolFailure(
            error='Failed to load sample',
            details={'relative_path': relative_path},
        )

    # _field_map and _rows are private; Sample exposes no public
    # accessor. _field_map is a dict[str, int] of column name to index.
    columns = list(sample._field_map)  # noqa: SLF001
    rows = sample._rows  # noqa: SLF001

    example_rows = [list(row) for row in rows[:_EXAMPLE_ROWS_LIMIT]]

    return {
        'type': sample_type,
        'columns': columns,
        'row_count': len(sample),
        'example_rows': example_rows,
    }


def register(
    mcp: FastMCP,
    context: AuthoringContext,
    *,
    transport: str,
) -> None:
    """Register sample-introspection tools on the server."""

    @mcp.tool(name='describe_sample')
    def _describe_sample_tool(
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
        return observe_failure(
            describe_sample(context, name=name, relative_path=relative_path),
            mcp_tool='describe_sample',
            mcp_transport=transport,
        )
