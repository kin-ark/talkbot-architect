"""Mutation ops: rewire-edge (incl. goto retarget) and delete-edge."""

from __future__ import annotations

from wizmodifier.floweditor import FlowEditor
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
