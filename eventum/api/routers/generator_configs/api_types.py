"""API-layer type-resolved generator configuration models.

These models mirror `runtime_types.GeneratorConfig` but relax each
non-string field to also accept ``PlaceholderString`` values
(``${params.*}`` / ``${secrets.*}``).  This keeps the OpenAPI schema
detailed (every plugin field is visible with its original type) while
letting the API read and write configs that contain variable
substitution placeholders.

Plugin config source files (``plugins/*/config.py``) are **not**
modified — the relaxation is applied programmatically at import time.
"""

import re
import types
from typing import (
    Annotated,
    Any,
    Literal,
    TypeAliasType,
    Union,
    assert_never,
    get_args,
    get_origin,
)

from annotated_types import Ge, Gt, Le, Lt
from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    RootModel,
    create_model,
)
from pydantic.fields import FieldInfo

from eventum.api.routers.generator_configs.runtime_types import (
    PluginNamedConfig,
)
from eventum.plugins.loader import (
    get_event_plugin_names,
    get_input_plugin_names,
    get_output_plugin_names,
    load_event_plugin,
    load_input_plugin,
    load_output_plugin,
)

# ── Placeholder type ─────────────────────────────────────────────────

_PLACEHOLDER_RE = re.compile(r'^\$\{(params|secrets)\..+\}$')

# Numeric constraints that must be moved from FieldInfo into
# `Annotated[T, ...]` so they only apply to the typed branch, not to
# PlaceholderString.  MinLen/MaxLen are intentionally dropped — they
# can crash on coerced types like Path (no len()) and are not
# meaningful when fields may contain placeholder strings.
_NUMERIC_CONSTRAINT_CLASSES = (Ge, Gt, Le, Lt)


def _validate_placeholder(value: str) -> str:
    if not _PLACEHOLDER_RE.match(value):
        msg = (
            'Value must be a ${params.*} or ${secrets.*} '
            f'placeholder, got: {value}'
        )
        raise ValueError(msg)
    return value


PlaceholderString = Annotated[
    str,
    AfterValidator(_validate_placeholder),
]

# ── Type relaxation ──────────────────────────────────────────────────

_relaxed_model_cache: dict[type, type] = {}


def _already_accepts_any_str(tp: type) -> bool:
    """Return True if the type is ``str`` (bare).

    Already accepts any string including placeholders without extra
    validation.
    """
    return tp is str


def _relax_type(  # noqa: C901, PLR0911, PLR0912
    annotation: Any,
) -> Any:
    """Recursively transform a type annotation to also accept
    ``PlaceholderString``.

    Examples
    --------
    >>> _relax_type(int)
    int | PlaceholderString
    >>> _relax_type(list[HttpUrl])
    list[HttpUrl | PlaceholderString]
    >>> _relax_type(str)
    str  # unchanged

    """
    # ---- leaf cases --------------------------------------------------
    if annotation is type(None):
        return annotation

    if _already_accepts_any_str(annotation):
        return annotation

    # ---- TypeAliasType (Python 3.12+ `type X = ...`) -----------------
    # Pydantic stores these unresolved; unwrap to the underlying type.
    if isinstance(annotation, TypeAliasType):
        return _relax_type(annotation.__value__)

    origin = get_origin(annotation)
    args = get_args(annotation)

    # ---- Union (includes T | None) -----------------------------------
    if origin is types.UnionType or origin is Union:
        # If the union already contains bare `str`, no change needed
        if any(_already_accepts_any_str(a) for a in args):
            return annotation

        # Recursively relax BaseModel members (so their inner
        # fields also accept placeholders).  Non-model members
        # are kept as-is.
        relaxed_args: list[Any] = []
        for a in args:
            if isinstance(a, type) and issubclass(a, BaseModel):
                relaxed_args.append(relax_model(a))
            else:
                relaxed_args.append(a)

        return Union[*relaxed_args, PlaceholderString]

    # ---- list[T] → list[_relax(T)] | PlaceholderString ----------------
    # Inner elements are relaxed AND the whole list can be a placeholder.
    if origin is list:
        inner = args[0] if args else Any
        return list[_relax_type(inner)] | PlaceholderString  # type: ignore[misc]

    # ---- dict[K, V] — typically dict[str, Any], unchanged ------------
    if origin is dict:
        return annotation

    # ---- Annotated[T, metadata...] -----------------------------------
    # Keep constraints on the original type; add PlaceholderString as a
    # separate union member so constraints only apply to the typed
    # branch.
    if origin is Annotated:
        base = args[0]
        metadata = args[1:]
        if _already_accepts_any_str(base):
            return annotation

        # For container types (e.g. list[HttpUrl]), relax inner
        # elements while preserving collection-level constraints
        # (MinLen, MaxLen).
        base_origin = get_origin(base)
        if base_origin is list:
            inner_args = get_args(base)
            inner = inner_args[0] if inner_args else Any
            relaxed_list = list[_relax_type(inner)]  # type: ignore[misc,valid-type]
            return (
                Annotated[relaxed_list, *metadata]  # type: ignore[valid-type]
                | PlaceholderString
            )

        # For scalar types, keep annotation intact so numeric
        # constraints (Ge, Gt, etc.) only apply to the typed branch.
        return annotation | PlaceholderString

    # ---- Literal[...] ------------------------------------------------
    if origin is Literal:
        return annotation | PlaceholderString

    # ---- Pydantic BaseModel subclass (nested config) -----------------
    if isinstance(annotation, type) and issubclass(
        annotation,
        BaseModel,
    ):
        return relax_model(annotation) | PlaceholderString

    # ---- Everything else (int, float, bool, HttpUrl, Path, …) --------
    return annotation | PlaceholderString


# ── Model relaxation ─────────────────────────────────────────────────


def _build_relaxed_field(
    field_info: FieldInfo,
    relaxed_annotation: Any,
) -> tuple[Any, FieldInfo]:
    """Build a ``(annotation, FieldInfo)`` tuple for
    ``create_model``.

    Numeric constraints (Ge, Gt, Le, Lt) have been folded into the
    type annotation by the caller.  Length constraints (MinLen, MaxLen)
    are intentionally dropped — they can crash on coerced types like
    ``Path`` (which doesn't support ``len()``), and are not meaningful
    when fields may contain placeholder strings.  Real validation
    happens at runtime after substitution.
    """
    from pydantic_core import PydanticUndefined

    kwargs: dict[str, Any] = {}

    if field_info.default is not PydanticUndefined:
        kwargs['default'] = field_info.default
    elif field_info.default_factory is not None:
        kwargs['default_factory'] = field_info.default_factory

    if field_info.title:
        kwargs['title'] = field_info.title

    if field_info.description:
        kwargs['description'] = field_info.description

    return (relaxed_annotation, Field(**kwargs))


def relax_model(
    model_cls: type[BaseModel],
) -> type[BaseModel]:
    """Create a relaxed copy of *model_cls* where every non-string
    field also accepts ``PlaceholderString``.

    Results are cached so that shared models (e.g. formatter configs
    referenced by several output plugins) are only generated once.
    """
    if model_cls in _relaxed_model_cache:
        return _relaxed_model_cache[model_cls]

    # Reserve a slot to break infinite recursion on self-referencing
    # models (unlikely but defensive).
    _relaxed_model_cache[model_cls] = model_cls  # temporary

    # RootModel subclasses need special handling: they must remain
    # RootModel so that Pydantic transparently unwraps the ``root``
    # field (i.e. ``{"mode": "chance", ...}`` is accepted directly
    # without requiring ``{"root": {"mode": "chance", ...}}``).
    # The discriminator is intentionally dropped because relaxed union
    # members have non-Literal alternatives that break Pydantic's
    # discriminated union resolution.
    if issubclass(model_cls, RootModel):
        root_fi = model_cls.model_fields['root']
        relaxed_root_type = _relax_type(root_fi.annotation)

        relaxed_root_cls = create_model(
            model_cls.__name__,
            __base__=RootModel,
            root=(relaxed_root_type, ...),
        )
        _relaxed_model_cache[model_cls] = relaxed_root_cls
        return relaxed_root_cls

    field_defs: dict[str, tuple[Any, FieldInfo]] = {}

    for name, fi in model_cls.model_fields.items():
        annotation = fi.annotation

        # Move numeric constraints from FieldInfo.metadata into the
        # annotation so they only apply to the typed branch of the
        # union, not to PlaceholderString.
        type_constraints = [
            m
            for m in fi.metadata
            if isinstance(m, _NUMERIC_CONSTRAINT_CLASSES)
        ]

        if type_constraints:
            annotation = Annotated[annotation, *type_constraints]  # type: ignore[assignment]

        # Relax the (potentially annotated) type
        relaxed = _relax_type(annotation)

        field_defs[name] = _build_relaxed_field(fi, relaxed)

    relaxed_cls: type[BaseModel] = create_model(  # type: ignore[call-overload]
        model_cls.__name__,
        **field_defs,  # type: ignore[arg-type]
        __config__=ConfigDict(frozen=True, extra='forbid'),
    )

    _relaxed_model_cache[model_cls] = relaxed_cls
    return relaxed_cls


# ── API plugin config model generation ───────────────────────────────


def _generate_api_plugin_config_models(
    plugin_type: Literal['input', 'event', 'output'],
) -> tuple[type[PluginNamedConfig], ...]:
    """Generate relaxed plugin configuration models.

    Mirrors
    :func:`runtime_types._generate_plugin_config_models`
    but wraps each plugin config with :func:`relax_model` first.
    """
    match plugin_type:
        case 'input':
            plugin_names = get_input_plugin_names()
            loader = load_input_plugin
        case 'event':
            plugin_names = get_event_plugin_names()
            loader = load_event_plugin
        case 'output':
            plugin_names = get_output_plugin_names()
            loader = load_output_plugin
        case t:
            assert_never(t)

    models: list[type[PluginNamedConfig]] = []
    for name in plugin_names:
        plugin = loader(name)
        relaxed_config = relax_model(plugin.config_cls)
        model = create_model(  # type: ignore[call-overload]
            name,
            **{name: (relaxed_config, ...)},  # type: ignore[arg-type]
            __base__=(PluginNamedConfig,),
        )
        models.append(model)

    return tuple(models)


# ── Top-level types ──────────────────────────────────────────────────

type ApiInputPluginNamedConfig = Union[  # type: ignore  # noqa: PGH003
    *_generate_api_plugin_config_models('input')  # type: ignore  # noqa: PGH003
]
type ApiEventPluginNamedConfig = Union[  # type: ignore  # noqa: PGH003
    *_generate_api_plugin_config_models('event')  # type: ignore  # noqa: PGH003
]
type ApiOutputPluginNamedConfig = Union[  # type: ignore  # noqa: PGH003
    *_generate_api_plugin_config_models('output')  # type: ignore  # noqa: PGH003
]


class ApiGeneratorConfig(BaseModel, extra='forbid', frozen=True):
    """Type-resolved generator config that also accepts placeholders.

    Attributes
    ----------
    input : list[ApiInputPluginNamedConfig]
        List of input plugin named configurations.

    event : ApiEventPluginNamedConfig
        Event plugin named configuration.

    output : list[ApiOutputPluginNamedConfig]
        List of output plugin named configurations.

    Notes
    -----
    Unlike ``runtime_types.GeneratorConfig`` which rejects placeholder
    strings, this model accepts ``${params.*}`` and ``${secrets.*}``
    in any field.  The OpenAPI schema still documents every plugin
    field with its original type.

    """

    input: list[ApiInputPluginNamedConfig]
    event: ApiEventPluginNamedConfig
    output: list[ApiOutputPluginNamedConfig]
