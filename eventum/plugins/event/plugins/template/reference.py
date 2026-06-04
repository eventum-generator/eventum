"""Programmatic description of the template Jinja context surface.

Introspects the live helper objects (the ``rand`` module and the
``Sample``, ``Dispatcher`` and ``State`` classes) so the description
cannot drift from the code: a new helper added to an existing namespace
surfaces here with no extra step. Non-introspectable entries (external
libraries, user-provided dicts, the event fields) are described in
prose. Consumed by the MCP ``eventum://templating/reference`` resource.
"""

import inspect
from dataclasses import dataclass

from eventum.plugins.event.plugins.template.dispatch import Dispatcher
from eventum.plugins.event.plugins.template.modules import rand
from eventum.plugins.event.plugins.template.sample_reader import Sample
from eventum.plugins.event.plugins.template.state import State


@dataclass(frozen=True)
class Helper:
    """A single callable available in the template context."""

    name: str
    signature: str
    summary: str


@dataclass(frozen=True)
class Namespace:
    """A named group of helpers (or a described, non-callable entry)."""

    path: str
    description: str
    helpers: tuple[Helper, ...]


@dataclass(frozen=True)
class ContextReference:
    """The full template context surface."""

    namespaces: tuple[Namespace, ...]


def _summary(obj: object) -> str:
    """Return the first line of an object's docstring, or empty string."""
    doc = inspect.getdoc(obj)
    if not doc:
        return ''
    return doc.strip().split('\n', 1)[0].strip()


def _signature(func: object) -> str:
    """Return the call signature string with ``self`` stripped."""
    try:
        sig = inspect.signature(func)  # type: ignore[arg-type]
    except TypeError, ValueError:
        return '()'
    params = [p for name, p in sig.parameters.items() if name != 'self']
    return str(sig.replace(parameters=params))


def _helpers(owner: object, module_name: str) -> tuple[Helper, ...]:
    """Collect public helpers defined in ``module_name`` from ``owner``."""
    found: list[Helper] = []
    for name, func in inspect.getmembers(owner, inspect.isfunction):
        if name.startswith('_'):
            continue
        if getattr(func, '__module__', None) != module_name:
            continue
        found.append(Helper(name, _signature(func), _summary(func)))
    return tuple(sorted(found, key=lambda h: h.name))


def _rand_namespace_classes() -> list[tuple[str, type]]:
    """Return public classes defined in the rand module, sorted by name."""
    classes: list[tuple[str, type]] = []
    for name, cls in inspect.getmembers(rand, inspect.isclass):
        if name.startswith('_'):
            continue
        if cls.__module__ != rand.__name__:
            continue
        classes.append((name, cls))
    return sorted(classes)


def build_context_reference() -> ContextReference:
    """Build the template context reference by introspection.

    Returns
    -------
    ContextReference
        Every namespace available to event templates: ``module.rand``
        and its sub-namespaces, ``samples.<name>``, ``dispatch``, the
        ``locals``/``shared``/``globals`` state objects, and described
        entries (``module.faker``/``module.mimesis``, ``params``,
        ``vars``, ``timestamp``, ``tags``).

    """
    namespaces: list[Namespace] = []

    namespaces.append(
        Namespace(
            'module.rand',
            'Random value helpers (top level of the rand module).',
            _helpers(rand, rand.__name__),
        )
    )
    for cname, cls in _rand_namespace_classes():
        namespaces.append(
            Namespace(
                f'module.rand.{cname}',
                _summary(cls),
                _helpers(cls, rand.__name__),
            )
        )

    namespaces.append(
        Namespace(
            'samples.<name>',
            'Accessor for a named sample. Index by name '
            '(samples.<name>) then call a method to draw rows.',
            _helpers(Sample, Sample.__module__),
        )
    )

    namespaces.append(
        Namespace(
            'dispatch',
            'Per-event control-flow signals.',
            _helpers(Dispatcher, Dispatcher.__module__),
        )
    )

    state_helpers = _helpers(State, State.__module__)
    namespaces.append(
        Namespace(
            'locals',
            'Per-template mutable state (not shared across templates).',
            state_helpers,
        )
    )
    namespaces.append(
        Namespace(
            'shared',
            'Per-generator mutable state shared across its templates.',
            state_helpers,
        )
    )
    namespaces.append(
        Namespace(
            'globals',
            'Cross-generator mutable state (thread-safe; also exposes '
            'acquire()/release()).',
            state_helpers,
        )
    )

    namespaces.append(
        Namespace(
            'module.faker',
            'Faker library access. Use module.faker.locale[code] to get '
            'a Faker instance, then call any Faker provider method.',
            (),
        )
    )
    namespaces.append(
        Namespace(
            'module.mimesis',
            'Mimesis library access. Use module.mimesis.locale[code] '
            'for a Generic provider; module.mimesis.enums/random are '
            're-exported.',
            (),
        )
    )
    namespaces.append(
        Namespace(
            'params',
            'User-defined constants from the template plugin config '
            '(env.globals); also fed by ${params.*} substitution.',
            (),
        )
    )
    namespaces.append(
        Namespace(
            'vars',
            'Per-template variables declared in the template config.',
            (),
        )
    )
    namespaces.append(
        Namespace(
            'timestamp',
            'The event timestamp (a timezone-aware datetime).',
            (),
        )
    )
    namespaces.append(
        Namespace('tags', 'The event tags (list of strings).', ()),
    )

    return ContextReference(tuple(namespaces))
