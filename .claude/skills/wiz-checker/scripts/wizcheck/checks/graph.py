"""Flow-graph integrity checks (WIZ100..WIZ199)."""

from __future__ import annotations

from pathlib import Path
import re
from uuid import UUID

import yaml

from wizcheck.ir import WizFile
from wizcheck.report import Finding, Location, Severity

_RULES_FILE = Path(__file__).resolve().parents[3] / "schema" / "dead_end_rules.yaml"

NODE_TYPE_CONDITIONAL_JUDGMENT = 7
_VAR_ID_RE = re.compile(r"\[?\{(\d+)\}\]?")


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
    findings.extend(_check_null_branches(wf))
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
    label_by_uuid = _build_label_lookup(wf)
    has_visual_children: set[UUID] = set()
    for comp in wf.components.values():
        for node in comp.details.flow_nodes.values():
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
    labels_str = (
        ": " + ", ".join(repr(lbl) for lbl in seen_labels)
        if seen_labels else ""
    )
    ref_count = len(refs)
    label_count = len(seen_labels)
    # ref_count: distinct orphan parent UUIDs (each represents one external link)
    # label_count: distinct component labels (fewer when one library entry has
    #              multiple instances referenced from different places)
    if label_count and label_count != ref_count:
        count_str = (
            f"{ref_count} external/library reference(s) to {label_count} distinct component(s)"
        )
    else:
        count_str = f"{ref_count} external/library reference(s)"
    return [Finding(
        code="WIZ104",
        severity=Severity.WARNING,
        location=Location(entity="WizFile", id="", field=None),
        message=(
            f"Export contains {count_str}{labels_str}. "
            f"Confirm each is an intentional Component Library import."
        ),
    )]


def _check_null_branches(wf: WizFile) -> list[Finding]:
    """WIZ105: Conditional Judgment missing Null branch on a date field."""
    out: list[Finding] = []
    for comp in wf.components.values():
        for node in comp.details.flow_nodes.values():
            if node.raw.get("type") != NODE_TYPE_CONDITIONAL_JUDGMENT:
                continue
            
            # Find which date variables are being evaluated in this node
            date_var_ids_evaluated: set[int] = set()
            branches = node.raw.get("branch", [])
            for branch in branches:
                for cond in (branch.get("branch_judgement_condition") or []):
                    left_val = str(cond.get("left_value", ""))
                    match = _VAR_ID_RE.search(left_val)
                    if match:
                        var_id = int(match.group(1))
                        v = wf.variables.get(var_id)
                        if v and v.text_type == "DATE":
                            date_var_ids_evaluated.add(var_id)
            
            if not date_var_ids_evaluated:
                continue
            
            # For each date variable evaluated, ensure there is a branch handling Null or empty
            for var_id in date_var_ids_evaluated:
                has_null_branch = False
                for branch in branches:
                    conditions = branch.get("branch_judgement_condition")
                    # A branch with no conditions acts as a fallback/default
                    if not conditions:
                        has_null_branch = True
                        break
                    
                    # Look for an explicit empty check on *this specific date variable*
                    for cond in conditions:
                        cond_left_val = str(cond.get("left_value", ""))
                        match = _VAR_ID_RE.search(cond_left_val)
                        if match and int(match.group(1)) == var_id:
                            op = str(cond.get("operator", "")).lower()
                            rval = str(cond.get("right_value", "")).lower()
                            if op in ("is empty", "is_empty", "isnull", "is_null") or rval in ("null", "empty", ""):
                                has_null_branch = True
                                break
                    if has_null_branch:
                        break
                
                if not has_null_branch:
                    out.append(Finding(
                        code="WIZ105",
                        severity=Severity.ERROR,
                        location=Location(entity="FlowNode", id=str(node.uuid), field=None),
                        message="Missing fallback/null branch on Date variable"
                    ))
                    # Only emit once per node even if multiple date variables are missing checks
                    break
    return out

