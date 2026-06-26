"""Mutation ops: rewire-edge, delete-edge, delete-node, rename-node."""

from __future__ import annotations

from wizmodifier import codec
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
