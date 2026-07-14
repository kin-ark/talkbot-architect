"""Load and validate a wiz-builder manifest YAML file."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml
from jsonschema import Draft7Validator

_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schema" / "manifest.schema.yaml"

_VALID_BRANCHES = frozenset({"Positive", "Negative", "Reject", "Unclassified", "No answer"})
_TERMINAL_TYPES = frozenset(
    {"exit", "transfer", "goto", "goto_kb", "goto_mr", "talk_continue", "exit_port"}
)
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
class TagCategorySpec:
    name: str
    values: tuple[str, ...]
    is_mutex: bool = False
    type: int = 0


@dataclass(frozen=True)
class TagAssignmentSpec:
    category: str
    values: tuple[str, ...]


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
    tags: tuple[TagAssignmentSpec, ...] = ()


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
class KnowledgeBase:
    """A KB entry: triggering intents → spoken answers, optionally delegating to a canvas."""

    name: str
    intents: tuple[str, ...]
    answers: tuple[str, ...]
    multi_round: str | None = None


@dataclass(frozen=True)
class Manifest:
    name: str
    branch: str
    language: str
    custom_variables: tuple[CustomVariable, ...]
    custom_intents: tuple[CustomIntent, ...]
    canvases: tuple[Canvas, ...]
    raw_text: str = field(repr=False)
    knowledge_bases: tuple[KnowledgeBase, ...] = field(default_factory=tuple)
    hot_words: tuple[str, ...] = field(default_factory=tuple)
    tags: tuple[TagCategorySpec, ...] = field(default_factory=tuple)
    enterprise_id: int | str | None = None


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
    declared_intents = {i["name"] for i in data.get("custom_intents", [])}

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

        node_branch_intents: dict[str, dict] = {
            n["id"]: ((n.get("config") or {}).get("branch_intents") or {})
            for n in node_list
        }

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
            # nested-source edges are validated against the child's exit ports in a later
            # cross-canvas pass; skip the system-branch check for them.
            if node_types.get(src) != "nested":
                extra = {"Default"} if node_types.get(src) == "assign" else set()
                custom = set(node_branch_intents.get(src, {}))
                allowed = _VALID_BRANCHES | extra | custom
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

        # Custom talk-branch validation: declared intents + mandatory Unclassified.
        edges_by_src: dict[str, set[str]] = {}
        for edge in edge_list:
            edges_by_src.setdefault(edge["from"], set()).add(edge["branch"])
        for node in node_list:
            if node.get("type", "talk") != "talk":
                continue
            bi = (node.get("config") or {}).get("branch_intents") or {}
            if not bi:
                continue
            nid = node["id"]
            for label, intent_names in bi.items():
                if label in _VALID_BRANCHES:
                    raise ManifestError(
                        f"{path}: canvas {cname!r}: talk node {nid!r} branch_intents label "
                        f"{label!r} collides with a system branch name; custom labels must "
                        f"be distinct"
                    )
                for iname in (intent_names or []):
                    if iname not in declared_intents:
                        raise ManifestError(
                            f"{path}: canvas {cname!r}: talk node {nid!r} branch {label!r} "
                            f"references intent {iname!r} which is not a declared custom_intent"
                        )
            if "Unclassified" not in edges_by_src.get(nid, set()):
                raise ManifestError(
                    f"{path}: canvas {cname!r}: talk node {nid!r} declares branch_intents "
                    f"but has no connected Unclassified branch (mandatory fallback)"
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

        # goto_mr config.target validation (target must be a multi-round canvas)
        # Compute the set of multi-round target canvas names from KBs
        mr_target_names = {
            kb.get("multi_round")
            for kb in (data.get("knowledge_bases") or [])
            if kb.get("multi_round")
        }
        for node in node_list:
            if node.get("type") == "goto_mr":
                nid = node["id"]
                cfg = node.get("config") or {}
                target = cfg.get("target")
                if not target:
                    raise ManifestError(
                        f"{path}: canvas {cname!r}: goto_mr node {nid!r} missing config.target "
                        f"(must name a multi-round dialogue canvas)"
                    )
                if target not in mr_target_names:
                    raise ManifestError(
                        f"{path}: canvas {cname!r}: goto_mr node {nid!r} "
                        f"config.target {target!r} is not a multi-round dialogue canvas "
                        f"(must be some knowledge_base's multi_round target)"
                    )
                # Container constraint: goto_mr node must be in a multi-round canvas
                if cname not in mr_target_names:
                    raise ManifestError(
                        f"{path}: goto_mr node {nid!r} is in canvas {cname!r} which is "
                        f"not a multi-round dialogue; goto_mr is only valid inside a "
                        f"multi-round component"
                    )

        # talk_continue config.target validation (optional return target; must be main-flow)
        # Container constraint: talk_continue must be inside a multi-round canvas
        for node in node_list:
            if node.get("type") == "talk_continue":
                nid = node["id"]
                cfg = node.get("config") or {}
                target = cfg.get("target")

                # Container constraint: canvas must be a multi-round target
                if cname not in mr_target_names:
                    raise ManifestError(
                        f"{path}: talk_continue node {nid!r} is in canvas {cname!r} which is "
                        f"not a multi-round dialogue; talk_continue is only valid inside a "
                        f"multi-round component"
                    )

                # Return target validation (if present)
                if target:
                    if target not in all_canvas_names:
                        raise ManifestError(
                            f"{path}: canvas {cname!r}: talk_continue node {nid!r} "
                            f"config.target {target!r} does not match any canvas name"
                        )
                    # Return target must be a main-flow canvas (NOT a multi-round target)
                    if target in mr_target_names:
                        raise ManifestError(
                            f"{path}: canvas {cname!r}: talk_continue node {nid!r} "
                            f"return target {target!r} must be a main-flow (non-multi-round) canvas"
                        )

        # goto_kb config.target validation (target is a KB name; resolved at compile time)
        for node in node_list:
            if node.get("type") == "goto_kb":
                nid = node["id"]
                cfg = node.get("config") or {}
                target = cfg.get("target")
                if not target:
                    raise ManifestError(
                        f"{path}: canvas {cname!r}: goto_kb node {nid!r} missing config.target "
                        f"(must name a knowledge_base in this manifest)"
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

    # --- Nested-component validation (cross-canvas) ---
    # Map canvas name -> set of exit_port names it declares.
    exit_ports_by_canvas: dict[str, set[str]] = {}
    for canvas in data["canvases"]:
        names: set[str] = set()
        for node in canvas["nodes"]:
            if node.get("type") == "exit_port":
                pname = (node.get("config") or {}).get("name")
                if not pname:
                    raise ManifestError(
                        f"{path}: canvas {canvas['name']!r}: exit_port node {node['id']!r} "
                        f"missing config.name"
                    )
                names.add(pname)
        exit_ports_by_canvas[canvas["name"]] = names

    # Count nested references per target; validate targets + branch names.
    nested_ref_count: dict[str, int] = {}
    for canvas in data["canvases"]:
        cname = canvas["name"]
        node_types = {n["id"]: n.get("type", "talk") for n in canvas["nodes"]}
        for node in canvas["nodes"]:
            if node.get("type") != "nested":
                continue
            target = (node.get("config") or {}).get("target")
            if not target or target not in all_canvas_names or target == cname:
                raise ManifestError(
                    f"{path}: canvas {cname!r}: nested node {node['id']!r} config.target "
                    f"{target!r} does not match any other canvas in this manifest"
                )
            nested_ref_count[target] = nested_ref_count.get(target, 0) + 1
            if not exit_ports_by_canvas.get(target):
                raise ManifestError(
                    f"{path}: nested node {node['id']!r} target {target!r} must contain at "
                    f"least one exit_port node"
                )
        # Edges leaving a nested node must name one of the child's exit ports.
        for edge in (canvas.get("edges") or []):
            if node_types.get(edge["from"]) == "nested":
                target = next(
                    (n["config"]["target"] for n in canvas["nodes"]
                     if n["id"] == edge["from"]), None
                )
                if edge["branch"] not in exit_ports_by_canvas.get(target, set()):
                    raise ManifestError(
                        f"{path}: canvas {cname!r}: edge from nested node {edge['from']!r} "
                        f"branch {edge['branch']!r} has no exit_port named {edge['branch']!r} "
                        f"in child {target!r}"
                    )
    for target, count in nested_ref_count.items():
        if count > 1:
            raise ManifestError(
                f"{path}: child canvas {target!r} is referenced by more than one nested node "
                f"({count}); a nested child maps to exactly one parent"
            )

    # M1: any canvas that contains exit_port nodes but is NOT the target of any nested node
    # is an error — exit_port is only valid inside a nested child canvas.
    child_canvas_names: set[str] = set(nested_ref_count.keys())
    for canvas in data["canvases"]:
        cname = canvas["name"]
        has_exit_port = any(n.get("type") == "exit_port" for n in canvas["nodes"])
        if has_exit_port and cname not in child_canvas_names:
            raise ManifestError(
                f"{path}: canvas {cname!r}: exit_port nodes only valid in a nested child canvas"
            )

    # --- knowledge_bases validation ---
    declared_intent_names = {i["name"] for i in data.get("custom_intents", [])}

    kb_list = data.get("knowledge_bases") or []
    kb_names: list[str] = []
    for kb in kb_list:
        kname = kb["name"]

        # Unique KB names
        if kname in kb_names:
            raise ManifestError(f"{path}: duplicate knowledge base name: {kname!r}")
        kb_names.append(kname)

        # Each intent must be a declared custom_intent
        for intent_ref in kb.get("intents") or []:
            if intent_ref not in declared_intent_names:
                raise ManifestError(
                    f"{path}: knowledge base {kname!r} intent {intent_ref!r} "
                    f"is not a declared custom_intent"
                )

        # Must have ≥1 answers OR a multi_round target
        has_answers = bool(kb.get("answers"))
        multi_round = kb.get("multi_round")
        if not has_answers and not multi_round:
            raise ManifestError(
                f"{path}: knowledge base {kname!r} must have at least one answer "
                f"or a multi_round target"
            )

        # multi_round (if set) must match a canvas name
        if multi_round and multi_round not in all_canvas_names:
            raise ManifestError(
                f"{path}: knowledge base {kname!r} multi_round target {multi_round!r} "
                f"does not match any canvas"
            )

    # --- tags validation ---
    tags_list = data.get("tags") or []
    tag_names: list[str] = []
    for t in tags_list:
        tname = t["name"]
        # Unique tag category names
        if tname in tag_names:
            raise ManifestError(f"{path}: duplicate tag category name: {tname!r}")
        tag_names.append(tname)
        # Unique values within each category
        values = t.get("values") or []
        if len(values) != len(set(values)):
            raise ManifestError(
                f"{path}: duplicate tag value in category {tname!r}"
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
                    tags=tuple(
                        TagAssignmentSpec(
                            category=t["category"], values=tuple(t.get("values") or ())
                        )
                        for t in node.get("tags") or []
                    ),
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

    knowledge_bases = [
        KnowledgeBase(
            name=kb["name"],
            intents=tuple(kb.get("intents") or []),
            answers=tuple(kb.get("answers") or []),
            multi_round=kb.get("multi_round"),
        )
        for kb in (data.get("knowledge_bases") or [])
    ]

    hot_words = tuple(
        w.strip() for w in (data.get("hot_words") or []) if w and w.strip()
    )

    tags = []
    for t in data.get("tags") or []:
        values = tuple(t.get("values") or ())
        if len(set(values)) != len(values):
            raise ManifestError(f"duplicate tag value in category {t['name']!r}")
        tags.append(TagCategorySpec(
            name=t["name"], values=values,
            is_mutex=bool(t.get("is_mutex", False)), type=int(t.get("type", 0)),
        ))
    cat_names = [t.name for t in tags]
    if len(set(cat_names)) != len(cat_names):
        raise ManifestError(f"duplicate tag category name: {sorted(cat_names)}")

    return Manifest(
        name=data["name"],
        branch=data["branch"],
        language=data["language"],
        custom_variables=tuple(custom_variables),
        custom_intents=tuple(custom_intents),
        canvases=tuple(canvases),
        knowledge_bases=tuple(knowledge_bases),
        hot_words=hot_words,
        tags=tuple(tags),
        enterprise_id=data.get("enterprise_id"),
        raw_text=raw_text,
    )
