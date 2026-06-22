"""Load and validate a wiz-builder manifest YAML file."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml
from jsonschema import Draft7Validator

_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schema" / "manifest.schema.yaml"

_VALID_BRANCHES = frozenset({"Positive", "Negative", "Reject", "Unclassified", "No answer"})


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

    # Per-canvas invariants
    for canvas in data["canvases"]:
        cname = canvas["name"]
        node_list = canvas["nodes"]
        edge_list = canvas.get("edges") or []

        # Unique node ids
        ids_in_canvas: set[str] = set()
        for i, node in enumerate(node_list):
            nid = node.get("id") or f"_auto_{i}"
            if nid in ids_in_canvas:
                raise ManifestError(f"{path}: duplicate node id {nid!r} in canvas {cname!r}")
            ids_in_canvas.add(nid)

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
            if branch not in _VALID_BRANCHES:
                raise ManifestError(
                    f"{path}: edge in canvas {cname!r} has invalid branch {branch!r}; "
                    f"must be one of {sorted(_VALID_BRANCHES)}"
                )
            key = (src, branch)
            if key in seen_src_branch:
                raise ManifestError(
                    f"{path}: canvas {cname!r} has duplicate edge ({src!r}, {branch!r})"
                )
            seen_src_branch.add(key)
            incoming.add(dst)

        # Exactly one entry node (node with no incoming edge)
        entry_nodes = [nid for nid in ids_in_canvas if nid not in incoming]
        if len(entry_nodes) != 1:
            raise ManifestError(
                f"{path}: canvas {cname!r} must have exactly one entry node "
                f"(a node with no incoming edge), found {len(entry_nodes)}: {sorted(entry_nodes)}"
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
        for i, node in enumerate(canvas["nodes"]):
            nodes.append(
                Node(
                    id=node.get("id") or f"_auto_{i}",
                    prompt=node["prompt"],
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
