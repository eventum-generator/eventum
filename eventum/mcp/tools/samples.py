"""Sample introspection tool."""

import asyncio
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


def _describe_sample(
    context: AuthoringContext,
    name: str,
    relative_path: str,
) -> dict[str, Any] | ToolFailure:
    """Resolve and parse the sample synchronously."""
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

    # Exact-case match: the sample config source validators accept
    # only lowercase '.csv'/'.json', mirroring the workspace file
    # extension allow-list.
    suffix = rel.suffix

    cfg: SampleConfigModel

    # Config construction stays inside the try: a symlinked source
    # may resolve to a different suffix, and the resulting
    # ValidationError must not escape raw with the absolute path.
    try:
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

        sample_config = SampleConfig(root=cfg)

        # source is absolute, so base_path is only a fallback for
        # relative sources; pass the file's parent regardless.
        reader = SamplesReader(
            {_KEY: sample_config},
            base_path=path.parent,
        )
        sample = reader[_KEY]
    except ContextualError as e:
        # Routed through to_tool_error: allow-listed + path-relativized;
        # reason text is scrubbed there too.
        return to_tool_error(e, context.generators_dir)
    except Exception:  # noqa: BLE001 - no raw exception/path may escape
        return ToolFailure(
            error='Failed to load sample',
            details={'file_path': relative_path},
        )

    row_count = len(sample)
    example_rows = [
        list(sample[i]) for i in range(min(_EXAMPLE_ROWS_LIMIT, row_count))
    ]

    return {
        'type': sample_type,
        'columns': sample.columns,
        'row_count': row_count,
        'example_rows': example_rows,
    }


async def describe_sample(
    context: AuthoringContext,
    name: str,
    relative_path: str,
) -> dict[str, Any] | ToolFailure:
    """Return introspection metadata for a sample file.

    The resolve-and-parse body runs in a worker thread: the whole
    sample is parsed to count rows, so the cost grows with the file
    size and must not block the event loop.

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
    return await asyncio.to_thread(
        _describe_sample, context, name, relative_path
    )


def register(
    mcp: FastMCP,
    context: AuthoringContext,
    *,
    transport: str,
) -> None:
    """Register sample-introspection tools on the server."""

    @mcp.tool(name='describe_sample')
    async def _describe_sample_tool(
        name: str,
        relative_path: str,
    ) -> dict[str, Any] | ToolFailure:
        """Describe a CSV or JSON sample file in a generator directory.

        Use it to learn a sample's column names so templates can
        reference them via ``samples.<name>.pick().<column>``.

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
            await describe_sample(
                context, name=name, relative_path=relative_path
            ),
            mcp_tool='describe_sample',
            mcp_transport=transport,
        )
