"""Structure ops: add BSC keys, populate the details payload, add a component."""

from __future__ import annotations

import json

from wizbuilder.noderender import EdgeSpec, NodeSpec, render_component_nodes

from wizmodifier import codec
from wizmodifier.io import InputBundle
from wizmodifier.ops._bsc import get_components, require_component, set_components

# The 6 keys wiz-builder adds to every BSC entry (canvases.py:119-124).
# NOTE: nluConf and outboundPorts overlap with _SECONDARY_STRIP_KEYS. add-bsc-keys is an
# opt-in op that intentionally re-adds those keys when explicit template parity is needed.
DEFAULT_BSC_KEYS = {
    "inboundPorts": "[]",
    "outboundPorts": "[]",
    "routes": "[]",
    "nluConf": "{}",
    "sourceUuid": "",
    # topFloorDetails is a JSON-encoded LIST (wiz-checker schema fields.md); WIZ import
    # parses it as an array, so "{}" => "expect [, actual {" once a component has nodes.
    "topFloorDetails": "[]",
}

# Keys from the Empty+Dialogue template that must not appear on secondary components.
# Confirmed by diffing real WIZ.AI multi-component exports vs T8 output:
# - createBy/createTime/language: template server metadata, absent from all real secondary BSCs
# - nluConf/outboundPorts/updateBy: only on real component[0], not component[1+]
_SECONDARY_STRIP_KEYS = frozenset({
    "createBy", "createTime", "language",
    "nluConf", "outboundPorts", "updateBy",
})

# Default node_language code: "3" = Bahasa Indonesia (IDN).
# The modifier operates on an existing export and has no manifest language field.
# We default to IDN ("3") because it is the only validated language code in this MVP.
# If the export's BizSpeechComponent carries a "language" field with a known mapping,
# that value is preferred; otherwise "3" is used.
_LANGUAGE_CODE_MAP = {0: "3"}  # WIZ language int 0 → node_language "3" (IDN)
_DEFAULT_NODE_LANGUAGE = "3"

# Valid conditional-branch operator tokens (authoring form). Mirrors manifest.py's
# _VALID_OPERATORS — duplicated here rather than imported because manifest.py keeps it
# private and the modifier must not depend on wiz-builder internals beyond noderender.
# The 11-op set confirmed from real WIZ.AI exports (see noderender._WIZ_OPERATOR).
_VALID_OPERATORS = frozenset(
    {">", ">=", "<", "<=", "=", "!=", "In", "NotIn", "IsNull", "NotNull", "Contains"}
)
_UNARY_OPERATORS = frozenset({"IsNull", "NotNull"})


def _speech_variables(bundle: InputBundle) -> list[dict]:
    """Decode the export's current SpeechVariable list (empty list on absence/parse miss)."""
    raw = bundle.data.get("SpeechVariable", "[]")
    try:
        sv = codec.decode(raw) if isinstance(raw, str) else raw
    except (ValueError, TypeError):
        return []
    return sv if isinstance(sv, list) else []


def _declared_var_names(bundle: InputBundle) -> set[str]:
    """Variable names from the bundle's current SpeechVariable (authoritative here)."""
    return {v.get("name") for v in _speech_variables(bundle) if v.get("name")}


def _var_source_map(bundle: InputBundle) -> dict[str, int]:
    """Map variable name → variableSource int (0=custom, 1=system) for rendering."""
    return {
        v.get("name"): v.get("variableSource", 0)
        for v in _speech_variables(bundle)
        if v.get("name")
    }


def _is_exit_port_node(node_obj: dict) -> bool:
    """Return True if node_obj (a decoded details entry) is an exit_port node.

    An exit_port is type-4 with EMPTY appoint_node_id/specificComponentName,
    distinguishing it from goto_component which populates both.
    """
    data = node_obj.get("data") or {}
    return (
        node_obj.get("type") == 4
        and data.get("appoint_node_id", "") == ""
        and data.get("specificComponentName", "") == ""
    )


def _exit_ports_from_comp(comp: dict) -> dict[str, str]:
    """Scan a BSC entry's decoded details for exit_port nodes.

    Returns {exit-port-name (data["name"]): node_uuid} for all exit_port nodes
    in the component.  Empty dict when the component has no details or no exit ports.
    """
    raw_details = comp.get("details")
    if not raw_details or raw_details in ("null", ""):
        return {}
    try:
        details = json.loads(raw_details) if isinstance(raw_details, str) else raw_details
    except (ValueError, TypeError):
        return {}
    if not isinstance(details, dict):
        return {}
    result: dict[str, str] = {}
    for node_uuid, node_obj in details.items():
        if _is_exit_port_node(node_obj):
            name = (node_obj.get("data") or {}).get("name", "")
            if name:
                result[name] = node_uuid
    return result


def _find_nested_ref_to(
    comp_by_name: dict[str, dict], target_comp_uuid: str, exclude_comp_name: str | None = None
) -> str | None:
    """Return the name of ANY component that already has a type-11 node pointing at
    `target_comp_uuid` (subComponentUuid), ignoring `exclude_comp_name` if given.

    Used by _validate_special_node to enforce single-parent uniqueness (M2).
    """
    for cname, comp in comp_by_name.items():
        if cname == exclude_comp_name:
            continue
        raw_details = comp.get("details")
        if not raw_details or raw_details in ("null", ""):
            continue
        try:
            details = json.loads(raw_details) if isinstance(raw_details, str) else raw_details
        except (ValueError, TypeError):
            continue
        if not isinstance(details, dict):
            continue
        for node_obj in details.values():
            if node_obj.get("type") == 11:
                data = node_obj.get("data") or {}
                if data.get("subComponentUuid") == target_comp_uuid:
                    return cname
    return None


def _validate_special_node(
    node: dict,
    declared_vars: set[str],
    canvas_node_ids: set[str],
    prefix: str,
    comp_by_name: dict[str, dict] | None = None,
    edge_branches_from_node: set[str] | None = None,
    current_comp_name: str | None = None,
    intent_names: set[str] | None = None,
) -> None:
    """Validate a conditional/assign/exit_port/nested node's config before rendering.

    Mirrors manifest.py invariants; branch targets resolve against canvas_node_ids
    (ids valid in THIS op's context).  Raises ValueError on any violation, prefixed
    with `prefix` ("append-node:" / "add-component:").

    comp_by_name: optional {component-name: bsc-dict} — required for nested validation.
    edge_branches_from_node: optional set of branch names used in edges leaving this node
        — used to validate that nested out-edges name real child exit ports.
    current_comp_name: optional name of the component receiving this node — used to
        skip self when scanning for existing nested references (M2).
    intent_names: optional set of intent names declared in the export's SpeechIntent —
        used to validate a talk node's config.branch_intents references.
    """
    ntype = node.get("type")

    if ntype in (None, "talk"):
        bi = (node.get("config") or {}).get("branch_intents") or {}
        if bi:
            nid = node.get("id", "<no-id>")
            known = intent_names or set()
            for label, names in bi.items():
                for iname in (names or []):
                    if iname not in known:
                        raise ValueError(
                            f"{prefix} talk node {nid!r} branch {label!r} references "
                            f"{iname!r} which is not an intent in this export"
                        )
            if "Unclassified" not in (edge_branches_from_node or set()):
                raise ValueError(
                    f"{prefix} talk node {nid!r} declares branch_intents but has "
                    f"no connected Unclassified branch"
                )

    if ntype not in (
        "conditional", "assign", "exit_port", "nested", "goto_kb", "goto", "goto_mr",
        "talk_continue"
    ):
        return
    nid = node.get("id", "<no-id>")
    cfg = node.get("config") or {}

    if ntype in ("goto", "goto_kb", "goto_mr", "talk_continue"):
        target = cfg.get("target")
        # talk_continue and goto_kb have optional targets; goto and goto_mr require them
        if ntype in ("goto", "goto_mr") and not target:
            raise ValueError(
                f"{prefix} {ntype} node {nid!r} missing config.target"
            )
        # talk_continue: if target is present, validation is deferred to append_node
        # where we can check component categories
        return

    if ntype == "exit_port":
        name = cfg.get("name")
        if not name:
            raise ValueError(
                f"{prefix} exit_port node {nid!r} missing config.name"
            )
        # Terminal: caller must pass no outgoing edges for this node.
        if edge_branches_from_node:
            raise ValueError(
                f"{prefix} exit_port node {nid!r} is terminal and must not have outgoing edges"
            )
        return

    if ntype == "nested":
        target = cfg.get("target")
        if not target:
            raise ValueError(
                f"{prefix} nested node {nid!r} missing config.target"
            )
        if comp_by_name is None or target not in comp_by_name:
            raise ValueError(
                f"{prefix} nested node {nid!r} config.target {target!r} "
                f"does not match any existing component name"
            )
        child_exits = _exit_ports_from_comp(comp_by_name[target])
        if not child_exits:
            raise ValueError(
                f"{prefix} nested node {nid!r} target {target!r} must contain "
                f"at least one exit_port node"
            )
        # M2: single-parent uniqueness — a child canvas may only be wired to one parent.
        child_comp = comp_by_name[target]
        child_uuid = child_comp.get("componentUuid", "")
        existing_parent = _find_nested_ref_to(
            comp_by_name, child_uuid, exclude_comp_name=current_comp_name
        )
        if existing_parent is not None:
            raise ValueError(
                f"append-node: child {target!r} is already referenced by another nested node"
            )
        # Validate that any outgoing edge branch names actually name a child exit port.
        if edge_branches_from_node:
            for branch in edge_branches_from_node:
                if branch not in child_exits:
                    raise ValueError(
                        f"{prefix} nested node {nid!r} edge branch {branch!r} has no "
                        f"exit_port named {branch!r} in child {target!r}"
                    )
        return

    if ntype == "assign":
        var = cfg.get("variable")
        if var not in declared_vars:
            raise ValueError(
                f"{prefix} assign node {nid!r} config.variable {var!r} "
                f"is not a declared variable"
            )
        if "value" not in cfg:
            raise ValueError(f"{prefix} assign node {nid!r} missing config.value")
        return

    # conditional
    var = cfg.get("variable")
    if var not in declared_vars:
        raise ValueError(
            f"{prefix} conditional node {nid!r} config.variable {var!r} "
            f"is not a declared variable"
        )
    branches = cfg.get("branches") or []
    if not branches:
        raise ValueError(f"{prefix} conditional node {nid!r} has no branches")
    defaults = [b for b in branches if b.get("name") == "Default"]
    if len(defaults) != 1:
        raise ValueError(
            f"{prefix} conditional node {nid!r} must have exactly one Default branch, "
            f"found {len(defaults)}"
        )
    name_to_target: dict[str, str] = {}
    for b in branches:
        bname = b.get("name")
        target = b.get("to")
        if not bname or not target:
            raise ValueError(
                f"{prefix} conditional node {nid!r} branch missing name or to: {b!r}"
            )
        if target not in canvas_node_ids:
            raise ValueError(
                f"{prefix} conditional node {nid!r} branch {bname!r} "
                f"has unknown target {target!r}"
            )
        # one port = one target (same branch name must share the same `to`)
        if bname in name_to_target and name_to_target[bname] != target:
            raise ValueError(
                f"{prefix} conditional node {nid!r} branch {bname!r} "
                f"has conflicting target {target!r}"
            )
        name_to_target[bname] = target
        if bname == "Default":
            continue
        op = b.get("op")
        if op not in _VALID_OPERATORS:
            raise ValueError(
                f"{prefix} conditional node {nid!r} branch {bname!r} "
                f"has invalid operator {op!r}; must be one of {sorted(_VALID_OPERATORS)}"
            )
        has_value = "value" in b
        has_value_var = "value_var" in b
        if op in _UNARY_OPERATORS:
            if has_value or has_value_var:
                raise ValueError(
                    f"{prefix} conditional node {nid!r} branch {bname!r} uses unary op "
                    f"{op!r} but supplies an operand"
                )
        else:
            if has_value == has_value_var:
                raise ValueError(
                    f"{prefix} conditional node {nid!r} branch {bname!r} must set "
                    f"exactly one of value/value_var"
                )
            if has_value_var and b["value_var"] not in declared_vars:
                raise ValueError(
                    f"{prefix} conditional node {nid!r} branch {bname!r} value_var "
                    f"{b['value_var']!r} is not a declared variable"
                )


def _resolve_context(bundle: InputBundle) -> tuple[int, dict[str, int], list[str], str]:
    """Extract speech_id, branch_intent_ids, kb_ids, and node_language from bundle.data.

    Returns (speech_id, branch_intent_ids, kb_ids, node_language).
    Mirrors the lookups in wiz-builder's canvases.py:apply_canvases.
    """
    # speech_id from first component (same as canvases.py approach)
    bsc_raw = bundle.data.get("BizSpeechComponent", "[]")
    bsc = json.loads(bsc_raw) if isinstance(bsc_raw, str) else bsc_raw
    speech_id: int = bsc[0].get("speechId", 0) if bsc else 0

    # branch_intent_ids from SpeechIntent
    speech_intents_raw = bundle.data.get("SpeechIntent", "[]")
    speech_intents = (
        json.loads(speech_intents_raw)
        if isinstance(speech_intents_raw, str)
        else speech_intents_raw
    )
    branch_intent_ids: dict[str, int] = {
        i["intentName"]: i["intentId"]
        for i in speech_intents
        if i.get("intentName")
    }

    # kb_ids from BizKnowledgeInfo
    biz_kb_raw = bundle.data.get("BizKnowledgeInfo", "[]")
    biz_kb = json.loads(biz_kb_raw) if isinstance(biz_kb_raw, str) else biz_kb_raw
    kb_ids: list[str] = [str(k["knowledgeId"]) for k in biz_kb]

    # node_language: try to read from existing component[0]; default to IDN "3"
    if bsc:
        lang_int = bsc[0].get("language", 0)
        node_language = _LANGUAGE_CODE_MAP.get(lang_int, _DEFAULT_NODE_LANGUAGE)
    else:
        node_language = _DEFAULT_NODE_LANGUAGE

    return speech_id, branch_intent_ids, kb_ids, node_language


def _build_component_nav(bsc: list[dict]) -> list[dict]:
    """Build a component-nav list from BizSpeechComponent entries (mirrors canvases.py logic)."""
    return [
        {
            "sortIndexABS": i + 1,
            "sortIndex": i + 1,
            "editStatus": 1,
            "hangUpRate": "0.0%",
            "label": comp.get("name", ""),
            "title": comp.get("name", ""),
            "uuid": comp.get("componentUuid", ""),
            "hitRate": "0.0%",
            "parentId": "",
            "componentUuid": comp.get("componentUuid", ""),
            "useStatus": 2 if i == 0 else 1,
            "children": [],
            "value": comp.get("componentUuid", ""),
        }
        for i, comp in enumerate(bsc)
    ]


def _render_nodes(
    params: dict,
    bundle: InputBundle,
    canvas_index: int,
    comp_uuid: str,
    minter,
):
    """Build NodeSpec/EdgeSpec lists from params and call render_component_nodes.

    params["nodes"] is a list of {id, prompt}.
    params.get("edges") is an optional list of {from, branch, to} (from/to map to src/dst).

    For goto nodes, resolves config["target"] (a canvas name) to the target componentUuid
    by looking up existing components' name→componentUuid mapping.

    For nested nodes, resolves config["target_uuid"] from the export's components AND
    builds nested_exit_map from the child component's details (exit_port nodes).

    Returns a RenderedNodes instance.
    """
    # Build name→uuid map and name→comp dict from existing components.
    bsc_raw = bundle.data.get("BizSpeechComponent", "[]")
    bsc = json.loads(bsc_raw) if isinstance(bsc_raw, str) else bsc_raw
    comp_uuid_by_name: dict[str, str] = {
        c.get("name", ""): c.get("componentUuid", "") for c in bsc
    }
    comp_by_name: dict[str, dict] = {c.get("name", ""): c for c in bsc}
    component_nav = _build_component_nav(bsc)

    # Pre-compute per-node edge branch sets for terminal validation.
    raw_edges = params.get("edges") or []
    branches_by_node: dict[str, set[str]] = {}
    for e in raw_edges:
        branches_by_node.setdefault(e["from"], set()).add(e["branch"])

    # Validate special nodes before rendering.
    # current_comp_name is unknown here (we're in _render_nodes, not append_node/add_component),
    # so pass None — the single-parent check is enforced in append_node directly.
    declared_vars = _declared_var_names(bundle)
    batch_node_ids = {n["id"] for n in params["nodes"]}
    for n in params["nodes"]:
        ntype = n.get("type")
        if ntype in ("conditional", "assign", "exit_port", "nested"):
            _validate_special_node(
                n, declared_vars, batch_node_ids, "add-component:",
                comp_by_name=comp_by_name,
                edge_branches_from_node=branches_by_node.get(n["id"]),
                current_comp_name=None,
            )

    # Build nested_exit_map: {target-name: {exit-name: child-exit-uuid}} for all nested nodes.
    nested_exit_map: dict[str, dict[str, str]] = {}
    for n in params["nodes"]:
        if n.get("type") == "nested":
            target_name = (n.get("config") or {}).get("target", "")
            if target_name and target_name not in nested_exit_map:
                child_comp = comp_by_name.get(target_name)
                if child_comp:
                    nested_exit_map[target_name] = _exit_ports_from_comp(child_comp)

    node_specs = []
    for n in params["nodes"]:
        cfg = dict(n.get("config") or {})
        ntype = n.get("type", "talk")
        if ntype == "goto":
            target_name = cfg.get("target", "")
            cfg["target_uuid"] = comp_uuid_by_name.get(target_name, "")
            cfg["target_name"] = target_name
            if not cfg["target_uuid"]:
                raise ValueError(
                    f"goto node {n['id']!r}: config.target {target_name!r} "
                    f"does not match any existing component name"
                )
        elif ntype == "nested":
            target_name = cfg.get("target", "")
            cfg["target_uuid"] = comp_uuid_by_name.get(target_name, "")
        node_specs.append(
            NodeSpec(
                id=n["id"], prompt=n.get("prompt", ""),
                type=ntype, config=cfg,
            )
        )
    edge_specs = [EdgeSpec(src=e["from"], branch=e["branch"], dst=e["to"]) for e in raw_edges]

    speech_id, branch_intent_ids, kb_ids, node_language = _resolve_context(bundle)

    return render_component_nodes(
        node_specs,
        edge_specs,
        canvas_index=canvas_index,
        comp_uuid=comp_uuid,
        speech_id=speech_id,
        branch_intent_ids=branch_intent_ids,
        kb_ids=kb_ids,
        node_language=node_language,
        minter=minter,
        component_nav=component_nav,
        var_source_by_name=_var_source_map(bundle),
        nested_exit_map=nested_exit_map or None,
    )


def _append_sentence_cut_speech(bundle: InputBundle, new_rows: list[dict]) -> None:
    """Decode SentenceCutSpeech, extend with new_rows, re-encode."""
    raw = bundle.data.get("SentenceCutSpeech", "[]")
    existing = json.loads(raw) if isinstance(raw, str) else list(raw)
    existing.extend(new_rows)
    bundle.data["SentenceCutSpeech"] = codec.encode(existing)


def add_bsc_keys(bundle: InputBundle, params: dict, minter) -> None:
    comps = get_components(bundle)
    comp = require_component(comps, params["component"])
    keys = params.get("keys") or DEFAULT_BSC_KEYS
    comp.update(keys)
    set_components(bundle, comps)


def populate_details(bundle: InputBundle, params: dict, minter) -> None:
    """Populate details/routes/inboundPorts on an existing component using real node shape.

    params:
        component: int — index of the target BizSpeechComponent
        nodes: list[{id, prompt}] — node specs
        edges: list[{from, branch, to}] — optional edge specs (default [])

    Appends SentenceCutSpeech rows to bundle.data["SentenceCutSpeech"].
    """
    comps = get_components(bundle)
    index = params["component"]
    comp = require_component(comps, index)
    comp_uuid = comp.get("componentUuid") or ""
    if not comp_uuid:
        raise ValueError(
            f"populate-details: component {index} has no componentUuid; "
            "cannot wire node/SentenceCutSpeech rows to it"
        )

    r = _render_nodes(params, bundle, canvas_index=index, comp_uuid=comp_uuid, minter=minter)

    comp["details"] = json.dumps(r.details, ensure_ascii=False, separators=(",", ":"))
    comp["routes"] = json.dumps(r.routes, ensure_ascii=False, separators=(",", ":"))
    comp["inboundPorts"] = json.dumps(r.inbound_ports, ensure_ascii=False, separators=(",", ":"))
    comp["topFloorDetails"] = json.dumps(
        r.top_floor_details, ensure_ascii=False, separators=(",", ":")
    )

    set_components(bundle, comps)
    _append_sentence_cut_speech(bundle, r.sentence_cut_speech)


def _ports_of(node_obj: dict) -> dict:
    """Map branch name -> port uuid from a rendered node's canvas.ports.items."""
    items = (node_obj.get("canvas") or {}).get("ports", {}).get("items", []) or []
    return {it["name"]: it["id"] for it in items}


def append_node(bundle: InputBundle, params: dict, minter) -> None:
    """Merge ONE node (+optional edges) into an existing component without
    re-rendering or renaming existing nodes (their uuids are preserved).

    params:
        component: int — target BizSpeechComponent index
        node: {id, prompt, type?} — the new node (logical id is local to this call)
        edges: optional list of {from, branch, to}; endpoints are EITHER the new
               node's logical id OR an existing node uuid already in details.
    """
    comps = get_components(bundle)
    index = params["component"]
    comp = require_component(comps, index)
    comp_uuid = comp.get("componentUuid") or ""
    if not comp_uuid:
        raise ValueError(f"append-node: component {index} has no componentUuid")

    raw_details = comp.get("details")
    details = (
        json.loads(raw_details)
        if isinstance(raw_details, str) and raw_details not in ("null", "")
        else {}
    )
    if not isinstance(details, dict):
        details = {}
    raw_routes = comp.get("routes")
    routes = (
        json.loads(raw_routes)
        if isinstance(raw_routes, str) and raw_routes not in ("null", "")
        else {}
    )
    if not isinstance(routes, dict):
        routes = {}
    raw_inbound = comp.get("inboundPorts")
    inbound = (
        json.loads(raw_inbound)
        if isinstance(raw_inbound, str) and raw_inbound not in ("null", "")
        else []
    )
    if not isinstance(inbound, list):
        inbound = []
    raw_tfd = comp.get("topFloorDetails")
    top_floor = (
        json.loads(raw_tfd)
        if isinstance(raw_tfd, str) and raw_tfd not in ("null", "")
        else []
    )
    if not isinstance(top_floor, list):
        top_floor = []

    node = params["node"]
    new_edges = params.get("edges") or []
    node_type_str = node.get("type", "talk")

    # Parse BSC for target resolution and component_nav (needed regardless of node type).
    bsc_raw2 = bundle.data.get("BizSpeechComponent", "[]")
    bsc2 = json.loads(bsc_raw2) if isinstance(bsc_raw2, str) else bsc_raw2
    comp_uuid_by_name: dict[str, str] = {
        c.get("name", ""): c.get("componentUuid", "") for c in bsc2
    }
    comp_by_name: dict[str, dict] = {c.get("name", ""): c for c in bsc2}

    # Compute edge branches leaving the new node (for terminal validation).
    edge_branches_from_node = {e["branch"] for e in new_edges if e["from"] == node["id"]}

    cfg = dict(node.get("config") or {})

    if node_type_str == "goto":
        target_name = cfg.get("target", "")
        cfg["target_uuid"] = comp_uuid_by_name.get(target_name, "")
        cfg["target_name"] = target_name
        if not cfg["target_uuid"]:
            raise ValueError(
                f"append-node: goto node {node['id']!r}: config.target {target_name!r} "
                f"does not match any existing component name"
            )
    elif node_type_str == "goto_mr":
        target_name = cfg.get("target", "")
        if not target_name:
            raise ValueError(
                f"append-node: goto_mr node {node['id']!r} missing config.target"
            )
        cfg["target_uuid"] = comp_uuid_by_name.get(target_name, "")
        cfg["target_name"] = target_name
        if not cfg["target_uuid"]:
            raise ValueError(
                f"append-node: goto_mr node {node['id']!r}: config.target {target_name!r} "
                f"does not match any existing component name"
            )
        # Validate that the component being appended to is a multi-round (category:2) component
        container_comp_category = comp.get("category", 1)
        if container_comp_category != 2:
            raise ValueError(
                "append-node: goto_mr is only valid inside a multi-round (category:2) component"
            )
        # Validate that the target component is a multi-round (category:2) component
        target_comp = comp_by_name.get(target_name)
        if target_comp and target_comp.get("category") != 2:
            raise ValueError(
                f"append-node: goto_mr target {target_name!r} is not a multi-round "
                f"(category:2) component"
            )
    elif node_type_str == "talk_continue":
        # Validate that the component being appended to is a multi-round (category:2) component
        container_comp_category = comp.get("category", 1)
        if container_comp_category != 2:
            raise ValueError(
                "append-node: talk_continue is only valid inside a multi-round "
                "(category:2) component"
            )
        # Optional return target: if config.target is present, resolve and validate
        target_name = cfg.get("target", "")
        if target_name:
            cfg["target_uuid"] = comp_uuid_by_name.get(target_name, "")
            cfg["target_name"] = target_name
            if not cfg["target_uuid"]:
                raise ValueError(
                    f"append-node: talk_continue node {node['id']!r}: "
                    f"config.target {target_name!r} does not match any existing component name"
                )
            # Validate that the return target component is a main-flow (category != 2) component
            target_comp = comp_by_name.get(target_name)
            if target_comp and target_comp.get("category") == 2:
                raise ValueError(
                    f"append-node: talk_continue return target {target_name!r} must be a main-flow "
                    f"(non-multi-round) component"
                )
        else:
            # No return target: set defaults
            cfg["target_uuid"] = ""
            cfg["target_name"] = ""
    elif node_type_str == "goto_kb":
        target_name = cfg.get("target", "")
        if not target_name:
            raise ValueError(
                f"append-node: goto_kb node {node['id']!r} missing config.target"
            )
        biz_kb_raw = bundle.data.get("BizKnowledgeInfo", "[]")
        biz_kb = json.loads(biz_kb_raw) if isinstance(biz_kb_raw, str) else biz_kb_raw
        kb_title_to_id: dict[str, int] = {
            k["kdTitle"]: k["knowledgeId"] for k in biz_kb if k.get("kdTitle")
        }
        if target_name not in kb_title_to_id:
            raise ValueError(
                f"append-node: goto_kb target {target_name!r} not found in BizKnowledgeInfo"
            )
        cfg["target_kid"] = kb_title_to_id[target_name]
    elif node_type_str == "nested":
        target_name = cfg.get("target", "")
        cfg["target_uuid"] = comp_uuid_by_name.get(target_name, "")

    # For conditional nodes, strip `to` from branches before isolated rendering.
    # render_component_nodes synthesises edges from config.branches[].to, but in append_node
    # the targets are existing node uuids (not logical ids in this render batch), which would
    # cause a KeyError. We wire the routes ourselves after render (using orig_branches below).
    orig_branches = list(cfg.get("branches") or [])  # preserve `to` for post-render wiring
    if node_type_str == "conditional":
        stripped_branches = [{k: v for k, v in b.items() if k != "to"} for b in orig_branches]
        cfg = dict(cfg)  # shallow copy so original params are unaffected
        cfg["branches"] = stripped_branches

    # Validate special nodes BEFORE rendering.
    current_comp_name = comp.get("name")
    if node_type_str in (
        "talk", "conditional", "assign", "exit_port", "nested", "goto", "goto_kb", "goto_mr",
        "talk_continue"
    ):
        _si_raw = bundle.data.get("SpeechIntent", "[]")
        _si = json.loads(_si_raw) if isinstance(_si_raw, str) else _si_raw
        _intent_names = {i["intentName"] for i in _si if i.get("intentName")}
        _validate_special_node(
            node,
            _declared_var_names(bundle),
            {node["id"], *details.keys()},
            "append-node:",
            comp_by_name=comp_by_name,
            edge_branches_from_node=edge_branches_from_node or None,
            current_comp_name=current_comp_name,
            intent_names=_intent_names,
        )

    # Build nested_exit_map for nested nodes: {target-name: {exit-name: child-exit-uuid}}.
    nested_exit_map: dict[str, dict[str, str]] | None = None
    if node_type_str == "nested":
        target_name = cfg.get("target", "")
        child_comp = comp_by_name.get(target_name)
        if child_comp:
            child_exits = _exit_ports_from_comp(child_comp)
            if child_exits:
                nested_exit_map = {target_name: child_exits}

    # Render the new node ALONE. Namespace its logical id so minted uuids cannot
    # collide with any existing node minted under the same canvas_index.
    spec = NodeSpec(
        id=f"append:{node['id']}",
        prompt=node.get("prompt", ""),
        type=node_type_str,
        config=cfg,
    )
    speech_id, branch_intent_ids, kb_ids, node_language = _resolve_context(bundle)
    component_nav = _build_component_nav(bsc2)
    r = render_component_nodes(
        [spec], [], canvas_index=index, comp_uuid=comp_uuid,
        speech_id=speech_id, branch_intent_ids=branch_intent_ids,
        kb_ids=kb_ids, node_language=node_language, minter=minter,
        component_nav=component_nav,
        var_source_by_name=_var_source_map(bundle),
        nested_exit_map=nested_exit_map,
    )
    (new_uuid, new_obj), = r.details.items()

    # Resolve edge endpoints: new node by logical id, existing nodes by uuid.
    def resolve_uuid(ref: str) -> str:
        if ref == node["id"]:
            return new_uuid
        if ref in details:
            return ref
        raise ValueError(
            f"append-node: edge endpoint {ref!r} is neither the new node id "
            f"nor an existing node uuid"
        )

    # Determine whether the new node is an entry node (no incoming edge).
    has_incoming = any(resolve_uuid(e["to"]) == new_uuid for e in new_edges)
    new_obj["is_default"] = not has_incoming
    new_obj.setdefault("data", {})["is_default"] = not has_incoming

    details[new_uuid] = new_obj
    routes.setdefault(new_uuid, {})
    _NODE_NAME = {
        "talk": "Talk Node",
        "conditional": "Conditional Judgment Node",
        "assign": "Variable Assignment Node",
        "nested": "Nested Component Node",
    }
    _NODE_TYPE_INT = {
        "talk": 1, "exit": 2, "goto": 4, "exit_port": 4,
        "conditional": 7, "goto_kb": 8, "goto_mr": 9, "talk_continue": 5, "assign": 10,
        "nested": 11, "transfer": 13,
    }
    # Terminal nodes (exit, transfer, goto, goto_kb, goto_mr, talk_continue, exit_port)
    # are not added to inboundPorts.
    _TERMINAL = frozenset(
        {"exit", "transfer", "goto", "goto_kb", "goto_mr", "talk_continue", "exit_port"}
    )
    if not has_incoming and node_type_str not in _TERMINAL:
        inbound.append({
            "name": _NODE_NAME.get(node_type_str, "Talk Node"),
            "type": _NODE_TYPE_INT.get(node_type_str, 1),
            "uuid": new_uuid,
            "is_default": True,
        })

    # exit, goto, goto_kb, and exit_port contribute a topFloorDetails row
    # (mirrors render_component_nodes). goto_mr, transfer, and nested do NOT.
    if node_type_str in ("exit", "goto", "goto_kb", "exit_port"):
        top_floor.append(new_obj["data"])

    # Wire each edge onto its source node's branch port.
    for e in new_edges:
        src_uuid = resolve_uuid(e["from"])
        dst_uuid = resolve_uuid(e["to"])
        src_ports = _ports_of(details[src_uuid])
        if e["branch"] not in src_ports:
            raise ValueError(
                f"append-node: branch {e['branch']!r} has no port on source node {e['from']!r}"
            )
        src_port_uuid = src_ports[e["branch"]]
        edge_uuid = str(minter.uuid(f"append-edge:{index}:{e['from']}:{e['branch']}:{e['to']}"))
        routes.setdefault(src_uuid, {})[src_port_uuid] = {
            "source": {"type": 1, "uuid": src_port_uuid},
            "target": {"type": 1, "uuid": dst_uuid},
            "portDetail": {"id": edge_uuid, "zIndex": 3},
        }

    # Wire conditional node branch ports from config.branches[].to.
    # The type-7 builder bakes one port per distinct branch name into canvas.ports.items.
    # Port uuid == all_client_intent id == routes key. Targets are resolved via resolve_uuid.
    if node_type_str == "conditional":
        new_node_ports = _ports_of(details[new_uuid])  # branch-name → port-uuid
        seen_branches: dict[str, str] = {}  # distinct branch-name → first-seen `to`
        for b in orig_branches:
            bname = b.get("name")
            to = b.get("to")
            if bname and to and bname not in seen_branches:
                seen_branches[bname] = to
        for branch_name, to_ref in seen_branches.items():
            if branch_name not in new_node_ports:
                raise ValueError(
                    f"append-node: conditional branch {branch_name!r} has no port "
                    f"on node {node['id']!r}"
                )
            port_uuid = new_node_ports[branch_name]
            dst_uuid = resolve_uuid(to_ref)
            edge_uuid = str(
                minter.uuid(f"append-edge:{index}:{node['id']}:{branch_name}:{to_ref}")
            )
            routes.setdefault(new_uuid, {})[port_uuid] = {
                "source": {"type": 1, "uuid": port_uuid},
                "target": {"type": 1, "uuid": dst_uuid},
                "portDetail": {"id": edge_uuid, "zIndex": 3},
            }

    # Wire nested node out-ports from new_edges.
    # For a nested node, the serializer bakes one out-port per child exit port with
    # port.uuid == child-exit-node-uuid. routes[nested][child-exit-uuid] = edge_obj.
    # new_edges from the caller use the child's exit-port NAME as `branch`; we look up
    # the corresponding child-exit-uuid from nested_exit_map to use as the routes key.
    if node_type_str == "nested" and nested_exit_map:
        target_name = cfg.get("target", "")
        child_exits = (nested_exit_map or {}).get(target_name, {})  # {exit-name: child-exit-uuid}
        for e in new_edges:
            if e["from"] != node["id"]:
                continue
            exit_name = e["branch"]
            child_exit_uuid = child_exits.get(exit_name)
            if not child_exit_uuid:
                raise ValueError(
                    f"append-node: nested branch {exit_name!r} not found in child {target_name!r}"
                )
            dst_uuid = resolve_uuid(e["to"])
            edge_uuid = str(
                minter.uuid(f"append-edge:{index}:{node['id']}:{exit_name}:{e['to']}")
            )
            routes.setdefault(new_uuid, {})[child_exit_uuid] = {
                # FIX 2: nested (type-11) out-edges use source.type=3
                # (port-origin reference into the child component).
                "source": {"type": 3, "uuid": child_exit_uuid},
                "target": {"type": 1, "uuid": dst_uuid},
                "portDetail": {"id": edge_uuid, "zIndex": 3},
            }

    comp["details"] = json.dumps(details, ensure_ascii=False, separators=(",", ":"))
    comp["routes"] = json.dumps(routes, ensure_ascii=False, separators=(",", ":"))
    comp["inboundPorts"] = json.dumps(inbound, ensure_ascii=False, separators=(",", ":"))
    comp["topFloorDetails"] = json.dumps(top_floor, ensure_ascii=False, separators=(",", ":"))

    # I1: when a nested node is appended, wire the child component's parentUuid to the
    # current (parent) component's componentUuid, mirroring the builder's behaviour.
    # NOTE: comp_by_name was built from bsc2 (a separate parsed list), so we must locate
    # the child in `comps` (the list we will write back) rather than mutating comp_by_name.
    if node_type_str == "nested":
        target_name_i1 = (node.get("config") or {}).get("target", "")
        child_comp_i1 = comp_by_name.get(target_name_i1)
        if child_comp_i1 is not None:
            target_uuid_i1 = child_comp_i1.get("componentUuid", "")
            for c in comps:
                if c.get("componentUuid") == target_uuid_i1:
                    c["parentUuid"] = comp_uuid
                    break

    set_components(bundle, comps)
    _append_sentence_cut_speech(bundle, r.sentence_cut_speech)


def add_component(bundle: InputBundle, params: dict, minter) -> None:
    """Append a new BizSpeechComponent, cloning the first entry's shared keys.

    If params has a 'nodes' list (each {id, prompt}), the details/routes/inboundPorts
    are populated via render_component_nodes; otherwise details is the literal string
    "null" (empty-canvas convention).

    Optional params["edges"] list of {from, branch, to} wires node connections.
    Appends SentenceCutSpeech rows to bundle.data when nodes are provided.
    """
    comps = get_components(bundle)
    base = comps[0] if comps else {}
    index = len(comps)
    nodes = params.get("nodes")

    new_comp = dict(base)
    if index > 0:
        for key in _SECONDARY_STRIP_KEYS:
            new_comp.pop(key, None)
    new_comp["componentUuid"] = str(minter.uuid(f"modifier-component:{index}"))
    new_comp["name"] = params["name"]
    new_comp["id"] = minter.int_id(f"modifier-component-id:{index}")
    new_comp["parentUuid"] = "0"
    new_comp["sortIndex"] = index + 1

    if nodes:
        comp_uuid = new_comp["componentUuid"]
        # Temporarily append so _resolve_context can read speechId from comps[0]
        comps.append(new_comp)
        set_components(bundle, comps)

        r = _render_nodes(params, bundle, canvas_index=index, comp_uuid=comp_uuid, minter=minter)

        # Re-read after set_components mutated the bundle
        comps = get_components(bundle)
        new_comp = comps[-1]
        new_comp["details"] = json.dumps(r.details, ensure_ascii=False, separators=(",", ":"))
        new_comp["routes"] = json.dumps(r.routes, ensure_ascii=False, separators=(",", ":"))
        new_comp["inboundPorts"] = json.dumps(
            r.inbound_ports, ensure_ascii=False, separators=(",", ":")
        )
        new_comp["topFloorDetails"] = json.dumps(
            r.top_floor_details, ensure_ascii=False, separators=(",", ":")
        )
        set_components(bundle, comps)
        _append_sentence_cut_speech(bundle, r.sentence_cut_speech)
    else:
        new_comp["details"] = "null"
        comps.append(new_comp)
        set_components(bundle, comps)
