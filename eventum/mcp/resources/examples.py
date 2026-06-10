"""``eventum://examples/generators`` resource.

Serves the bundled worked example(s) with full file contents, plus URL
pointers to richer external example sets. The server performs no
network I/O: an agent fetches the pointers with its own web tools. This
keeps the server deterministic and air-gapped-safe.
"""

import json
from importlib.resources import files
from typing import TypedDict

from mcp.server.fastmcp import FastMCP


class _BundledExample(TypedDict):
    name: str
    description: str
    files: list[str]


BUNDLED: list[_BundledExample] = [
    {
        'name': 'web-access-log',
        'description': (
            'One JSON access-log event per tick: random client IP, '
            'HTTP method, sampled path + status, response size. Uses '
            'cron input, a chance-mode template, a JSON sample, and '
            'file output with the json formatter.'
        ),
        'files': [
            'generator.yml',
            'templates/access.json.jinja',
            'samples/paths.json',
        ],
    },
    {
        'name': 'signup-events',
        'description': (
            'One JSON signup event per tick with user fields drawn from '
            'a CSV sample. Uses cron input, a chance-mode template, a '
            'CSV sample with a header (named-column access), and file '
            'output with the json formatter.'
        ),
        'files': [
            'generator.yml',
            'templates/signup.json.jinja',
            'samples/users.csv',
        ],
    },
    {
        'name': 'latency-metrics',
        'description': (
            'A statsd-style latency line per tick over a fixed time '
            'range. Uses a linspace input (evenly spaced timestamps) and '
            'the template output formatter, whose template wraps the raw '
            'event value.'
        ),
        'files': [
            'generator.yml',
            'templates/latency.jinja',
        ],
    },
    {
        'name': 'audit-backfill',
        'description': (
            'A finite batch of audit events at explicit past timestamps. '
            'Uses the timestamps input plugin for historical backfill '
            'instead of a live stream.'
        ),
        'files': [
            'generator.yml',
            'templates/audit.json.jinja',
        ],
    },
]

EXTERNAL: list[dict[str, str]] = [
    {
        'name': 'content-packs',
        'url': 'https://github.com/eventum-generator/content-packs',
        'description': (
            'Many realistic, ready-to-run generators (cloud, network, '
            'security, web).'
        ),
    },
    {
        'name': 'hub',
        'url': 'https://eventum.run/hub',
        'description': 'Browse generators on the Eventum hub.',
    },
]


def _read_bundled() -> list[dict[str, object]]:
    root = files('eventum.mcp').joinpath('examples')
    out: list[dict[str, object]] = []
    for entry in BUNDLED:
        name = entry['name']
        contents = {
            rel: root.joinpath(name, rel).read_text(encoding='utf-8')
            for rel in entry['files']
        }
        out.append(
            {
                'name': name,
                'description': entry['description'],
                'files': contents,
            }
        )
    return out


def render_examples() -> str:
    """Render the examples resource payload as JSON text."""
    return json.dumps(
        {'bundled': _read_bundled(), 'external': EXTERNAL},
        indent=2,
    )


def register(mcp: FastMCP) -> None:
    """Register the examples resource."""

    @mcp.resource(
        'eventum://examples/generators',
        name='Example generators',
        description=(
            'Worked example generators (full file sets) plus pointers '
            'to external example repositories. Read these to learn '
            'real generator structure.'
        ),
        mime_type='application/json',
    )
    def examples_generators() -> str:
        return render_examples()
