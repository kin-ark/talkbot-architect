"""Load and validate a wiz-builder manifest YAML file."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml
from jsonschema import Draft7Validator

_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schema" / "manifest.schema.yaml"


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

    `id` is the manifest-local handle used by sibling nodes' `parent` field. If
    omitted in the YAML, the loader synthesizes ``_auto_<index>`` based on the
    node's position within its canvas. The id is independent of the UUID
    minted later by the compiler.
    """

    id: str
    label: str
    parent: str | None


@dataclass(frozen=True)
class Canvas:
    name: str
    nodes: tuple[Node, ...]


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

    # Per-canvas: at least one root, no cross-canvas parent refs, unique local IDs
    for canvas in data["canvases"]:
        cname = canvas["name"]
        ids_in_canvas: set[str] = set()
        for i, node in enumerate(canvas["nodes"]):
            nid = node.get("id") or f"_auto_{i}"
            if nid in ids_in_canvas:
                raise ManifestError(f"{path}: duplicate node id {nid!r} in canvas {cname!r}")
            ids_in_canvas.add(nid)

        for node in canvas["nodes"]:
            parent = node["parent"]
            if parent is None:
                continue
            if parent not in ids_in_canvas:
                raise ManifestError(
                    f"{path}: node {node.get('id') or node['label']!r} in canvas {cname!r} "
                    f"references parent {parent!r} which is not declared in this canvas "
                    f"(parent must be the id of another node in the same canvas; "
                    f"cross-canvas references are not supported)"
                )

        roots = [n for n in canvas["nodes"] if n["parent"] is None]
        if not roots:
            raise ManifestError(
                f"{path}: canvas {cname!r} has no root node "
                f"(need at least one node with parent: null)"
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
                    label=node["label"],
                    parent=node["parent"],
                )
            )
        canvases.append(Canvas(name=canvas["name"], nodes=tuple(nodes)))

    return Manifest(
        name=data["name"],
        branch=data["branch"],
        language=data["language"],
        custom_variables=tuple(custom_variables),
        custom_intents=tuple(custom_intents),
        canvases=tuple(canvases),
        raw_text=raw_text,
    )
