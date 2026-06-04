"""``eventum://templating/reference`` resource.

Renders the introspection-built template context reference (owned by
the template plugin) as Markdown. No business logic here - this module
only formats and serves.
"""

from mcp.server.fastmcp import FastMCP

from eventum.plugins.event.plugins.template.reference import (
    build_context_reference,
)

_INTRO = (
    'Helpers available inside Eventum event templates (Jinja). Use '
    'these to author template files. Signatures omit `self`.'
)


def render_templating_reference() -> str:
    """Render the template context reference as Markdown."""
    ref = build_context_reference()
    lines = ['# Eventum template context reference', '', _INTRO, '']
    for ns in ref.namespaces:
        lines.append(f'## `{ns.path}`')
        if ns.description:
            lines.extend(['', ns.description])
        if ns.helpers:
            lines.append('')
            for helper in ns.helpers:
                tail = f' - {helper.summary}' if helper.summary else ''
                lines.append(
                    f'- `{ns.path}.{helper.name}{helper.signature}`{tail}'
                )
        lines.append('')
    return '\n'.join(lines)


def register(mcp: FastMCP) -> None:
    """Register the templating-reference resource."""

    @mcp.resource(
        'eventum://templating/reference',
        name='Template context reference',
        description=(
            'Helpers available inside event templates: module.rand.*, '
            'samples.*, dispatch, state, and the event fields. Read '
            'this before writing template files.'
        ),
        mime_type='text/markdown',
    )
    def templating_reference() -> str:
        return render_templating_reference()
