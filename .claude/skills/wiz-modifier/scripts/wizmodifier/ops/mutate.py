"""Mutation ops: rewire-edge, delete-edge, delete-node, rename-node."""

from __future__ import annotations

from wizmodifier import codec
from wizmodifier.floweditor import FlowEditError, FlowEditor
from wizmodifier.io import InputBundle
from wizmodifier.ops._bsc import get_components, require_component, set_components


def rewire_edge(bundle: InputBundle, params: dict, minter) -> None:  # noqa: ARG001
    """Set or replace an edge route for `branch` on a node.

    params:
        component    — BSC index (int)
        from         — {uuid: <uuid>} or {label: <name>} — the source node
        branch       — out-port name on the source node
        to           — {uuid: <uuid>} or {label: <name>} — the target node
                       (mutually exclusive with to_component)
        to_component — component name (str) — only valid when the source node is
                       a goto (type 4); resolves to componentUuid and calls
                       set_goto_target instead of set_edge_target

    If the source node is type 4 (goto) AND `to_component` is present:
        - resolves the named component from the BSC list
        - calls fe.set_goto_target(from_uuid, comp_uuid, comp_name)
    Otherwise:
        - resolves `to` via fe.resolve() (validates the target exists)
        - calls fe.set_edge_target(from_uuid, branch, to_uuid)

    Raises:
        ValueError      if `to_component` is given but no matching BSC entry found
        FlowEditError   if `from`/`to` ref is unresolvable or ambiguous, or branch
                        is not a declared port on the source node
    """
    comps = get_components(bundle)
    comp = require_component(comps, params["component"])
    fe = FlowEditor(comp)

    from_uuid = fe.resolve(params["from"])
    branch: str = params["branch"]

    if fe.node_type(from_uuid) == 4 and params.get("to_component"):
        # goto retarget: resolve component name → uuid from the BSC list
        target_name: str = params["to_component"]
        target_comp = next(
            (c for c in comps if c.get("name") == target_name and c.get("componentUuid")),
            None,
        )
        if target_comp is None:
            raise ValueError(
                f"rewire-edge: to_component {target_name!r} not found in BizSpeechComponent"
            )
        fe.set_goto_target(from_uuid, target_comp["componentUuid"], target_name)
    else:
        # Normal edge rewire: resolve the target node (validates existence)
        to_uuid = fe.resolve(params["to"])
        fe.set_edge_target(from_uuid, branch, to_uuid)

    fe.flush()
    set_components(bundle, comps)


def delete_edge(bundle: InputBundle, params: dict, minter) -> None:  # noqa: ARG001
    """Remove the route for `branch` on a node; the out-port is left intact.

    params:
        component — BSC index (int)
        from      — {uuid: <uuid>} or {label: <name>}
        branch    — out-port name whose route to remove

    Raises:
        FlowEditError   if `from` ref is unresolvable or ambiguous, or branch is
                        not a declared port on the source node
    """
    comps = get_components(bundle)
    comp = require_component(comps, params["component"])
    fe = FlowEditor(comp)

    from_uuid = fe.resolve(params["from"])
    fe.remove_edge(from_uuid, params["branch"])

    fe.flush()
    set_components(bundle, comps)


def delete_node(bundle: InputBundle, params: dict, minter) -> dict:  # noqa: ARG001
    """Remove a node and cascade-clean all related tables.

    params:
        component — BSC index (int)
        node      — {uuid: <uuid>} or {label: <name>}

    Decodes SentenceCutSpeech / SentenceCutKnowledge from the export-level
    bundle.data, delegates to FlowEditor.remove_node() which mutates those lists
    in-place, then writes the updated lists back via codec.encode().

    Returns the summary dict from remove_node:
        {
            "unwired_inbound": [(src_uuid, branch), ...],
            "orphaned":        [uuid, ...],
            "removed_rows":    <int>,
        }

    Raises:
        FlowEditError   if the node ref is unresolvable or ambiguous
    """
    comps = get_components(bundle)
    comp = require_component(comps, params["component"])
    fe = FlowEditor(comp)

    uuid = fe.resolve(params["node"])

    scs: list[dict] = codec.decode(bundle.data.get("SentenceCutSpeech", "[]"))
    sck: list[dict] = codec.decode(bundle.data.get("SentenceCutKnowledge", "[]"))

    summary = fe.remove_node(uuid, scs, sck)

    bundle.data["SentenceCutSpeech"] = codec.encode(scs)
    bundle.data["SentenceCutKnowledge"] = codec.encode(sck)
    fe.flush()
    set_components(bundle, comps)

    return summary


def move_node(bundle: InputBundle, params: dict, minter) -> dict:  # noqa: ARG001
    """Move a node from one component to another.

    params:
        node           — {uuid: <uuid>} or {label: <name>} — the node to move
        to_component   — component name (str) — the destination component
        from_component — (optional int) index of the source component; if omitted,
                         the source is auto-detected by scanning all components for
                         the one containing the node.

    Steps:
    1. Resolve source component (explicit index or scan).
    2. Resolve destination component by name; reject same-component move.
    3. Capture inbound and outbound edges before extraction for reporting.
    4. extract_node from src (unwires inbound, carries SCS/SCK rows deep-copied).
    5. insert_node into dst (rewriting componentUuid on carried rows).
    6. Drop any outbound routes in dst that point at nodes not in dst's details
       (cross-boundary danglers); report them in dropped_cross_edges.
    7. Flush both editors, write scs/sck back, set_components.

    Returns:
        {
            "moved":               <node uuid>,
            "dropped_cross_edges": [(branch, target_uuid), ...],
            "unwired_inbound":     [(src_uuid, branch), ...],
        }

    Raises:
        ValueError      if to_component is not found, or src == dst
        FlowEditError   if the node ref is unresolvable or ambiguous
    """
    comps = get_components(bundle)

    # --- Step 1: resolve source component ---
    explicit_from = params.get("from_component")
    if explicit_from is not None:
        src_comp = comps[int(explicit_from)]
        fe_src = FlowEditor(src_comp)
        uuid = fe_src.resolve(params["node"])
    else:
        # Scan all components for the one that resolves the node ref.
        fe_src = None
        uuid = None
        src_comp = None
        for comp in comps:
            fe_candidate = FlowEditor(comp)
            try:
                resolved = fe_candidate.resolve(params["node"])
            except (FlowEditError, KeyError, ValueError):
                continue
            fe_src = fe_candidate
            uuid = resolved
            src_comp = comp
            break
        if fe_src is None or uuid is None:
            ref = params["node"]
            raise FlowEditError(f"move-node: could not find node {ref!r} in any component")

    # --- Step 2: resolve dest component by name; reject same-component ---
    to_name: str = params["to_component"]
    dst_comp = next(
        (c for c in comps if c.get("name") == to_name and c.get("componentUuid")),
        None,
    )
    if dst_comp is None:
        raise ValueError(
            f"move-node: to_component {to_name!r} not found in BizSpeechComponent"
        )
    if src_comp.get("componentUuid") == dst_comp.get("componentUuid"):
        raise ValueError(
            "move-node: source and destination component are the same"
        )
    fe_dst = FlowEditor(dst_comp)

    # --- Step 3: capture inbound/outbound before extraction ---
    # Inbound edges (in src) targeting the node — extract_node unwires these.
    unwired_inbound: list[tuple[str, str]] = [
        (src_uuid, branch) for (src_uuid, branch, _t) in fe_src.in_edges(uuid)
    ]

    # --- Step 4: decode export-level SCS/SCK, then extract ---
    scs: list[dict] = codec.decode(bundle.data.get("SentenceCutSpeech", "[]"))
    sck: list[dict] = codec.decode(bundle.data.get("SentenceCutKnowledge", "[]"))

    payload = fe_src.extract_node(uuid, scs, sck)

    # --- Step 4b: remove src-component rows for the moved node ---
    # extract_node deep-copies the rows into the payload but leaves the originals
    # in scs/sck.  Prune them now so insert_node's rewritten copies are the only
    # ones that remain (prevents duplicate audio rows in the final export).
    src_comp_uuid = src_comp.get("componentUuid", "")
    scs[:] = [
        r for r in scs
        if not (r.get("componentUuid") == src_comp_uuid and r.get("id") == uuid)
    ]
    sck[:] = [
        r for r in sck
        if not (r.get("componentUuid") == src_comp_uuid and r.get("id") == uuid)
    ]

    # --- Step 5: insert into dest (rewriting componentUuid on SCS/SCK rows) ---
    fe_dst.insert_node(payload, scs, sck)

    # --- Step 6: drop cross-boundary outbound edges in dst ---
    # After insert, fe_dst.routes[uuid] may have routes to nodes not in fe_dst.details.
    dropped_cross_edges: list[tuple[str, str]] = []
    node_routes_in_dst = fe_dst.routes.get(uuid, {})
    # Build inverse port-id → branch-name map for the moved node in dst.
    # _ports reads from fe_dst.details (node was just inserted there).
    ports_inv = {pid: branch for branch, pid in fe_dst._ports(uuid).items()}
    for port_id, edge in list(node_routes_in_dst.items()):
        target_uuid = (edge.get("target") or {}).get("uuid")
        if target_uuid and target_uuid not in fe_dst.details:
            branch = ports_inv.get(port_id, port_id)
            dropped_cross_edges.append((branch, target_uuid))
            del node_routes_in_dst[port_id]
    # Rebuild inbound in dst after potential route removal.
    fe_dst._rebuild_inbound()

    # --- Step 7: write back ---
    bundle.data["SentenceCutSpeech"] = codec.encode(scs)
    bundle.data["SentenceCutKnowledge"] = codec.encode(sck)
    fe_src.flush()
    fe_dst.flush()
    set_components(bundle, comps)

    return {
        "moved": uuid,
        "dropped_cross_edges": dropped_cross_edges,
        "unwired_inbound": unwired_inbound,
    }


def complete_component(bundle: InputBundle, params: dict, minter) -> dict:
    """Auto-complete a component to the M4 completeness rules.

    Ensures:
    - The component has at least one Exit node (type 2).
    - Every talk node (type 1) has an Unclassified out-port.
    - Every unconnected out-branch is wired to the Exit node.

    params:
        component    — BSC index (int)
        exit_target  — (optional) {uuid: <uuid>} or {label: <name>} — reuse an
                       existing node as the exit target instead of creating one.

    Returns:
        {
            "added_exit":        bool   — True if a new Exit node was minted,
            "wired_branches":    int    — number of branches wired to the exit,
            "added_unclassified": int   — number of Unclassified ports added,
        }

    Idempotent: running on an already-complete component returns all-zero counts.

    Raises:
        FlowEditError  if exit_target ref is unresolvable or ambiguous.
    """
    comps = get_components(bundle)
    comp = require_component(comps, params["component"])
    fe = FlowEditor(comp)

    # --- Step 1: determine / create the exit node ---
    added_exit = False
    exit_target = params.get("exit_target")

    if exit_target is not None:
        # Caller supplied an explicit target node to use as the exit.
        exit_uuid = fe.resolve(exit_target)
    elif fe.has_exit():
        # Reuse the existing exit node.
        exit_uuid = next(u for u, n in fe.details.items() if n.get("type") == 2)
    else:
        # Mint a new Exit node and append its SCS row to the export.
        exit_uuid, scs_row = fe.add_exit_node(minter)
        added_exit = True
        scs: list[dict] = codec.decode(bundle.data.get("SentenceCutSpeech", "[]"))
        scs.append(scs_row)
        bundle.data["SentenceCutSpeech"] = codec.encode(scs)

    # --- Step 2: ensure every talk node has an Unclassified out-port ---
    # Do this BEFORE calling unconnected_branches() so newly-added ports are included.
    added_unclassified = 0
    for uuid, node in fe.details.items():
        if node.get("type") == 1 and fe.ensure_unclassified(uuid):
            added_unclassified += 1

    # --- Step 3: wire every unconnected branch to the exit node ---
    # SKIP nested (type-11) nodes: their out-ports mirror the child canvas's exit_port
    # nodes and are routed by child-exit-uuid, NOT by the parent canvas's port ids. The
    # nested node's canvas.ports.items use display ids that differ from its routes keys,
    # so unconnected_branches() mis-reports those ports as unwired — wiring them fabricates
    # bogus routes keyed by non-routing port ids that break WIZ import (malformed `routes`).
    wired = 0
    for node_uuid, branch in fe.unconnected_branches():
        if fe.node_type(node_uuid) == 11:
            continue
        fe.set_edge_target(node_uuid, branch, exit_uuid)
        wired += 1

    # --- Step 4: flush and persist ---
    fe.flush()
    set_components(bundle, comps)

    return {
        "added_exit": added_exit,
        "wired_branches": wired,
        "added_unclassified": added_unclassified,
    }


def rename_node(bundle: InputBundle, params: dict, minter) -> None:  # noqa: ARG001
    """Set a new label and/or prompt text on a node.

    params:
        component — BSC index (int)
        node      — {uuid: <uuid>} or {label: <name>}
        label     — (optional str) new human-readable label (data.name)
        prompt    — (optional str) new spoken-text prompt (dialog_list + SCS)

    At least one of `label` or `prompt` must be supplied.

    When `prompt` is given, decodes SentenceCutSpeech from bundle.data, calls
    fe.set_prompt() (which mutates the list in-place), and writes it back.

    Raises:
        ValueError      if neither `label` nor `prompt` is present
        FlowEditError   if the node ref is unresolvable or ambiguous
    """
    label: str | None = params.get("label")
    prompt: str | None = params.get("prompt")
    if label is None and prompt is None:
        raise ValueError("rename-node requires 'label' or 'prompt' (or both)")

    comps = get_components(bundle)
    comp = require_component(comps, params["component"])
    fe = FlowEditor(comp)

    uuid = fe.resolve(params["node"])

    if label is not None:
        fe.set_label(uuid, label)

    if prompt is not None:
        scs: list[dict] = codec.decode(bundle.data.get("SentenceCutSpeech", "[]"))
        fe.set_prompt(uuid, prompt, scs)
        bundle.data["SentenceCutSpeech"] = codec.encode(scs)

    fe.flush()
    set_components(bundle, comps)


def set_node_config(bundle: InputBundle, params: dict, minter) -> None:  # noqa: ARG001
    """Retarget / reconfigure an existing node in place (uuid + ports preserved).

    Dispatch by node type:
      4  goto        -> params['to_component'] (name)  -> set_goto_target
      8  goto_kb     -> params['kb'] (name)            -> set_goto_kb_target
      9  goto_mr     -> params['to_component'] (name)  -> set_goto_mr_target
      10 assign      -> params['variable'] and/or ['value']
      7  conditional -> params['variable'] and/or ['branches'] (updates by name)
    """
    from wizmodifier import codec
    from wizmodifier.ops.structure import _var_source_map

    comps = get_components(bundle)
    comp = require_component(comps, params["component"])
    fe = FlowEditor(comp)
    uuid = fe.resolve(params["node"])
    t = fe.node_type(uuid)

    if t == 4:
        name = params["to_component"]
        tgt = next((c for c in comps if c.get("name") == name and c.get("componentUuid")), None)
        if tgt is None:
            raise ValueError(f"set-node-config: to_component {name!r} not found")
        fe.set_goto_target(uuid, tgt["componentUuid"], name)
    elif t == 8:
        name = params["kb"]
        kbs = codec.decode(bundle.data.get("BizKnowledgeInfo", "[]"))
        kb = next((k for k in kbs if k.get("kdTitle") == name), None)
        if kb is None:
            raise ValueError(f"set-node-config: KB {name!r} not found in BizKnowledgeInfo")
        fe.set_goto_kb_target(uuid, kb.get("knowledgeId"))
    elif t == 9:
        name = params["to_component"]
        tgt = next((c for c in comps if c.get("name") == name and c.get("componentUuid")), None)
        if tgt is None:
            raise ValueError(f"set-node-config: to_component {name!r} not found")
        if str(tgt.get("category", 1)) != "2":
            bundle.warnings.append(
                f"set-node-config: goto_mr target {name!r} is not a multi-round (category:2) component")
        fe.set_goto_mr_target(uuid, tgt["componentUuid"], name)
    elif t == 10:
        var = params.get("variable")
        src = _var_source_map(bundle).get(var, 0) if var is not None else 0
        fe.set_assign(uuid, variable=var, value=params.get("value"), src=src)
    elif t == 7:
        var = params.get("variable")
        src = _var_source_map(bundle).get(var, 0) if var is not None else 0
        fe.set_conditional(uuid, variable=var, branch_updates=params.get("branches"), src=src)
    else:
        raise ValueError(f"set-node-config does not support node type {t}")

    fe.flush()
    set_components(bundle, comps)
