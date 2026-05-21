"""Flow-graph integrity checks (WIZ100..WIZ199)."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

import yaml

from wizcheck.ir import WizFile
from wizcheck.report import Finding, Location, Severity

_RULES_FILE = Path(__file__).resolve().parents[3] / "schema" / "dead_end_rules.yaml"


def _load_rules() -> dict:
    if not _RULES_FILE.exists():
        return {"labels_requiring_children": []}
    return yaml.safe_load(_RULES_FILE.read_text(encoding="utf-8")) or {}


_RULES = _load_rules()


def check_graph(wf: WizFile) -> list[Finding]:
    findings: list[Finding] = []
    findings.extend(_check_orphan_refs(wf))
    findings.extend(_check_unreachable(wf))
    findings.extend(_check_dead_ends(wf))
    findings.extend(_check_cycles(wf))
    findings.extend(_check_library_refs_rollup(wf))
    return findings


def _build_label_lookup(wf: WizFile) -> dict[UUID, str]:
    out: dict[UUID, str] = {}
    for comp in wf.components.values():
        for node in comp.details.flow_nodes.values():
            out[node.uuid] = node.label
    return out


def _check_orphan_refs(wf: WizFile) -> list[Finding]:
    """WIZ100: a node's parentId points to a UUID not present in the export.

    v3: demoted from ERROR to WARNING. Typically a reference to a WIZ.AI
    Component Library entry whose definition lives outside this export, but
    can also signal a structural defect. The user must verify in the WIZ.AI UI.
    """
    label_by_uuid = _build_label_lookup(wf)
    out: list[Finding] = []
    for orphan in wf.flow.orphan_refs():
        children = list(wf.flow.graph.successors(orphan))
        child_labels = sorted({label_by_uuid.get(c, "") for c in children if label_by_uuid.get(c)})
        label_hint = (
            f" (referenced by node(s) labelled {', '.join(repr(lbl) for lbl in child_labels)})"
            if child_labels else ""
        )
        out.append(Finding(
            code="WIZ100",
            severity=Severity.WARNING,
            location=Location(entity="FlowNode", id=str(orphan), field="parent_uuid"),
            message=(
                f"FlowNode {orphan} is referenced as a parent but is not present in this "
                f"export{label_hint}. May be a Component Library reference or a structural "
                f"defect — verify in the WIZ.AI UI."
            ),
        ))
    return out


def _check_unreachable(wf: WizFile) -> list[Finding]:
    """WIZ101: nodes that cannot be reached from any root.

    v3: the root set includes (a) declared component roots AND (b) library-ref
    orphan parents. A node whose only path to a real root goes through an
    external library reference is reachable via that import, not unreachable.
    """
    roots: set[UUID] = set()
    for comp in wf.components.values():
        roots.update(comp.details.root_uuids)
    # Treat library-ref parents as additional external roots.
    roots.update(wf.flow.orphan_refs())
    reachable: set[UUID] = set()
    for r in roots:
        reachable.update(wf.flow.reachable_from(r))
    out: list[Finding] = []
    for node_uuid in wf.flow.all_nodes():
        if node_uuid not in reachable:
            out.append(Finding(
                code="WIZ101",
                severity=Severity.WARNING,
                location=Location(entity="FlowNode", id=str(node_uuid), field=None),
                message=f"FlowNode {node_uuid} is unreachable from any component root.",
            ))
    return out


def _check_dead_ends(wf: WizFile) -> list[Finding]:
    """WIZ102: leaf nodes with labels that are configured to require children."""
    expected_labels = set(_RULES.get("labels_requiring_children", []))
    label_by_uuid: dict[UUID, str] = {}
    has_visual_children: set[UUID] = set()
    for comp in wf.components.values():
        for node in comp.details.flow_nodes.values():
            label_by_uuid[node.uuid] = node.label
            if node.raw.get("children"):
                has_visual_children.add(node.uuid)
    out: list[Finding] = []
    for leaf in wf.flow.dead_ends():
        if leaf in has_visual_children:
            continue
        label = label_by_uuid.get(leaf)
        if label and label in expected_labels:
            out.append(Finding(
                code="WIZ102",
                severity=Severity.WARNING,
                location=Location(entity="FlowNode", id=str(leaf), field=None),
                message=(
                    f"FlowNode {leaf} (label={label!r}) has no outgoing transitions; "
                    f"this label is configured to require children."
                ),
            ))
    return out


def _check_cycles(wf: WizFile) -> list[Finding]:
    out: list[Finding] = []
    for cycle in wf.flow.cycles():
        out.append(Finding(
            code="WIZ103",
            severity=Severity.WARNING,
            location=Location(entity="FlowNode", id=str(cycle[0]), field=None),
            message=f"Cycle detected through FlowNodes: {' -> '.join(str(n) for n in cycle)}.",
        ))
    return out


def _check_library_refs_rollup(wf: WizFile) -> list[Finding]:
    """WIZ104: per-file rollup of external/library references.

    Emitted once when one or more orphan parent UUIDs exist. Lists the unique
    set of child labels so the user can audit which Component Library entries
    this export depends on.
    """
    refs = wf.flow.library_refs()
    if not refs:
        return []
    label_by_uuid = _build_label_lookup(wf)
    seen_labels: list[str] = []
    for _orphan, children in refs.items():
        for child in children:
            label = label_by_uuid.get(child, "")
            if label and label not in seen_labels:
                seen_labels.append(label)
    labels_str = f": {seen_labels}" if seen_labels else ""
    return [Finding(
        code="WIZ104",
        severity=Severity.WARNING,
        location=Location(entity="WizFile", id="", field=None),
        message=(
            f"Export contains {len(refs)} external/library reference(s){labels_str}. "
            f"Confirm each is an intentional Component Library import."
        ),
    )]
