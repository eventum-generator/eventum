"""Shared constants, template factory, and report printer for benchmarks."""

from __future__ import annotations

from dataclasses import dataclass, field

from jinja2 import DictLoader

from eventum.plugins.event.plugins.template.config import (
    TemplateConfigForGeneralModes,
    TemplateEventPluginConfig,
    TemplateEventPluginConfigForGeneralModes,
    TemplatePickingMode,
)
from eventum.plugins.event.plugins.template.plugin import TemplateEventPlugin

# ---------------------------------------------------------------------------
# Performance result
# ---------------------------------------------------------------------------


@dataclass
class PerfResult:
    """Minimal performance result: duration + event count."""

    duration_seconds: float = 0.0
    total_events: int = 0
    metadata: dict = field(default_factory=dict)

# ---------------------------------------------------------------------------
# Template sources
# ---------------------------------------------------------------------------

TEMPLATE_MINIMAL = '{"@timestamp": "{{ timestamp }}"}'

TEMPLATE_TYPICAL = """\
{
  "@timestamp": "{{ timestamp.isoformat() }}",
  "event": {
    "category": ["{{ ['network','authentication','process','web'] | random }}"],
    "kind": "event",
    "module": "benchmark"
  },
  "host": {
    "name": "{{ ['web-01','web-02','api-01','api-02','db-01'] | random }}"
  },
  "source": {
    "ip": "10.0.{{ range(1,10) | random }}.{{ range(1,255) | random }}"
  },
  "user": {
    "name": "user-{{ range(1000,9999) | random }}"
  },
  "message": "{{ ['INFO','WARN','ERROR','DEBUG'] | random }} \
[{{ ['auth','http','db','cache','queue'] | random }}] \
Request {{ range(1000,9999) | random }} processed in \
{{ range(1,9999) | random }}ms with status \
{{ [200,201,204,301,400,401,403,404,500,502,503] | random }}",
  "tags": ["benchmark", "perf"]
}\
"""

# ---------------------------------------------------------------------------
# Template plugin factory
# ---------------------------------------------------------------------------


def create_template_plugin(
    templates: dict[str, str],
    *,
    mode: TemplatePickingMode = TemplatePickingMode.SPIN,
    samples: dict | None = None,
    params: dict | None = None,
) -> TemplateEventPlugin:
    """Create a TemplateEventPlugin with DictLoader (no filesystem).

    Parameters
    ----------
    templates:
        Mapping of ``{alias: jinja2_source}``.
    mode:
        Template picking mode.
    samples:
        Sample configs to pass to the plugin.
    params:
        Global template params.

    """
    template_items = [
        {alias: TemplateConfigForGeneralModes(template=f'{alias}.jinja')}
        for alias in templates
    ]
    loader_mapping = {
        f'{alias}.jinja': source for alias, source in templates.items()
    }

    return TemplateEventPlugin(
        config=TemplateEventPluginConfig(
            root=TemplateEventPluginConfigForGeneralModes(
                params=params or {},
                samples=samples or {},
                mode=mode,
                templates=template_items,
            ),
        ),
        params={
            'id': 1,
            'templates_loader': DictLoader(mapping=loader_mapping),
        },
    )


# ---------------------------------------------------------------------------
# Report printer
# ---------------------------------------------------------------------------


def print_report(
    label: str,
    result: PerfResult,
    *,
    params: dict[str, object] | None = None,
) -> None:
    """Print a human-readable performance report for CI visibility."""
    print(f'\n{"=" * 60}')  # noqa: T201
    print(label)  # noqa: T201
    if params:
        parts = ' | '.join(f'{k}={v}' for k, v in params.items())
        print(f'Parameters: {parts}')  # noqa: T201

    duration = result.duration_seconds
    eps = result.total_events / duration if duration > 0 else 0

    print(  # noqa: T201
        f'Duration: {duration:.1f}s | '
        f'Total events: {result.total_events:,} | '
        f'EPS: {eps:,.0f}',
    )
    print(f'{"=" * 60}\n')  # noqa: T201
