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
