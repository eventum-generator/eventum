"""Rename tools for the objects an instance holds (HTTP only).

Renaming a project or a generator touches the generator directory, the
startup file, and the live manager together, so those tools delegate to
the ``app.renaming`` service and only translate its outcome for the
agent. A secret rename moves its keyring entry and carries over
everything referring to it, never exposing its value.
"""

import asyncio
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from eventum.app.renaming import (
    RenameConflictError,
    RenameError,
    RenameNotFoundError,
    rename_instance,
    rename_project,
)
from eventum.app.secrets import rename_secret
from eventum.mcp.context import LiveContext
from eventum.mcp.errors import (
    ToolFailure,
    read_only_failure,
    scrub_message,
    to_tool_error,
)
from eventum.mcp.observability import observe_failure
from eventum.security.manage import SecretNameError


async def rename_generator_config(
    context: LiveContext, name: str, new_name: str
) -> dict[str, Any] | ToolFailure:
    """Rename a project directory and repoint the generators using it."""
    if context.read_only:
        return read_only_failure({'name': name})
    try:
        affected = await asyncio.to_thread(
            lambda: rename_project(
                manager=context.manager,
                startup=context.startup,
                generators_dir=context.generators_dir,
                name=name,
                new_name=new_name,
            ),
        )
    except RenameError as e:
        return to_tool_error(e, context.generators_dir)
    return {
        'name': name,
        'new_name': new_name,
        'renamed': True,
        'generator_ids': affected,
    }


async def rename_generator(
    context: LiveContext, generator_id: str, new_id: str
) -> dict[str, Any] | ToolFailure:
    """Rename a generator in the manager and in the startup file."""
    if context.read_only:
        return read_only_failure({'id': generator_id})
    try:
        await asyncio.to_thread(
            lambda: rename_instance(
                manager=context.manager,
                startup=context.startup,
                id=generator_id,
                new_id=new_id,
            ),
        )
    except RenameError as e:
        # Rename errors key the identifier as 'value'; the tool keys it
        # as 'id', matching the other generator tools.
        failure = to_tool_error(e, context.generators_dir)
        details = dict(failure.details)
        details.pop('value', None)
        details['id'] = generator_id
        return ToolFailure(error=failure.error, details=details)
    return {'id': generator_id, 'new_id': new_id, 'renamed': True}


async def rename_secret_name(  # noqa: PLR0911 - one per outcome
    context: LiveContext, secret: str, new_name: str
) -> dict[str, Any] | ToolFailure:
    """Move a secret to a new name, taking its referrers along.

    Every failure the agent can act on differently gets its own answer:
    a read-only server, a missing secret, a name that is taken, a name
    no configuration can reference, and a rename that failed midway.
    """
    if context.read_only:
        return read_only_failure({'name': secret})
    try:
        updated = await asyncio.to_thread(
            lambda: rename_secret(
                generators_dir=context.generators_dir,
                config_filename=Path(context.config_filename),
                repositories=context.repositories,
                name=secret,
                new_name=new_name,
            ),
        )
    except RenameNotFoundError:
        return ToolFailure(error='Secret not found', details={'name': secret})
    except RenameConflictError as e:
        # A name is taken either by another secret or by a repository
        # authenticating with it, and the two need different answers:
        # the message names which, and the repositories behind it are
        # what the agent has to free before trying again.
        failure = to_tool_error(e, context.generators_dir)
        return ToolFailure(
            error=failure.error,
            details={**failure.details, 'name': new_name},
        )
    except RenameError as e:
        # The keyring reports its failures in text this package does
        # not control, so only the message - a static string - crosses
        # the boundary, and the reason behind it stays on the server.
        return ToolFailure(
            error=scrub_message(str(e), context.generators_dir),
            details={'name': secret},
        )
    except SecretNameError as e:
        # The rule the name has to follow is the message, and it is
        # what the agent needs to pick another one.
        return ToolFailure(error=str(e), details={'name': new_name})
    except Exception:  # noqa: BLE001 - no raw error/path may escape
        return ToolFailure(error='Failed to rename secret')
    return {
        'name': secret,
        'new_name': new_name,
        'renamed': True,
        'projects': updated.projects,
        'repositories': updated.repositories,
    }


def register(mcp: FastMCP, context: LiveContext, *, transport: str) -> None:
    """Register the rename tools on the server."""

    @mcp.tool(name='rename_generator_config')
    async def _rename_generator_config_tool(
        name: str,
        new_name: str,
    ) -> dict[str, Any] | ToolFailure:
        """Rename a project, moving its directory on disk.

        Generators configured from the project are repointed at the new
        directory, both in the startup file and in the runtime, so their
        ids and parameters are unaffected. Every one of them must be
        stopped first, since a running generator reads its templates and
        samples from the directory while it works - stop them with
        ``stop_generator``. Blocked when the server is read-only.

        Parameters
        ----------
        name : str
            Current project name, as returned by
            ``list_generator_configs``.

        new_name : str
            Name to rename the project to. Must be a single directory
            name and must not be taken.

        Returns
        -------
        dict[str, Any] | ToolFailure
            ``{'name', 'new_name', 'renamed': True, 'generator_ids'}``
            with the ids that were repointed, or a structured failure if
            the server is read-only, the project does not exist, the new
            name is taken, or a generator using the project is active.
            Does not raise.

        """
        return observe_failure(
            await rename_generator_config(context, name, new_name),
            mcp_tool='rename_generator_config',
            mcp_transport=transport,
        )

    @mcp.tool(name='rename_generator')
    async def _rename_generator_tool(
        generator_id: str,
        new_id: str,
    ) -> dict[str, Any] | ToolFailure:
        """Rename a registered generator.

        The generator keeps its project, its parameters and its scenario
        membership; only the id changes, in the runtime and in the
        startup file. It must not be running - stop it first with
        ``stop_generator``. Log entries already written under the old id
        stay in their own log file. Blocked when the server is
        read-only.

        Parameters
        ----------
        generator_id : str
            Current id of the generator.

        new_id : str
            Id to rename the generator to. Must not be taken by another
            generator or startup entry.

        Returns
        -------
        dict[str, Any] | ToolFailure
            ``{'id', 'new_id', 'renamed': True}``, or a structured
            failure if the server is read-only, the generator does not
            exist, the new id is taken, or the generator is active.
            Does not raise.

        """
        return observe_failure(
            await rename_generator(context, generator_id, new_id),
            mcp_tool='rename_generator',
            mcp_transport=transport,
        )

    @mcp.tool(name='rename_secret')
    async def _rename_secret_tool(
        secret: str,
        new_name: str,
    ) -> dict[str, Any] | ToolFailure:
        """Rename a secret, keeping its value under the new name.

        The value is moved without being exposed, and everything
        referring to the secret follows: the ``${secrets.<secret>}``
        token is rewritten in the configuration of every project
        reading it, and every connected repository authenticating with
        it is pointed at the new name. A generator already running
        keeps the configuration it loaded and reads the new name the
        next time it starts. Refused when a repository already
        authenticates with the new name. Blocked when the server is
        read-only.

        Parameters
        ----------
        secret : str
            Current name of the secret.

        new_name : str
            Name to rename the secret to. Must not be taken, and must
            be words of letters, digits and ``_`` separated by ``.``,
            since a configuration references it as
            ``${secrets.<name>}``.

        Returns
        -------
        dict[str, Any] | ToolFailure
            ``{'name', 'new_name', 'renamed': True, 'projects',
            'repositories'}`` with the referrers carried over, or a
            structured failure if the server is read-only, the secret
            does not exist, the new name is taken or cannot be
            referenced, or the referrers cannot be carried over. Does
            not raise.

        """
        return observe_failure(
            await rename_secret_name(context, secret, new_name),
            mcp_tool='rename_secret',
            mcp_transport=transport,
        )
