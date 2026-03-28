"""Detect globals.set/get usage in Jinja2 templates via AST analysis."""

from dataclasses import dataclass, field
from typing import Literal

from jinja2 import Environment
from jinja2 import nodes


WarningType = Literal['dynamic_key', 'update_call']


@dataclass(frozen=True)
class GlobalsReference:
    """A single reference to globals in a template."""

    key: str
    template: str


@dataclass(frozen=True)
class GlobalsWarning:
    """A warning about globals usage that cannot be fully detected."""

    type: WarningType
    template: str


@dataclass
class GlobalsUsage:
    """Detected globals usage in templates."""

    writes: list[GlobalsReference] = field(default_factory=list)
    reads: list[GlobalsReference] = field(default_factory=list)
    warnings: list[GlobalsWarning] = field(default_factory=list)

    def merge(self, other: GlobalsUsage) -> None:
        """Merge another GlobalsUsage into this one."""
        self.writes.extend(other.writes)
        self.reads.extend(other.reads)
        self.warnings.extend(other.warnings)


_ENV = Environment(extensions=['jinja2.ext.do', 'jinja2.ext.loopcontrols'])


def detect_globals_usage(source: str, template_name: str) -> GlobalsUsage:
    """Parse a Jinja2 template and detect globals.set/get usage.

    Parameters
    ----------
    source : str
        Jinja2 template source code.
    template_name : str
        Name of the template file (for reporting).

    Returns
    -------
    GlobalsUsage
        Detected writes, reads, and warnings.
    """
    usage = GlobalsUsage()

    try:
        ast = _ENV.parse(source)
    except Exception:
        return usage

    _walk_node(ast, template_name, usage)
    return usage


def _is_globals_name(node: nodes.Node) -> bool:
    """Check if a node refers to the `globals` variable."""
    return isinstance(node, nodes.Name) and node.name == 'globals'


def _walk_node(
    node: nodes.Node,
    template_name: str,
    usage: GlobalsUsage,
) -> None:
    """Recursively walk AST nodes to find globals references."""
    # globals.set("key", value) or globals.get("key", default)
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
                            template=template_name,
                        )
                    )
                elif node.args:
                    usage.warnings.append(
                        GlobalsWarning(
                            type='dynamic_key',
                            template=template_name,
                        )
                    )

            elif method == 'get':
                if node.args and isinstance(node.args[0], nodes.Const):
                    usage.reads.append(
                        GlobalsReference(
                            key=node.args[0].value,
                            template=template_name,
                        )
                    )
                elif node.args:
                    usage.warnings.append(
                        GlobalsWarning(
                            type='dynamic_key',
                            template=template_name,
                        )
                    )

            elif method == 'update':
                usage.warnings.append(
                    GlobalsWarning(
                        type='update_call',
                        template=template_name,
                    )
                )

    # globals["key"] (getitem read access)
    elif isinstance(node, nodes.Getitem):
        if _is_globals_name(node.node):
            if isinstance(node.arg, nodes.Const):
                usage.reads.append(
                    GlobalsReference(
                        key=node.arg.value,
                        template=template_name,
                    )
                )

    # Recurse into child nodes
    for child in node.iter_child_nodes():
        _walk_node(child, template_name, usage)
