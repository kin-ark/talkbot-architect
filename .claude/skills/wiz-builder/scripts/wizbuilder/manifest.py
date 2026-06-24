"""Load and validate a wiz-builder manifest YAML file."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml
from jsonschema import Draft7Validator

_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schema" / "manifest.schema.yaml"

_VALID_BRANCHES = frozenset({"Positive", "Negative", "Reject", "Unclassified", "No answer"})
_TERMINAL_TYPES = frozenset({"exit", "transfer", "goto"})
_VALID_OPERATORS = frozenset(
    {">", ">=", "<", "<=", "=", "!=", "In", "NotIn", "IsNull", "NotNull", "Contains"}
)
_UNARY_OPERATORS = frozenset({"IsNull", "NotNull"})


class ManifestError(Exception):
    """Raised when a manifest fails to load, parse, or validate."""


@dataclass(frozen=True)
class CustomVariable:
    name: str


@dataclass(frozen=True)
class CustomIntent:
    name: str
    language: str
    keywords: tuple[str, ...] = ()
    user_responses: tuple[str, ...] = ()


@dataclass(frozen=True)
class Node:
    """A FlowNode in a canvas.

    `id` is the manifest-local handle used in edge definitions. The id is
    independent of the UUID minted later by the compiler.
    """

    id: str
    prompt: str
    type: str = "talk"
    config: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Edge:
    """A directed edge between two canvas nodes along a named branch port.

    In YAML the keys are ``from``/``to``/``branch``; the loader maps
    ``from`` → ``src`` and ``to`` → ``dst`` to avoid Python's reserved keyword.
    """

    src: str
    branch: str
    dst: str


@dataclass(frozen=True)
class Canvas:
    name: str
    nodes: tuple[Node, ...]
    edges: tuple[Edge, ...]


@dataclass(frozen=True)
class Manifest:
    name: str
    branch: str
    language: str
    custom_variables: tuple[CustomVariable, ...]
    custom_intents: tuple[CustomIntent, ...]
    canvases: tuple[Canvas, ...]
    raw_text: str = field(repr=False)


def load_manifest(path: str | Path) -> Manifest:
    """Load, parse, and validate a manifest YAML file."""
    path = Path(path)
    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as e:
        raise ManifestError(f"{path}: cannot read file: {e}") from e

    try:
        data = yaml.safe_load(raw_text)
    except yaml.YAMLError as e:
        raise ManifestError(f"{path}: YAML parse error: {e}") from e

    if not isinstance(data, dict):
        raise ManifestError(
            f"{path}: top-level YAML must be a mapping, got {type(data).__name__}"
        )

    _schema_validate(data, path)
    _validate_cross_field_invariants(data, path)
    return _build_manifest(data, raw_text)


def _schema_validate(data: dict, path: Path) -> None:
    schema = yaml.safe_load(_SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft7Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda e: e.absolute_path)
    if errors:
        # Surface the first error with its JSON path for clarity.
        first = errors[0]
        loc = "/".join(str(p) for p in first.absolute_path) or "<root>"
        raise ManifestError(f"{path}: schema violation at {loc}: {first.message}")


def _validate_cross_field_invariants(data: dict, path: Path) -> None:
    # Unique canvas names
    canvas_names = [c["name"] for c in data["canvases"]]
    if len(canvas_names) != len(set(canvas_names)):
        dupes = [n for n in canvas_names if canvas_names.count(n) > 1]
        raise ManifestError(f"{path}: duplicate canvas name: {sorted(set(dupes))}")

    # Unique custom variable names
    var_names = [v["name"] for v in data.get("custom_variables", [])]
    if len(var_names) != len(set(var_names)):
        dupes = [n for n in var_names if var_names.count(n) > 1]
        raise ManifestError(f"{path}: duplicate custom variable name: {sorted(set(dupes))}")

    # Unique custom intent names
    intent_names = [i["name"] for i in data.get("custom_intents", [])]
    if len(intent_names) != len(set(intent_names)):
        dupes = [n for n in intent_names if intent_names.count(n) > 1]
        raise ManifestError(f"{path}: duplicate custom intent name: {sorted(set(dupes))}")

    # Collect all canvas names (needed for goto target validation below)
    all_canvas_names: set[str] = set(canvas_names)

    declared_vars = {v["name"] for v in data.get("custom_variables", [])}

    # Per-canvas invariants
    for canvas in data["canvases"]:
        cname = canvas["name"]
        node_list = canvas["nodes"]
        edge_list = canvas.get("edges") or []

        # Unique node ids; also build a map id → node type for terminal checks
        ids_in_canvas: set[str] = set()
        node_types: dict[str, str] = {}
        for node in node_list:
            nid = node["id"]
            if nid in ids_in_canvas:
                raise ManifestError(f"{path}: duplicate node id {nid!r} in canvas {cname!r}")
            ids_in_canvas.add(nid)
            node_types[nid] = node.get("type", "talk")

        # Edge endpoint existence and branch validity
        seen_src_branch: set[tuple[str, str]] = set()
        incoming: set[str] = set()
        for edge in edge_list:
            src = edge["from"]
            dst = edge["to"]
            branch = edge["branch"]

            if src not in ids_in_canvas:
                raise ManifestError(
                    f"{path}: edge in canvas {cname!r} references unknown source node {src!r}"
                )
            if dst not in ids_in_canvas:
                raise ManifestError(
                    f"{path}: edge in canvas {cname!r} references unknown destination node {dst!r}"
                )
            extra = {"Default"} if node_types.get(src) == "assign" else set()
            allowed = _VALID_BRANCHES | extra
            if branch not in allowed:
                raise ManifestError(
                    f"{path}: edge in canvas {cname!r} has invalid branch {branch!r}; "
                    f"must be one of {sorted(allowed)}"
                )
            key = (src, branch)
            if key in seen_src_branch:
                raise ManifestError(
                    f"{path}: canvas {cname!r} has duplicate edge ({src!r}, {branch!r})"
                )
            seen_src_branch.add(key)
            incoming.add(dst)

            # Terminal rule: exit/transfer/goto nodes must not have outgoing edges
            if node_types.get(src) in _TERMINAL_TYPES:
                raise ManifestError(
                    f"{path}: canvas {cname!r}: node {src!r} has type {node_types[src]!r} "
                    f"which is terminal and must not have outgoing edges"
                )

        # Validate conditional branch target existence early (before the entry-node check)
        # so that "unknown target" errors fire before "no entry node" errors.
        # Also collect valid conditional branch targets as "incoming" for entry-node calc.
        for node in node_list:
            if node.get("type") == "conditional":
                nid = node["id"]
                for b in (node.get("config") or {}).get("branches") or []:
                    t = b.get("to")
                    bname = b.get("name")
                    if t is not None and t not in ids_in_canvas:
                        raise ManifestError(
                            f"{path}: canvas {cname!r}: conditional node {nid!r} branch "
                            f"{bname!r} has unknown target {t!r}"
                        )
                    if t and t in ids_in_canvas:
                        incoming.add(t)

        # Exactly one entry node (node with no incoming edge)
        entry_nodes = [nid for nid in ids_in_canvas if nid not in incoming]
        if len(entry_nodes) != 1:
            raise ManifestError(
                f"{path}: canvas {cname!r} must have exactly one entry node "
                f"(a node with no incoming edge), found {len(entry_nodes)}: {sorted(entry_nodes)}"
            )

        # goto config.target validation
        for node in node_list:
            if node.get("type") == "goto":
                nid = node["id"]
                cfg = node.get("config") or {}
                target = cfg.get("target")
                if not target:
                    raise ManifestError(
                        f"{path}: canvas {cname!r}: goto node {nid!r} missing config.target "
                        f"(must name another canvas in this manifest)"
                    )
                if target not in all_canvas_names or target == cname:
                    raise ManifestError(
                        f"{path}: canvas {cname!r}: goto node {nid!r} config.target {target!r} "
                        f"does not match any other canvas name in this manifest"
                    )

        for node in node_list:
            ntype = node.get("type")
            cfg = node.get("config") or {}

            if ntype == "assign":
                var = cfg.get("variable")
                if var not in declared_vars:
                    raise ManifestError(
                        f"{path}: canvas {cname!r}: assign node {node['id']!r} "
                        f"config.variable {var!r} is not a declared variable"
                    )
                if "value" not in cfg:
                    raise ManifestError(
                        f"{path}: canvas {cname!r}: assign node {node['id']!r} "
                        f"missing config.value"
                    )

            elif ntype == "conditional":
                nid = node["id"]
                var = cfg.get("variable")
                if var not in declared_vars:
                    raise ManifestError(
                        f"{path}: canvas {cname!r}: conditional node {nid!r} "
                        f"config.variable {var!r} is not a declared variable"
                    )
                branches = cfg.get("branches") or []
                if not branches:
                    raise ManifestError(
                        f"{path}: canvas {cname!r}: conditional node {nid!r} has no branches"
                    )
                defaults = [b for b in branches if b.get("name") == "Default"]
                if len(defaults) != 1:
                    raise ManifestError(
                        f"{path}: canvas {cname!r}: conditional node {nid!r} must have "
                        f"exactly one Default branch, found {len(defaults)}"
                    )
                name_to_target: dict[str, str] = {}
                for b in branches:
                    bname = b.get("name")
                    target = b.get("to")
                    if not bname or not target:
                        raise ManifestError(
                            f"{path}: canvas {cname!r}: conditional node {nid!r} branch "
                            f"missing name or to: {b!r}"
                        )
                    # target existence is validated in the early pre-entry-node pass above
                    # one port = one target (same name must share to)
                    if bname in name_to_target and name_to_target[bname] != target:
                        raise ManifestError(
                            f"{path}: canvas {cname!r}: conditional node {nid!r} branch "
                            f"{bname!r} has conflicting target {target!r}"
                        )
                    name_to_target[bname] = target
                    # rule validation (Default has no condition)
                    if bname == "Default":
                        continue
                    op = b.get("op")
                    if op not in _VALID_OPERATORS:
                        raise ManifestError(
                            f"{path}: canvas {cname!r}: conditional node {nid!r} branch "
                            f"{bname!r} has invalid operator {op!r}; "
                            f"must be one of {sorted(_VALID_OPERATORS)}"
                        )
                    has_value = "value" in b
                    has_value_var = "value_var" in b
                    if op in _UNARY_OPERATORS:
                        if has_value or has_value_var:
                            raise ManifestError(
                                f"{path}: canvas {cname!r}: conditional node {nid!r} branch "
                                f"{bname!r} uses unary op {op!r} but supplies an operand"
                            )
                    else:
                        if has_value == has_value_var:
                            raise ManifestError(
                                f"{path}: canvas {cname!r}: conditional node {nid!r} branch "
                                f"{bname!r} must set exactly one of value/value_var"
                            )
                        if has_value_var and b["value_var"] not in declared_vars:
                            raise ManifestError(
                                f"{path}: canvas {cname!r}: conditional node {nid!r} branch "
                                f"{bname!r} value_var {b['value_var']!r} is not a declared variable"
                            )


def _build_manifest(data: dict, raw_text: str) -> Manifest:
    custom_variables = [
        CustomVariable(name=v["name"]) for v in data.get("custom_variables", [])
    ]
    custom_intents = [
        CustomIntent(
            name=i["name"],
            language=i["language"],
            keywords=tuple(i.get("keywords", [])),
            user_responses=tuple(i.get("user_responses", [])),
        )
        for i in data.get("custom_intents", [])
    ]
    canvases = []
    for canvas in data["canvases"]:
        nodes = []
        for node in canvas["nodes"]:
            nodes.append(
                Node(
                    id=node["id"],
                    prompt=node.get("prompt", ""),
                    type=node.get("type", "talk"),
                    config=node.get("config", {}),
                )
            )
        edges = []
        for edge in canvas.get("edges") or []:
            edges.append(
                Edge(
                    src=edge["from"],
                    branch=edge["branch"],
                    dst=edge["to"],
                )
            )
        canvases.append(Canvas(name=canvas["name"], nodes=tuple(nodes), edges=tuple(edges)))

    return Manifest(
        name=data["name"],
        branch=data["branch"],
        language=data["language"],
        custom_variables=tuple(custom_variables),
        custom_intents=tuple(custom_intents),
        canvases=tuple(canvases),
        raw_text=raw_text,
    )
