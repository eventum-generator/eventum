"""Detect the global state a generator project reads and writes.

A generator touches the global state from its Jinja2 templates and from
the script of its `script` event plugin. Both are parsed here - with
the Jinja2 parser and the Python one - and reported the same way: the
keys a file writes, the keys it reads, and the calls whose keys cannot
be resolved without running the file.

The analysis is static: nothing of the project is imported or rendered,
so a key a file builds at runtime is reported as a warning instead of
being guessed.
"""

import ast
from dataclasses import dataclass, field
from pathlib import Path, PurePath
from typing import Literal

import structlog
from jinja2 import Environment, nodes

logger = structlog.stdlib.get_logger()

WarningType = Literal['dynamic_key', 'update_call']

_TEMPLATE_SUFFIXES = ('.j2', '.jinja')
_SCRIPT_SUFFIXES = ('.py',)

SUPPORTED_SUFFIXES = (*_TEMPLATE_SUFFIXES, *_SCRIPT_SUFFIXES)
"""Suffixes of the files that carry detectable globals usage."""

_GLOBALS_NAME = 'globals'


@dataclass(frozen=True)
class GlobalsReference:
    """A single reference to globals in a generator file."""

    key: str
    path: str


@dataclass(frozen=True)
class GlobalsWarning:
    """A warning about globals usage that cannot be fully detected."""

    type: WarningType
    path: str


@dataclass
class GlobalsUsage:
    """Detected globals usage in generator files."""

    writes: list[GlobalsReference] = field(default_factory=list)
    reads: list[GlobalsReference] = field(default_factory=list)
    warnings: list[GlobalsWarning] = field(default_factory=list)

    def merge(self, other: GlobalsUsage) -> None:
        """Merge another GlobalsUsage into this one."""
        self.writes.extend(other.writes)
        self.reads.extend(other.reads)
        self.warnings.extend(other.warnings)


_ENV = Environment(extensions=['jinja2.ext.do', 'jinja2.ext.loopcontrols'])


def collect_globals_usage(generator_dir: Path) -> GlobalsUsage:
    """Detect globals usage across a whole generator project.

    Walks the directory tree once, reads every template and script, and
    runs AST detection over each of them. Performs blocking filesystem
    IO and CPU-bound parsing, so it must run in a worker thread to
    avoid blocking an event loop.

    Parameters
    ----------
    generator_dir : Path
        Resolved generator directory to scan.

    Returns
    -------
    GlobalsUsage
        Merged writes, reads, and warnings from all files of the
        project. A file that cannot be read is skipped.

    """
    usage = GlobalsUsage()

    for filepath in generator_dir.rglob('*'):
        if filepath.suffix not in SUPPORTED_SUFFIXES or not filepath.is_file():
            continue

        rel_path = str(filepath.relative_to(generator_dir))

        try:
            content = filepath.read_text(encoding='utf-8')
        except OSError:
            logger.warning('Failed to read file', path=str(filepath))
            continue

        usage.merge(detect_globals_usage(content, rel_path))

    return usage


def detect_globals_usage(content: str, path: str) -> GlobalsUsage:
    """Detect globals usage in a generator file.

    Parameters
    ----------
    content : str
        Content of the file.

    path : str
        Path of the file (for reporting), its suffix selects the
        parser.

    Returns
    -------
    GlobalsUsage
        Detected writes, reads, and warnings. Empty for a file that is
        neither a template nor a script, and for one that cannot be
        parsed.

    """
    suffix = PurePath(path).suffix

    if suffix in _TEMPLATE_SUFFIXES:
        return _detect_in_template(content, path)

    if suffix in _SCRIPT_SUFFIXES:
        return _detect_in_script(content, path)

    return GlobalsUsage()


def _detect_in_template(content: str, path: str) -> GlobalsUsage:
    """Detect globals usage in a Jinja2 template."""
    usage = GlobalsUsage()

    try:
        tree = _ENV.parse(content)
    except Exception:  # noqa: BLE001
        return usage

    _walk_template_node(tree, path, usage)
    return usage


def _is_globals_name(node: nodes.Node) -> bool:
    """Check if a node refers to the `globals` variable."""
    return isinstance(node, nodes.Name) and node.name == _GLOBALS_NAME


def _walk_template_node(  # noqa: C901
    node: nodes.Node,
    path: str,
    usage: GlobalsUsage,
) -> None:
    """Recursively walk AST nodes to find globals references."""
    # Handle method calls: set, get, update
    if isinstance(node, nodes.Call):
        if isinstance(node.node, nodes.Getattr) and _is_globals_name(
            node.node.node
        ):
            method = node.node.attr

            if method == 'set':
                if node.args and isinstance(node.args[0], nodes.Const):
                    usage.writes.append(
                        GlobalsReference(
                            key=node.args[0].value,
                            path=path,
                        )
                    )
                elif node.args:
                    usage.warnings.append(
                        GlobalsWarning(
                            type='dynamic_key',
                            path=path,
                        )
                    )

            elif method == 'get':
                if node.args and isinstance(node.args[0], nodes.Const):
                    usage.reads.append(
                        GlobalsReference(
                            key=node.args[0].value,
                            path=path,
                        )
                    )
                elif node.args:
                    usage.warnings.append(
                        GlobalsWarning(
                            type='dynamic_key',
                            path=path,
                        )
                    )

            elif method == 'update':
                usage.warnings.append(
                    GlobalsWarning(
                        type='update_call',
                        path=path,
                    )
                )

    elif (
        isinstance(node, nodes.Getitem)
        and _is_globals_name(node.node)
        and isinstance(node.arg, nodes.Const)
    ):
        usage.reads.append(
            GlobalsReference(
                key=node.arg.value,
                path=path,
            )
        )

    # Recurse into child nodes
    for child in node.iter_child_nodes():
        _walk_template_node(child, path, usage)


def _detect_in_script(content: str, path: str) -> GlobalsUsage:
    """Detect globals usage in a script of the `script` event plugin.

    The state reaches a script as the `globals` key of the params its
    `produce` function receives, so both the subscription itself and
    the names it is assigned to are followed.
    """
    usage = GlobalsUsage()

    try:
        tree = ast.parse(content)
    except SyntaxError:
        return usage

    state_names = _collect_state_names(tree)

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            _detect_script_call(node, state_names, path, usage)
        elif (
            isinstance(node, ast.Subscript)
            and _is_state_expression(node.value, state_names)
            and isinstance(node.slice, ast.Constant)
            and isinstance(node.slice.value, str)
        ):
            usage.reads.append(
                GlobalsReference(key=node.slice.value, path=path)
            )

    return usage


def _is_globals_subscript(node: ast.expr) -> bool:
    """Check if a node subscribes the `globals` key of the params."""
    return (
        isinstance(node, ast.Subscript)
        and isinstance(node.slice, ast.Constant)
        and node.slice.value == _GLOBALS_NAME
    )


def _collect_state_names(tree: ast.Module) -> set[str]:
    """Collect names the global state is assigned to."""
    names: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and _is_globals_subscript(node.value):
            names.update(
                target.id
                for target in node.targets
                if isinstance(target, ast.Name)
            )
        elif (
            isinstance(node, ast.AnnAssign)
            and node.value is not None
            and _is_globals_subscript(node.value)
            and isinstance(node.target, ast.Name)
        ):
            names.add(node.target.id)

    return names


def _is_state_expression(node: ast.expr, state_names: set[str]) -> bool:
    """Check if a node evaluates to the global state."""
    if isinstance(node, ast.Name):
        return node.id in state_names

    return _is_globals_subscript(node)


def _detect_script_call(
    node: ast.Call,
    state_names: set[str],
    path: str,
    usage: GlobalsUsage,
) -> None:
    """Record a state method call of a script."""
    if not isinstance(node.func, ast.Attribute) or not _is_state_expression(
        node.func.value, state_names
    ):
        return

    method = node.func.attr

    if method == 'update':
        usage.warnings.append(GlobalsWarning(type='update_call', path=path))
        return

    if method not in ('set', 'get') or not node.args:
        return

    key = node.args[0]

    if isinstance(key, ast.Constant) and isinstance(key.value, str):
        reference = GlobalsReference(key=key.value, path=path)

        if method == 'set':
            usage.writes.append(reference)
        else:
            usage.reads.append(reference)
    else:
        usage.warnings.append(GlobalsWarning(type='dynamic_key', path=path))
