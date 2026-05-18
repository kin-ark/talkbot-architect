"""Flow-graph integrity checks (WIZ100..WIZ199)."""

from __future__ import annotations

from pathlib import Path

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
    return findings


def _check_orphan_refs(wf: WizFile) -> list[Finding]:
    out: list[Finding] = []
    for orphan in wf.flow.orphan_refs():
        out.append(Finding(
            code="WIZ100",
            severity=Severity.ERROR,
            location=Location(entity="FlowNode", id=str(orphan), field="parent_uuid"),
            message=f"FlowNode {orphan} is referenced as a parent but does not exist.",
        ))
    return out


def _check_unreachable(wf: WizFile) -> list[Finding]:
    """Nodes that cannot be reached from any component's declared roots."""
    roots: set = set()
    for comp in wf.components.values():
        roots.update(comp.details.root_uuids)
    reachable: set = set()
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
    expected_labels = set(_RULES.get("labels_requiring_children", []))
    # Build label + raw-children lookup
    label_by_uuid: dict = {}
    has_visual_children: set = set()  # UUIDs with non-empty raw["children"]
    for comp in wf.components.values():
        for node in comp.details.flow_nodes.values():
            label_by_uuid[node.uuid] = node.label
            if node.raw.get("children"):
                has_visual_children.add(node.uuid)
    out: list[Finding] = []
    for leaf in wf.flow.dead_ends():
        if leaf in has_visual_children:
            continue  # FlowNode has nested raw children — not a real dead-end
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
