"""Tests for the template context reference builder."""

from eventum.plugins.event.plugins.template.reference import (
    build_context_reference,
)


def _paths(ref: object) -> set[str]:
    return {ns.path for ns in ref.namespaces}  # type: ignore[attr-defined]


def test_includes_rand_namespaces() -> None:
    """All rand sub-namespaces are present in the reference."""
    ref = build_context_reference()
    paths = _paths(ref)
    assert {
        'module.rand',
        'module.rand.number',
        'module.rand.string',
        'module.rand.network',
        'module.rand.crypto',
        'module.rand.datetime',
    } <= paths


def test_rand_helpers_are_introspected_with_signatures() -> None:
    """Rand helpers carry correct names, signatures, and summaries."""
    ref = build_context_reference()
    by_path = {ns.path: ns for ns in ref.namespaces}
    crypto = {h.name for h in by_path['module.rand.crypto'].helpers}
    assert {'sha1', 'sha256', 'md5', 'uuid4'} <= crypto
    network = {h.name for h in by_path['module.rand.network'].helpers}
    assert {'ip_v4', 'ip_v6', 'mac'} <= network
    number = by_path['module.rand.number'].helpers
    integer = next(h for h in number if h.name == 'integer')
    assert 'a' in integer.signature
    assert 'self' not in integer.signature
    assert integer.summary  # non-empty docstring summary


def test_includes_samples_dispatch_and_state() -> None:
    """Sample, dispatch, state, and described-only entries are present."""
    ref = build_context_reference()
    by_path = {ns.path: ns for ns in ref.namespaces}
    samples = {h.name for h in by_path['samples.<name>'].helpers}
    assert {
        'pick',
        'pick_n',
        'weighted_pick',
        'weighted_pick_n',
        'where',
    } <= samples
    dispatch = {h.name for h in by_path['dispatch'].helpers}
    assert {'drop', 'next', 'exhaust'} <= dispatch
    assert 'globals' in by_path
    assert 'params' in by_path
    assert 'vars' in by_path


def test_described_namespaces_have_no_introspected_helpers() -> None:
    """Described-only namespaces have empty helpers and non-empty prose."""
    ref = build_context_reference()
    by_path = {ns.path: ns for ns in ref.namespaces}
    assert by_path['module.faker'].helpers == ()
    assert by_path['module.faker'].description  # but has prose


def test_globals_exposes_lock_methods_not_on_locals() -> None:
    """Globals surfaces acquire/release; locals does not."""
    ref = build_context_reference()
    by_path = {ns.path: ns for ns in ref.namespaces}
    gl = {h.name for h in by_path['globals'].helpers}
    loc = {h.name for h in by_path['locals'].helpers}
    assert {'acquire', 'release'} <= gl
    assert not ({'acquire', 'release'} & loc)


def test_module_importer_and_subprocess_are_surfaced() -> None:
    """The generic module importer and subprocess are present."""
    ref = build_context_reference()
    by_path = {ns.path: ns for ns in ref.namespaces}
    assert 'module' in by_path
    description = by_path['module'].description.lower()
    assert 'import any' in description
    assert 'installed' in description
    assert by_path['module'].helpers == ()
    subprocess_helpers = {h.name for h in by_path['subprocess'].helpers}
    assert 'run' in subprocess_helpers


def test_every_env_global_is_documented() -> None:
    """Every env-level template global maps to a reference namespace.

    Guards against drift: a global injected into the Jinja environment
    (as ``subprocess`` once was) but missing from the reference fails
    here.
    """
    from pathlib import Path

    from jinja2 import DictLoader, Environment

    from eventum.plugins.event.plugins.template.config import (
        TemplateConfigForGeneralModes,
        TemplateEventPluginConfig,
        TemplateEventPluginConfigForGeneralModes,
        TemplatePickingMode,
    )
    from eventum.plugins.event.plugins.template.plugin import (
        TemplateEventPlugin,
    )

    plugin = TemplateEventPlugin(
        config=TemplateEventPluginConfig(
            root=TemplateEventPluginConfigForGeneralModes(
                params={},
                samples={},
                mode=TemplatePickingMode.ALL,
                templates=[
                    {
                        'event': TemplateConfigForGeneralModes(
                            template=Path('event.jinja')
                        )
                    }
                ],
            )
        ),
        params={
            'id': 1,
            'templates_loader': DictLoader(mapping={'event.jinja': ''}),
        },
    )

    builtins = set(Environment().globals)
    injected = set(plugin._env.globals) - builtins  # noqa: SLF001
    ref = build_context_reference()
    documented = {ns.path.split('.')[0] for ns in ref.namespaces}

    missing = injected - documented
    assert not missing, f'undocumented template globals: {sorted(missing)}'
