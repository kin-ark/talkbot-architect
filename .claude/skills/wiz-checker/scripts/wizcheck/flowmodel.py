"""FlowModel — envelope/routes-based node and branch extraction.

Builds a FlowModel directly from the raw WIZ export dict.
Canonical sources:
  - Nodes:  BizSpeechComponent[i].details  (dict keyed by node UUID)
  - Edges:  BizSpeechComponent[i].routes   (dict keyed by source node UUID)
  - Labels: details[nodeUuid].data.all_client_intent[j].id == portUuid in routes

JSON-string wrapping: raw exports wrap BizSpeechComponent and details as JSON
strings. unwrap() handles both forms transparently.

Task 3 will populate KBView.multi_round; this task leaves it None.
"""
from __future__ import annotations

import contextlib
import json
import re
from dataclasses import dataclass, field
from typing import Any

from wizcheck.flow_constants import NODE_TYPE_MAP, UNKNOWN_NODE_TYPE

# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def unwrap(value: Any) -> list | dict:
    """Normalise a value that may be a JSON-encoded string, a list, or a dict.

    - JSON string → json.loads result (list or dict)
    - list/dict   → returned as-is (same object)
    - None        → [] (empty list sentinel)
    """
    if value is None:
        return []
    if isinstance(value, (list, dict)):
        return value
    if isinstance(value, str):
        return json.loads(value)
    return value


def node_type_of(envelope_or_data: dict) -> str:
    """Return the stable node-type name for an envelope or data dict.

    Reads the ``type`` key at the top level of *envelope_or_data* first;
    if absent, falls back to ``envelope_or_data["data"]["type"]``.
    Maps through NODE_TYPE_MAP; returns ``"unknown"`` for unmapped values
    or when ``type`` is entirely absent.
    """
    raw_type = envelope_or_data.get("type")
    if raw_type is None:
        data = envelope_or_data.get("data", {})
        raw_type = data.get("type") if isinstance(data, dict) else None
    if raw_type is None:
        return UNKNOWN_NODE_TYPE
    return NODE_TYPE_MAP.get(raw_type, UNKNOWN_NODE_TYPE)


# ---------------------------------------------------------------------------
# Dataclasses (exact field names — Phase 5 frontend depends on these)
# ---------------------------------------------------------------------------

@dataclass
class BranchEdge:
    label: str                          # branch/intent name, condition name, or ""
    kind: str                           # "intent" | "condition" | "default" | "next" | "exit"
    target_uuid: str | None = None      # destination node in SAME component
    target_component: str | None = None # type-4 cross-component jump (componentUuid)
    target_kb: int | None = None        # type-8 KB jump (knowledgeId as int)
    terminal: str | None = None         # "hangup" (type-2 exit) | "transfer" (type-13 transfer)


@dataclass
class FlowModelNode:
    uuid: str
    label: str
    node_type: str                       # via NODE_TYPE_MAP, else "unknown"
    text: str                            # first data.list[].text (joined by " / " if multiple)
    referenced_vars: list[str]           # names from data.node_variables[].name + {var} refs
    allowed_kbs: list[int]               # data.allow_jump_knowledges cast to int
    # raw envelope data dict (branch conditions, sentenceText, etc.)
    data: dict = field(default_factory=dict)
    branches: list[BranchEdge] = field(default_factory=list)


@dataclass
class FlowComponent:
    uuid: str
    name: str
    sort_index: int
    entry_uuid: str | None              # node with is_default true
    root_uuids: list[str]               # [entry_uuid] if present else []
    nodes: dict[str, FlowModelNode]
    parent_uuid: str = ""               # populated from parentUuid; "" or "0" = top-level


@dataclass
class KBView:
    knowledge_id: int
    title: str
    kd_type: int
    intents: list[int]
    multi_round: FlowModel | None = None  # set in Task 3; leave None here


@dataclass
class FlowModel:
    components: list[FlowComponent]
    knowledge_bases: list[KBView]


# ---------------------------------------------------------------------------
# Internal extraction helpers
# ---------------------------------------------------------------------------

_VAR_REF_RE = re.compile(r"\{([A-Za-z_]\w*)\}")


def _extract_text(data: dict) -> str:
    """Join text from data.list[] with ' / ', skipping empty strings.

    Handles both dict form (``{"text": "..."}`` — spec shape) and plain
    string form (bare string — observed in the real export).
    """
    items = data.get("list")
    if not isinstance(items, list):
        items = []
    parts: list[str] = []
    for item in items:
        if isinstance(item, dict):
            t = item.get("text", "")
        elif isinstance(item, str):
            t = item
        else:
            t = ""
        if t:
            parts.append(t)
    return " / ".join(parts)


def _extract_referenced_vars(data: dict, text: str) -> list[str]:
    """Collect variable names from data.node_variables[] plus {Name} refs in text."""
    seen: dict[str, None] = {}  # ordered set
    node_vars = data.get("node_variables")
    if isinstance(node_vars, list):
        for v in node_vars:
            name = v.get("name") if isinstance(v, dict) else None
            if name:
                seen[name] = None
    for match in _VAR_REF_RE.finditer(text):
        name = match.group(1)
        if name not in seen:
            seen[name] = None
    return list(seen)


def _build_branches(
    node_uuid: str,
    node_type: str,
    data: dict,
    routes: dict,
) -> list[BranchEdge]:
    """Build the branch list for one node according to the brief's rules."""
    branches: list[BranchEdge] = []

    if node_type == "exit_port":
        # type 4 with empty appoint_node_id + empty specificComponentName:
        # a named terminal return port in a child (nested) component.
        label = data.get("name") or ""
        branches.append(BranchEdge(
            label=label,
            kind="exit",
        ))
        return branches

    if node_type == "goto_component":
        # type 4: ONE cross-component exit edge
        target_comp = data.get("appoint_node_id")
        label = data.get("specificComponentName") or "go to component"
        branches.append(BranchEdge(
            label=label,
            kind="exit",
            target_component=target_comp,
        ))
        return branches

    if node_type == "nested_component":
        # type 11: one branch per exit port of the child component.
        # Routes key = child exit node uuid; target uuid = parent's downstream node.
        # Port label resolved from canvas.ports.items[].name where items[].uuid == route key.
        # The canvas port items were injected into data as '_canvas_ports_items' by _build_node.
        canvas_ports_items: list[dict] = data.get("_canvas_ports_items", [])
        # Build uuid→name lookup from ports items
        port_uuid_to_name: dict[str, str] = {}
        for item in canvas_ports_items:
            if isinstance(item, dict):
                port_id = item.get("uuid")
                if port_id:
                    port_uuid_to_name[port_id] = item.get("name", "")

        edge_map = routes.get(node_uuid, {})
        if isinstance(edge_map, dict):
            for exit_port_uuid, edge in edge_map.items():
                target_uuid = None
                if isinstance(edge, dict):
                    tgt = edge.get("target")
                    if isinstance(tgt, dict):
                        target_uuid = tgt.get("uuid") or None
                label = port_uuid_to_name.get(exit_port_uuid, "")
                branches.append(BranchEdge(
                    label=label,
                    kind="exit",
                    target_uuid=target_uuid,
                ))
        return branches

    if node_type == "goto_kb":
        # type 8: ONE KB exit edge
        raw_kb_id = data.get("appoint_knowledge_id")
        try:
            target_kb = int(raw_kb_id) if raw_kb_id not in (None, "") else None
        except (ValueError, TypeError):
            target_kb = None
        branches.append(BranchEdge(
            label="go to KB",
            kind="exit",
            target_kb=target_kb,
        ))
        return branches

    if node_type == "exit":
        # type 2: ONE terminal hang-up edge (is_transfer flag is NOT authoritative;
        # transfer-to-human is a distinct node type 13 — see NODE_TYPE_MAP).
        branches.append(BranchEdge(
            label="hang up",
            kind="exit",
            terminal="hangup",
        ))
        return branches

    if node_type == "transfer":
        # type 13: ONE terminal transfer-to-human edge
        branches.append(BranchEdge(
            label="transfer",
            kind="exit",
            terminal="transfer",
        ))
        return branches

    # types 1, 5, 7, 10 — derive edges from routes + all_client_intent
    edge_map = routes.get(node_uuid, {})
    if not isinstance(edge_map, dict) or not edge_map:
        return branches

    # Build port-uuid → intent-name lookup from all_client_intent
    intent_lookup: dict[str, str] = {}
    aci = data.get("all_client_intent")
    if isinstance(aci, list):
        for entry in aci:
            if not isinstance(entry, dict):
                continue
            port_id = entry.get("id")
            if port_id:
                intent_lookup[port_id] = entry.get("name", "")

    for port_uuid, edge in edge_map.items():
        target = edge.get("target") if isinstance(edge, dict) else None
        if not isinstance(target, dict):
            continue
        target_uuid = target.get("uuid")
        if not target_uuid:
            continue
        label = intent_lookup.get(port_uuid, "")

        if node_type == "conditional":
            kind = "default" if label == "Default" else "condition"
        elif node_type in ("talk", "talk_continue"):
            kind = "intent"
        elif node_type == "variable_assignment":
            kind = "next"
        else:
            kind = "next"

        branches.append(BranchEdge(
            label=label,
            kind=kind,
            target_uuid=target_uuid,
        ))

    return branches


def _build_node(
    node_uuid: str,
    envelope: dict,
    routes: dict,
) -> FlowModelNode:
    """Build a FlowModelNode from a details envelope."""
    if not isinstance(envelope, dict):
        envelope = {}
    node_type = node_type_of(envelope)
    data = envelope.get("data")
    if not isinstance(data, dict):
        data = {}

    # Type-4 disambiguation: a type-4 node with empty appoint_node_id AND
    # empty specificComponentName is an exit_port (named return in a child
    # component), not a goto_component.
    if (
        node_type == "goto_component"
        and data.get("appoint_node_id", "") == ""
        and data.get("specificComponentName", "") == ""
    ):
        node_type = "exit_port"

    # For nested_component (type 11), inject canvas port items into data so
    # _build_branches can resolve exit port labels from canvas.ports.items.
    # We use a private key to avoid mutating the original data dict.
    if node_type == "nested_component":
        canvas = envelope.get("canvas", {})
        if isinstance(canvas, dict):
            ports = canvas.get("ports", {})
            canvas_ports_items = ports.get("items", []) if isinstance(ports, dict) else []
        else:
            canvas_ports_items = []
        # Make a shallow copy so we don't mutate the original envelope data
        data = dict(data)
        data["_canvas_ports_items"] = canvas_ports_items

    label = (
        envelope.get("name")
        or data.get("name")
        or node_uuid
    )

    text = _extract_text(data)
    referenced_vars = _extract_referenced_vars(data, text)
    allowed_kbs = []
    akj = data.get("allow_jump_knowledges")
    if isinstance(akj, list):
        for k in akj:
            with contextlib.suppress(ValueError, TypeError):
                allowed_kbs.append(int(k))

    branches = _build_branches(node_uuid, node_type, data, routes)

    # Strip the private injection key from the stored data dict
    data.pop("_canvas_ports_items", None)

    return FlowModelNode(
        uuid=node_uuid,
        label=label,
        node_type=node_type,
        text=text,
        referenced_vars=referenced_vars,
        allowed_kbs=allowed_kbs,
        data=data,
        branches=branches,
    )


# ---------------------------------------------------------------------------
# KB-plane helpers
# ---------------------------------------------------------------------------

def _build_multiround(kb: dict, data: dict) -> FlowModel | None:
    """Return a shallow FlowModel containing the multi-round component, or None.

    Scans kb.kdInfo for an entry with a non-empty multipleAppointId.  If found,
    builds all components from `data`, picks the one matching that UUID, and
    returns FlowModel(components=[that_component], knowledge_bases=[]).
    Does NOT recurse into nested multi-round (one level only).
    """
    multi_uuid: str | None = None
    kd_info = unwrap(kb.get("kdInfo"))
    if not isinstance(kd_info, list):
        kd_info = []
    for item in kd_info:
        if not isinstance(item, dict):
            continue
        candidate = item.get("multipleAppointId")
        if candidate:
            multi_uuid = candidate
            break

    if not multi_uuid:
        return None

    all_components = build_components(data)
    target = next((c for c in all_components if c.uuid == multi_uuid), None)
    if target is None:
        return None

    return FlowModel(components=[target], knowledge_bases=[])


def _build_kbs(data: dict) -> list[KBView]:
    """Build KBView list from BizKnowledgeInfo in the raw export dict."""
    kbs_raw = unwrap(data.get("BizKnowledgeInfo"))
    if not isinstance(kbs_raw, list):
        kbs_raw = []
    result: list[KBView] = []
    for kb in kbs_raw:
        if not isinstance(kb, dict):
            continue
        kb_id = kb.get("knowledgeId")
        if kb_id is None:
            continue
        try:
            knowledge_id = int(kb_id)
        except (ValueError, TypeError):
            continue
        title = kb.get("kdTitle", "") or ""
        try:
            kd_type = int(kb.get("kdType", 0) or 0)
        except (ValueError, TypeError):
            kd_type = 0
        intents_raw = unwrap(kb.get("intents"))
        intents = []
        if isinstance(intents_raw, list):
            for i in intents_raw:
                if isinstance(i, dict) and "intentId" in i:
                    with contextlib.suppress(ValueError, TypeError):
                        intents.append(int(i["intentId"]))
        multi_round = _build_multiround(kb, data)
        result.append(KBView(
            knowledge_id=knowledge_id,
            title=title,
            kd_type=kd_type,
            intents=intents,
            multi_round=multi_round,
        ))
    return result


# ---------------------------------------------------------------------------
# Public build functions
# ---------------------------------------------------------------------------

def build_components(data: dict) -> list[FlowComponent]:
    """Build FlowComponent list from raw export dict.

    Task 3 will call this directly when building the KB plane.
    """
    raw_components = unwrap(data.get("BizSpeechComponent"))
    if not isinstance(raw_components, list):
        raw_components = []
    components: list[FlowComponent] = []

    for comp in raw_components:
        if not isinstance(comp, dict):
            continue
        comp_uuid = comp.get("componentUuid", "")
        comp_name = comp.get("name", "")
        sort_index = comp.get("sortIndex", 0)
        # details/routes may be absent, an empty/"null" JSON string (real exports
        # emit `details: "null"` for empty components), or already-parsed objects.
        # Coerce anything that isn't a dict to an empty dict.
        details = unwrap(comp.get("details"))
        if not isinstance(details, dict):
            details = {}
        routes = unwrap(comp.get("routes"))
        if not isinstance(routes, dict):
            routes = {}

        entry_uuid: str | None = None
        nodes: dict[str, FlowModelNode] = {}

        for node_uuid, envelope in details.items():
            node = _build_node(node_uuid, envelope, routes)
            nodes[node_uuid] = node
            if isinstance(envelope, dict) and envelope.get("is_default"):
                entry_uuid = node_uuid

        root_uuids = [entry_uuid] if entry_uuid else []

        parent_uuid = comp.get("parentUuid", "") or ""

        components.append(FlowComponent(
            uuid=comp_uuid,
            name=comp_name,
            sort_index=sort_index,
            entry_uuid=entry_uuid,
            root_uuids=root_uuids,
            nodes=nodes,
            parent_uuid=parent_uuid,
        ))

    return components


def build_flow_model(data: dict) -> FlowModel:
    """Build a FlowModel from the raw export dict.

    KB plane (KBView assembly, multi_round links) is left to Task 3.
    """
    components = build_components(data)
    knowledge_bases = _build_kbs(data)
    return FlowModel(components=components, knowledge_bases=knowledge_bases)


# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------

def _branch_to_dict(b: BranchEdge) -> dict:
    return {
        "label": b.label,
        "kind": b.kind,
        "target_uuid": b.target_uuid,
        "target_component": b.target_component,
        "target_kb": b.target_kb,
        "terminal": b.terminal,
    }


def _node_to_dict(n: FlowModelNode) -> dict:
    return {
        "uuid": n.uuid,
        "label": n.label,
        "node_type": n.node_type,
        "text": n.text,
        "referenced_vars": n.referenced_vars,
        "allowed_kbs": n.allowed_kbs,
        "data": n.data,
        "branches": [_branch_to_dict(b) for b in n.branches],
    }


def _component_to_dict(c: FlowComponent) -> dict:
    return {
        "uuid": c.uuid,
        "name": c.name,
        "sort_index": c.sort_index,
        "entry_uuid": c.entry_uuid,
        "root_uuids": c.root_uuids,
        "nodes": {uuid: _node_to_dict(n) for uuid, n in c.nodes.items()},
        "parent_uuid": c.parent_uuid,
    }


def _kb_to_dict(kb: KBView) -> dict:
    return {
        "knowledge_id": kb.knowledge_id,
        "title": kb.title,
        "kd_type": kb.kd_type,
        "intents": kb.intents,
        "multi_round": flow_model_to_dict(kb.multi_round) if kb.multi_round else None,
    }


def flow_model_to_dict(fm: FlowModel) -> dict:
    """Serialise FlowModel to a JSON-compatible dict."""
    return {
        "components": [_component_to_dict(c) for c in fm.components],
        "knowledge_bases": [_kb_to_dict(kb) for kb in fm.knowledge_bases],
    }
