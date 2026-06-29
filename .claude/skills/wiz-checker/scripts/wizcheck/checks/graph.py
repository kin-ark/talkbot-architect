"""Flow-graph integrity checks (WIZ100..WIZ199).

WIZ100-WIZ105 run against wf.flow_model. When wf.flow_model is None those
checks are skipped — use parse_dict() to get a populated WizFile.

WIZ106 (phantom routes port-key) reads from component.raw only, so it always
runs regardless of whether wf.flow_model is populated.
"""

from __future__ import annotations

import json
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


# ---------------------------------------------------------------------------
# WIZ106 helpers — raw-IR read, no flow_model required
# ---------------------------------------------------------------------------

# Terminal node types: routes must be empty.
# type 4 = goto_component OR exit_port — both terminal.
_TERMINAL_TYPE_INTS = frozenset({2, 4, 8, 13})


def _decode(raw: object) -> dict:
    """Decode an escaped-JSON field (or return {} on failure)."""
    if raw is None or raw in ("", "null"):
        return {}
    try:
        return json.loads(raw) if isinstance(raw, str) else raw  # type: ignore[return-value]
    except (ValueError, TypeError):
        return {}


def _child_exit_uuids(all_details_by_comp: dict[str, dict], sub_uuid: str) -> set[str] | None:
    """Return the child component's exit_port node uuids, or None if child absent.

    exit_port = type-4 with EMPTY appoint_node_id AND specificComponentName.
    Returns None when the child component is not in the export (external/library).
    """
    det = all_details_by_comp.get(sub_uuid)
    if det is None:
        return None
    out: set[str] = set()
    for u, n in det.items():
        d = n.get("data", {})
        if (
            n.get("type") == 4
            and not d.get("appoint_node_id")
            and not d.get("specificComponentName")
        ):
            out.add(u)
    return out


def _check_routes_validity(wf: WizFile) -> list[Finding]:
    """WIZ106: every routes port-key must reference a real out-port of the node.

    - talk/conditional/assign -> a canvas.ports.items id.
    - nested (type 11) -> a child-exit-node uuid (resolved from the child component's
      exit_port nodes). If the child is absent (external/library), tolerate.
    - terminal (type 2/4/8/13) -> routes must be {}.
    A port-key matching none = phantom route (import-breaker) -> ERROR.
    """
    out: list[Finding] = []
    # Build componentUuid -> decoded details map (needed for nested child resolution).
    details_by_comp: dict[str, dict] = {}
    for comp in wf.components.values():
        cu = comp.raw.get("componentUuid", "")
        details_by_comp[cu] = _decode(comp.raw.get("details"))

    for comp in wf.components.values():
        cu = comp.raw.get("componentUuid", "")
        details = details_by_comp.get(cu, {})
        routes = _decode(comp.raw.get("routes"))
        if not isinstance(routes, dict):
            continue

        for node_uuid, portmap in routes.items():
            node = details.get(node_uuid)
            if node is None:
                continue  # routes key for an unknown node — left to other checks
            ntype = node.get("type")
            if ntype in _TERMINAL_TYPE_INTS:
                if portmap:  # terminal nodes must have empty routes
                    out.append(Finding(
                        code="WIZ106",
                        severity=Severity.ERROR,
                        location=Location(
                            entity="BizSpeechComponent", id=cu, field="routes"
                        ),
                        message=(
                            f"Terminal node {node_uuid!r} (type {ntype}) in component "
                            f"{cu!r} has non-empty routes; terminal nodes must not route."
                        ),
                    ))
                continue

            if not isinstance(portmap, dict):
                continue

            if ntype == 11:
                # nested node — valid port keys are the child's exit_port uuids
                sub = node.get("data", {}).get("subComponentUuid", "")
                valid = _child_exit_uuids(details_by_comp, sub)
                if valid is None:
                    continue  # external/library child — cannot resolve; tolerate
            else:
                # talk / conditional / assign — valid keys are canvas.ports.items ids
                valid = {
                    it.get("id")
                    for it in (node.get("canvas") or {}).get("ports", {}).get("items", [])
                }

            # `valid` is a (possibly empty) set here — the unresolvable nested/library
            # case already `continue`d above. An empty set means the node declares NO
            # real out-ports, so any routed port-key is a phantom (do NOT short-circuit
            # on empty, which would let phantoms through).
            for port_key in portmap:
                if port_key not in valid:
                    out.append(Finding(
                        code="WIZ106",
                        severity=Severity.ERROR,
                        location=Location(
                            entity="BizSpeechComponent", id=cu, field="routes"
                        ),
                        message=(
                            f"Node {node_uuid!r} (type {ntype}) in component {cu!r} has a "
                            f"routes port-key {port_key!r} that is not a real out-port "
                            f"(phantom route — breaks WIZ import)."
                        ),
                    ))
    return out


_TERMINAL_NODE_TYPES = frozenset({
    "exit",
    "transfer",
    "goto_component",
    "goto_kb",
    "exit_port",   # type-4 with empty appoint fields — distinct from goto_component
})


def _check_component_exit(wf: WizFile) -> list[Finding]:
    """WIZ107: a component with >=1 non-terminal node must contain >=1 terminal node."""
    fm = wf.flow_model
    assert fm is not None
    out: list[Finding] = []
    for comp in fm.components:
        types = [n.node_type for n in comp.nodes.values()]
        if not types:
            continue
        has_nonterminal = any(t not in _TERMINAL_NODE_TYPES for t in types)
        has_terminal = any(t in _TERMINAL_NODE_TYPES for t in types)
        if has_nonterminal and not has_terminal:
            out.append(Finding(
                code="WIZ107", severity=Severity.WARNING,
                location=Location(entity="BizSpeechComponent", id=comp.uuid, field=None),
                message=(
                    f"Component {comp.name!r} ({comp.uuid!r}) has no terminal node "
                    f"(Exit/Transfer/Goto) — the flow cannot end."
                ),
            ))
    return out


def _check_talk_unclassified(wf: WizFile) -> list[Finding]:
    """WIZ108: every talk node must have an Unclassified branch that is connected."""
    fm = wf.flow_model
    assert fm is not None
    out: list[Finding] = []
    for comp in fm.components:
        for node in comp.nodes.values():
            if node.node_type != "talk":
                continue
            unc = [b for b in node.branches if b.label == "Unclassified"]
            connected = any(
                (b.target_uuid or b.target_component or b.target_kb or b.terminal)
                for b in unc
            )
            if not connected:
                why = (
                    "has no Unclassified branch" if not unc
                    else "Unclassified branch is unconnected"
                )
                out.append(Finding(
                    code="WIZ108", severity=Severity.WARNING,
                    location=Location(entity="FlowNode", id=node.uuid, field=None),
                    message=(
                        f"Talk node {node.uuid!r} (label={node.label!r}) {why}."
                    ),
                ))
    return out


def check_graph(wf: WizFile) -> list[Finding]:
    findings: list[Finding] = []
    # WIZ106 reads raw component data only — runs even when flow_model is None.
    findings.extend(_check_routes_validity(wf))
    if wf.flow_model is None:
        return findings
    findings.extend(_check_orphan_refs(wf))
    findings.extend(_check_unreachable(wf))
    findings.extend(_check_dead_ends(wf))
    findings.extend(_check_cycles(wf))
    findings.extend(_check_library_refs_rollup(wf))
    findings.extend(_check_null_branches(wf))
    findings.extend(_check_component_exit(wf))
    findings.extend(_check_talk_unclassified(wf))
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
# WIZ101: unreachable — nodes not reachable from the component's entry node(s)
# ---------------------------------------------------------------------------

def _check_unreachable(wf: WizFile) -> list[Finding]:
    """WIZ101: nodes that cannot be reached from any root within their component.

    For each FlowComponent the reachable set is computed by BFS/DFS from the
    component's entry node(s):
    - Use comp.root_uuids if non-empty (= [entry_uuid] when is_default node exists).
    - If root_uuids is empty (no entry node declared) skip the component — cannot
      determine reachability without a starting point.

    Only same-component edges (branch.target_uuid present in comp.nodes) are
    followed. Cross-component jumps and KB jumps are intentional exits, not
    intra-component edges.
    """
    fm = wf.flow_model
    assert fm is not None
    out: list[Finding] = []
    for comp in fm.components:
        if not comp.root_uuids:
            # No entry point declared — cannot compute reachability; skip.
            continue
        node_uuids: set[str] = set(comp.nodes.keys())
        # BFS from each root, following same-component edges only.
        reachable: set[str] = set()
        queue: list[str] = list(comp.root_uuids)
        for seed in queue:
            if seed in node_uuids:
                reachable.add(seed)
        i = 0
        while i < len(queue):
            current_uuid = queue[i]
            i += 1
            node = comp.nodes.get(current_uuid)
            if node is None:
                continue
            for branch in node.branches:
                if (
                    branch.target_uuid is not None
                    and branch.target_uuid in node_uuids
                    and branch.target_uuid not in reachable
                ):
                    reachable.add(branch.target_uuid)
                    queue.append(branch.target_uuid)
        for node_uuid in node_uuids:
            if node_uuid not in reachable:
                out.append(Finding(
                    code="WIZ101",
                    severity=Severity.WARNING,
                    location=Location(entity="FlowNode", id=node_uuid, field=None),
                    message=f"FlowNode {node_uuid!r} is unreachable from any component root.",
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
# Reads FlowModelNode.data['branch'] via wf.flow_model.
# Returns [] when wf.flow_model is None (guarded at check_graph entry).
# ---------------------------------------------------------------------------

def _eval_null_branches_for_node(node_uuid: str, branches: list, wf: WizFile) -> list[Finding]:
    """WIZ105 null-branch evaluator for a single node.

    Accepts the node UUID (str), the branch list, and the WizFile (for variable
    lookup). Returns a list of findings (0 or 1 per node).
    """
    out: list[Finding] = []

    # Find which date variables are being evaluated in this node
    date_var_ids_evaluated: set[int] = set()
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
        return out

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
                    null_op = op in ("is empty", "is_empty", "isnull", "is_null")
                    null_rval = rval in ("null", "empty", "")
                    if null_op or null_rval:
                        has_null_branch = True
                        break
            if has_null_branch:
                break

        if not has_null_branch:
            out.append(Finding(
                code="WIZ105",
                severity=Severity.ERROR,
                location=Location(entity="FlowNode", id=node_uuid, field=None),
                message="Missing fallback/null branch on Date variable",
            ))
            # Only emit once per node even if multiple date variables are missing checks
            break
    return out


def _check_null_branches(wf: WizFile) -> list[Finding]:
    """WIZ105: Conditional judgment on date field MUST have a default or Null branch.

    Reads from wf.flow_model (FlowModelNode.data['branch']). Called only when
    wf.flow_model is not None.
    """
    assert wf.flow_model is not None
    out: list[Finding] = []
    for fc in wf.flow_model.components:
        for node in fc.nodes.values():
            if node.node_type != "conditional":
                continue
            branches = node.data.get("branch") or []
            out.extend(_eval_null_branches_for_node(node.uuid, branches, wf))
    return out


