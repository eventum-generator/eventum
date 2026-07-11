"""Scenario-management tools (HTTP transport only).

Scenarios are named groups of generators, stored as tags on startup
entries. These tools list and edit those tags through the shared
``Startup`` service; they hold no logic of their own.
"""

import asyncio
from typing import Any

from mcp.server.fastmcp import FastMCP

from eventum.app.startup import StartupError
from eventum.mcp.context import LiveContext
from eventum.mcp.errors import ToolFailure, read_only_failure, to_tool_error
from eventum.mcp.observability import observe_failure


async def list_scenarios(context: LiveContext) -> list[str] | ToolFailure:
    """Return the distinct scenario names across all startup entries."""
    try:
        return await asyncio.to_thread(context.startup.list_scenarios)
    except StartupError as e:
        return to_tool_error(e, context.generators_dir)


async def get_scenario(
    context: LiveContext, scenario: str
) -> dict[str, Any] | ToolFailure:
    """Return a scenario with the ids of the generators it groups."""
    try:
        ids = await asyncio.to_thread(
            context.startup.get_scenario_generators, scenario
        )
    except StartupError as e:
        return to_tool_error(e, context.generators_dir)
    if not ids:
        return ToolFailure(
            error='Scenario not found', details={'name': scenario}
        )
    return {'name': scenario, 'generator_ids': ids}


async def add_generator_to_scenario(
    context: LiveContext, generator_id: str, scenario: str
) -> dict[str, Any] | ToolFailure:
    """Tag a generator as belonging to a scenario."""
    if context.read_only:
        return read_only_failure({'value': generator_id, 'name': scenario})
    try:
        await asyncio.to_thread(
            context.startup.tag_scenario, generator_id, scenario
        )
    except StartupError as e:
        return to_tool_error(e, context.generators_dir)
    return {'generator_id': generator_id, 'scenario': scenario, 'added': True}


async def remove_generator_from_scenario(
    context: LiveContext, generator_id: str, scenario: str
) -> dict[str, Any] | ToolFailure:
    """Remove a generator's membership in a scenario."""
    if context.read_only:
        return read_only_failure({'value': generator_id, 'name': scenario})
    try:
        await asyncio.to_thread(
            context.startup.untag_scenario, generator_id, scenario
        )
    except StartupError as e:
        return to_tool_error(e, context.generators_dir)
    return {
        'generator_id': generator_id,
        'scenario': scenario,
        'removed': True,
    }


async def delete_scenario(
    context: LiveContext, scenario: str
) -> dict[str, Any] | ToolFailure:
    """Remove a scenario tag from every generator that carries it."""
    if context.read_only:
        return read_only_failure({'name': scenario})
    try:
        affected = await asyncio.to_thread(
            context.startup.delete_scenario, scenario
        )
    except StartupError as e:
        return to_tool_error(e, context.generators_dir)
    return {'scenario': scenario, 'deleted': True, 'generator_ids': affected}


def register(mcp: FastMCP, context: LiveContext, *, transport: str) -> None:
    """Register scenario-management tools on the server."""

    @mcp.tool(name='list_scenarios')
    async def _list_scenarios_tool() -> list[str] | ToolFailure:
        """List the scenarios defined in the startup file.

        A scenario is a named group of generators; this returns the
        distinct scenario names across all startup entries.

        Returns
        -------
        list[str] | ToolFailure
            Sorted scenario names (empty if none), or a structured
            failure if the startup file cannot be read. Does not raise.

        """
        return observe_failure(
            await list_scenarios(context),
            mcp_tool='list_scenarios',
            mcp_transport=transport,
        )

    @mcp.tool(name='get_scenario')
    async def _get_scenario_tool(
        scenario: str,
    ) -> dict[str, Any] | ToolFailure:
        """Return a scenario and the ids of the generators in it.

        Parameters
        ----------
        scenario : str
            Scenario name, as returned by ``list_scenarios``.

        Returns
        -------
        dict[str, Any] | ToolFailure
            ``{'name', 'generator_ids'}``, or a structured failure if
            the scenario does not exist. Does not raise.

        """
        return observe_failure(
            await get_scenario(context, scenario),
            mcp_tool='get_scenario',
            mcp_transport=transport,
        )

    @mcp.tool(name='add_generator_to_scenario')
    async def _add_generator_to_scenario_tool(
        generator_id: str,
        scenario: str,
    ) -> dict[str, Any] | ToolFailure:
        """Add a generator to a scenario.

        Tags the startup entry for ``generator_id`` with ``scenario``,
        creating the scenario if no generator carried it yet. Blocked
        when the server is read-only.

        Parameters
        ----------
        generator_id : str
            Id of a generator defined in the startup file.

        scenario : str
            Scenario name to add.

        Returns
        -------
        dict[str, Any] | ToolFailure
            ``{'generator_id', 'scenario', 'added': True}``, or a
            structured failure if the server is read-only, the
            generator is not defined, or it already belongs to the
            scenario. Does not raise.

        """
        return observe_failure(
            await add_generator_to_scenario(context, generator_id, scenario),
            mcp_tool='add_generator_to_scenario',
            mcp_transport=transport,
        )

    @mcp.tool(name='remove_generator_from_scenario')
    async def _remove_generator_from_scenario_tool(
        generator_id: str,
        scenario: str,
    ) -> dict[str, Any] | ToolFailure:
        """Remove a generator from a scenario.

        Drops the ``scenario`` tag from the startup entry for
        ``generator_id``. Blocked when the server is read-only.

        Parameters
        ----------
        generator_id : str
            Id of a generator in the scenario.

        scenario : str
            Scenario name to remove from the generator.

        Returns
        -------
        dict[str, Any] | ToolFailure
            ``{'generator_id', 'scenario', 'removed': True}``, or a
            structured failure if the server is read-only or the
            generator is not in the scenario. Does not raise.

        """
        return observe_failure(
            await remove_generator_from_scenario(
                context, generator_id, scenario
            ),
            mcp_tool='remove_generator_from_scenario',
            mcp_transport=transport,
        )

    @mcp.tool(name='delete_scenario')
    async def _delete_scenario_tool(
        scenario: str,
    ) -> dict[str, Any] | ToolFailure:
        """Delete a scenario by removing its tag from every generator.

        Leaves the generators themselves untouched. Blocked when the
        server is read-only.

        Parameters
        ----------
        scenario : str
            Scenario name to delete.

        Returns
        -------
        dict[str, Any] | ToolFailure
            ``{'scenario', 'deleted': True, 'generator_ids'}`` with the
            ids that were untagged, or a structured failure if the
            server is read-only or the scenario does not exist. Does not
            raise.

        """
        return observe_failure(
            await delete_scenario(context, scenario),
            mcp_tool='delete_scenario',
            mcp_transport=transport,
        )
