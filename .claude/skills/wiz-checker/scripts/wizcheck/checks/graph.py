"""Flow-graph integrity checks (WIZ100..WIZ199).

WIZ100-WIZ104 are rewritten onto FlowModel (Tasks 1-2 output). When
wf.flow_model is None the FlowModel checks return an empty list — test helpers
that construct WizFile directly do not populate flow_model; use parse_dict()
to get a populated WizFile.

WIZ105 (Conditional Judgment missing Null branch on date field) uses the
legacy IR (wf.components / FlowNode.raw) because FlowModelNode does not carry
branch_judgement_condition data. It runs unconditionally — wf.components is
always populated by parse_dict().
"""

from __future__ import annotations

import re
from pathlib import Path

import networkx as nx
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
    if wf.flow_model is not None:
        findings.extend(_check_orphan_refs(wf))
        findings.extend(_check_dead_ends(wf))
        findings.extend(_check_cycles(wf))
        findings.extend(_check_library_refs_rollup(wf))
    findings.extend(_check_null_branches(wf))
    return findings


# ---------------------------------------------------------------------------
# WIZ100: orphan refs — branch.target_uuid not present in same-component nodes
# ---------------------------------------------------------------------------

def _check_orphan_refs(wf: WizFile) -> list[Finding]:
    """WIZ100: a same-component branch.target_uuid that is absent from the component's nodes.

    Only applies to target_uuid (same-component edges). Cross-component jumps
    (target_component), KB jumps (target_kb), and terminal branches are intentional
    exits and are NOT orphans.
    """
    fm = wf.flow_model
    assert fm is not None
    out: list[Finding] = []
    for comp in fm.components:
        node_uuids: set[str] = set(comp.nodes.keys())
        for node in comp.nodes.values():
            for branch in node.branches:
                if (
                    branch.target_uuid is not None
                    and branch.target_component is None
                    and branch.target_kb is None
                    and branch.terminal is None
                    and branch.target_uuid not in node_uuids
                ):
                    out.append(Finding(
                        code="WIZ100",
                        severity=Severity.WARNING,
                        location=Location(entity="FlowNode", id=node.uuid, field="branch"),
                        message=(
                            f"FlowNode {node.uuid!r} (label={node.label!r}) has a branch "
                            f"targeting {branch.target_uuid!r} which is not present in "
                            f"component {comp.uuid!r}. May be a Component Library reference "
                            f"or a structural defect — verify in the WIZ.AI UI."
                        ),
                    ))
    return out


# ---------------------------------------------------------------------------
# WIZ102: dead-ends — nodes with no target branch and not terminal
# ---------------------------------------------------------------------------

def _check_dead_ends(wf: WizFile) -> list[Finding]:
    """WIZ102: nodes with labels configured to require children that have no outgoing branch.

    Dead-end = no branch has any target (target_uuid/target_component/target_kb)
    AND no branch is terminal.

    Label allowlist from schema/dead_end_rules.yaml. FlowModelNode.label carries
    the node's display name (envelope['name']), which matches the step labels in
    the YAML (e.g. 'Greeting', 'Pitch'). Nodes whose label is not in the allowlist
    are not flagged — a leaf with an unlisted label is treated as an intentional
    closing node.
    """
    fm = wf.flow_model
    assert fm is not None
    expected_labels: set[str] = set(_RULES.get("labels_requiring_children", []))
    out: list[Finding] = []
    for comp in fm.components:
        for node in comp.nodes.values():
            # Determine whether any branch carries a target or is terminal
            has_exit = any(
                b.target_uuid is not None
                or b.target_component is not None
                or b.target_kb is not None
                or b.terminal is not None
                for b in node.branches
            )
            if has_exit:
                continue
            # Node has no outgoing target or terminal — check label allowlist
            if node.label in expected_labels:
                out.append(Finding(
                    code="WIZ102",
                    severity=Severity.WARNING,
                    location=Location(entity="FlowNode", id=node.uuid, field=None),
                    message=(
                        f"FlowNode {node.uuid!r} (label={node.label!r}) has no outgoing "
                        f"transitions; this label is configured to require children."
                    ),
                ))
    return out


# ---------------------------------------------------------------------------
# WIZ103: cycles — per-component same-component directed cycle detection
# ---------------------------------------------------------------------------

def _check_cycles(wf: WizFile) -> list[Finding]:
    """WIZ103: directed cycle through same-component target_uuid edges.

    Cross-component and KB jumps are excluded — they don't form intra-component cycles.
    """
    fm = wf.flow_model
    assert fm is not None
    out: list[Finding] = []
    for comp in fm.components:
        node_uuids: set[str] = set(comp.nodes.keys())
        g: nx.DiGraph = nx.DiGraph()
        for node in comp.nodes.values():
            g.add_node(node.uuid)
            for branch in node.branches:
                if (
                    branch.target_uuid is not None
                    and branch.target_uuid in node_uuids
                ):
                    g.add_edge(node.uuid, branch.target_uuid)
        for cycle in nx.simple_cycles(g):
            out.append(Finding(
                code="WIZ103",
                severity=Severity.WARNING,
                location=Location(entity="FlowNode", id=cycle[0], field=None),
                message=(
                    f"Cycle detected through FlowNodes: "
                    f"{' -> '.join(str(n) for n in cycle)}."
                ),
            ))
    return out


# ---------------------------------------------------------------------------
# WIZ104: library refs rollup — cross-component/KB targets not in the model
# ---------------------------------------------------------------------------

def _check_library_refs_rollup(wf: WizFile) -> list[Finding]:
    """WIZ104: per-file rollup of external/library references.

    External component ref: branch.target_component not matching any component uuid.
    External KB ref: branch.target_kb not in the FlowModel's knowledge_bases.

    Emitted at most once per file, listing the distinct external targets.
    """
    fm = wf.flow_model
    assert fm is not None
    known_comp_uuids: set[str] = {c.uuid for c in fm.components}
    known_kb_ids: set[int] = {kb.knowledge_id for kb in fm.knowledge_bases}

    external_comps: set[str] = set()
    external_kbs: set[int] = set()

    for comp in fm.components:
        for node in comp.nodes.values():
            for branch in node.branches:
                if (
                    branch.target_component is not None
                    and branch.target_component not in known_comp_uuids
                ):
                    external_comps.add(branch.target_component)
                if (
                    branch.target_kb is not None
                    and branch.target_kb not in known_kb_ids
                ):
                    external_kbs.add(branch.target_kb)

    if not external_comps and not external_kbs:
        return []

    parts: list[str] = []
    if external_comps:
        parts.append(f"{len(external_comps)} external component reference(s)")
    if external_kbs:
        parts.append(f"{len(external_kbs)} external KB reference(s)")
    ref_str = " and ".join(parts)

    return [Finding(
        code="WIZ104",
        severity=Severity.WARNING,
        location=Location(entity="WizFile", id="", field=None),
        message=(
            f"Export contains {ref_str}. "
            f"Confirm each is an intentional Component Library import."
        ),
    )]


# ---------------------------------------------------------------------------
# WIZ105: Conditional Judgment missing Null branch on a date field
# Uses legacy IR (wf.components / FlowNode.raw) because FlowModelNode does
# not carry branch_judgement_condition data.
# ---------------------------------------------------------------------------

def _check_null_branches(wf: WizFile) -> list[Finding]:
    """WIZ105: Conditional judgment on date field MUST have a default or Null branch."""
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
                        message="Missing fallback/null branch on Date variable",
                    ))
                    # Only emit once per node even if multiple date variables are missing checks
                    break
    return out
