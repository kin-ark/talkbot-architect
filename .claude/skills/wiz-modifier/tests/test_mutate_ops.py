"""Tests for rewire-edge and delete-edge ops (Task 5 — FM-T5)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# wiz-builder's scripts dir is a sibling skill, not on pythonpath.
sys.path.insert(
    0, str(Path(__file__).resolve().parents[2] / "wiz-builder" / "scripts")
)

from wizbuilder.compile import compile_manifest  # noqa: E402
from wizbuilder.ids import IdMinter  # noqa: E402
from wizmodifier.floweditor import FlowEditError, FlowEditor  # noqa: E402
from wizmodifier.io import InputBundle  # noqa: E402
from wizmodifier.ops import mutate  # noqa: E402
from wizmodifier.ops._bsc import get_components  # noqa: E402

FIXTURES = Path(__file__).resolve().parents[2] / "wiz-builder" / "tests" / "fixtures"
MINTER = IdMinter(manifest_hash="deadbeef")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build(tmp_path: Path, manifest_name: str) -> dict:
    """Compile a builder fixture manifest → parsed export dict."""
    out = tmp_path / "speech.json"
    compile_manifest(FIXTURES / manifest_name, out)
    return json.loads(out.read_text(encoding="utf-8"))


def _bundle(doc: dict) -> InputBundle:
    return InputBundle(data=dict(doc), speech_name="s.json")


def _uw(v):
    return json.loads(v) if isinstance(v, str) else v


def _comp_fe(bundle: InputBundle, index: int = 0) -> tuple[dict, FlowEditor]:
    """Return (comp_dict, FlowEditor) for component at index (re-decoded from bundle)."""
    comp = get_components(bundle)[index]
    return comp, FlowEditor(comp)


# ---------------------------------------------------------------------------
# Test 1: rewire-edge repoints a talk branch to another existing node
# ---------------------------------------------------------------------------


def test_rewire_edge_talk_branch(tmp_path):
    """rewire-edge: repoint an existing talk branch to a different node via uuid ref."""
    doc = _build(tmp_path, "manifest_conditional_assign.yaml")
    bundle = _bundle(doc)

    comp, fe = _comp_fe(bundle)
    details = _uw(comp["details"])

    # The manifest wires: greet(Positive) → check_status.
    # Find the first talk node (type=1) that has a wired Positive branch.
    talk_nodes = [u for u, n in details.items() if n.get("type") == 1]
    assert talk_nodes, "Expected at least one talk node"

    # Find the talk node with a Positive out-edge (the "greet" node)
    greet_uuid = None
    for uuid in talk_nodes:
        branches = {b for b, _ in fe.out_edges(uuid)}
        if "Positive" in branches:
            greet_uuid = uuid
            break
    assert greet_uuid is not None, "Expected a talk node with a wired Positive branch"

    # Find a different target: the exit node (type=2)
    exit_uuid = next(u for u, n in details.items() if n.get("type") == 2)

    # Record current Positive target (should be check_status, not exit)
    original_target = dict(fe.out_edges(greet_uuid))["Positive"]
    assert original_target != exit_uuid

    # Rewire Positive → exit
    mutate.rewire_edge(bundle, {
        "component": 0,
        "from": {"uuid": greet_uuid},
        "branch": "Positive",
        "to": {"uuid": exit_uuid},
    }, MINTER)

    # Re-decode from bundle (flush must have written back)
    comp2, fe2 = _comp_fe(bundle)
    edges_after = dict(fe2.out_edges(greet_uuid))
    assert edges_after["Positive"] == exit_uuid


# ---------------------------------------------------------------------------
# Test 2: rewire-edge on a goto node with to_component
# ---------------------------------------------------------------------------


def test_rewire_edge_goto_to_component(tmp_path):
    """rewire-edge with to_component on a goto node updates appoint_node_id."""
    doc = _build(tmp_path, "manifest_goto.yaml")
    bundle = _bundle(doc)

    # Component 0 = "1. A Canvas"; component 1 = "2. B Canvas"
    comps = get_components(bundle)
    assert len(comps) >= 2

    # Find the goto node (type=4) in comp 0 with a non-empty appoint_node_id
    comp0 = comps[0]
    details0 = _uw(comp0["details"])
    goto_uuid = next(
        u for u, n in details0.items()
        if n.get("type") == 4 and (n.get("data") or {}).get("appoint_node_id")
    )

    target_comp = comps[1]
    target_uuid = target_comp["componentUuid"]
    target_name = target_comp["name"]

    mutate.rewire_edge(bundle, {
        "component": 0,
        "from": {"uuid": goto_uuid},
        "branch": "Default",
        "to_component": target_name,
    }, MINTER)

    # Re-read and confirm appoint_node_id on the goto node
    comp0_after = get_components(bundle)[0]
    details_after = _uw(comp0_after["details"])
    goto_node = details_after[goto_uuid]
    assert goto_node["data"]["appoint_node_id"] == target_uuid
    assert goto_node["data"]["specificComponentName"] == target_name


def test_rewire_edge_goto_unknown_component_raises(tmp_path):
    """rewire-edge: unknown to_component raises ValueError."""
    doc = _build(tmp_path, "manifest_goto.yaml")
    bundle = _bundle(doc)

    comp0 = get_components(bundle)[0]
    details0 = _uw(comp0["details"])
    goto_uuid = next(
        u for u, n in details0.items()
        if n.get("type") == 4 and (n.get("data") or {}).get("appoint_node_id")
    )

    with pytest.raises(ValueError, match="NoSuchCanvas|not found"):
        mutate.rewire_edge(bundle, {
            "component": 0,
            "from": {"uuid": goto_uuid},
            "branch": "Default",
            "to_component": "NoSuchCanvas",
        }, MINTER)


# ---------------------------------------------------------------------------
# Test 3: rewire-edge unknown to node ref raises; ambiguous label raises
# ---------------------------------------------------------------------------


def test_rewire_edge_unknown_to_raises(tmp_path):
    """rewire-edge: unknown to uuid raises FlowEditError."""
    doc = _build(tmp_path, "manifest_conditional_assign.yaml")
    bundle = _bundle(doc)

    comp, fe = _comp_fe(bundle)
    details = _uw(comp["details"])
    talk_uuid = next(u for u, n in details.items() if n.get("type") == 1)

    with pytest.raises((FlowEditError, ValueError)):
        mutate.rewire_edge(bundle, {
            "component": 0,
            "from": {"uuid": talk_uuid},
            "branch": "Positive",
            "to": {"uuid": "00000000-0000-0000-0000-000000000000"},
        }, MINTER)


def test_rewire_edge_ambiguous_label_raises(tmp_path):
    """rewire-edge: ambiguous from-label raises FlowEditError."""
    doc = _build(tmp_path, "manifest_conditional_assign.yaml")
    # Patch: give two talk nodes the same label to create ambiguity
    comps = _uw(doc["BizSpeechComponent"])
    details = _uw(comps[0]["details"])

    # Find the two talk nodes (type=1) and give both the same unique label
    talk_uuids = [u for u, n in details.items() if n.get("type") == 1]
    assert len(talk_uuids) >= 2, "Need at least two talk nodes to test ambiguity"
    for uuid in talk_uuids:
        details[uuid]["data"]["name"] = "SameName"  # create collision

    comps[0]["details"] = json.dumps(details)
    doc["BizSpeechComponent"] = json.dumps(comps)
    bundle = _bundle(doc)

    with pytest.raises(FlowEditError, match="ambiguous"):
        mutate.rewire_edge(bundle, {
            "component": 0,
            "from": {"label": "SameName"},  # ambiguous
            "branch": "Positive",
            "to": {"label": "SameName"},
        }, MINTER)


# ---------------------------------------------------------------------------
# Test 4: delete-edge drops the route, out-port still exists
# ---------------------------------------------------------------------------


def test_delete_edge_drops_route(tmp_path):
    """delete-edge: branch route is removed; out-port stays in canvas.ports."""
    doc = _build(tmp_path, "manifest_conditional_assign.yaml")
    bundle = _bundle(doc)

    comp, fe = _comp_fe(bundle)
    details = _uw(comp["details"])

    # Find the first talk node with a wired Positive branch (the "greet" node)
    greet_uuid = None
    for uuid, node in details.items():
        if node.get("type") == 1:
            branches = {b for b, _ in fe.out_edges(uuid)}
            if "Positive" in branches:
                greet_uuid = uuid
                break
    assert greet_uuid is not None, "Expected a talk node with a wired Positive branch"

    mutate.delete_edge(bundle, {
        "component": 0,
        "from": {"uuid": greet_uuid},
        "branch": "Positive",
    }, MINTER)

    # Re-decode
    comp2, fe2 = _comp_fe(bundle)
    # Branch no longer in out_edges (no route)
    edges_after = dict(fe2.out_edges(greet_uuid))
    assert "Positive" not in edges_after

    # But the port must still exist in canvas.ports.items
    details2 = _uw(comp2["details"])
    node2 = details2[greet_uuid]
    port_names = {
        it["name"]
        for it in (node2.get("canvas") or {}).get("ports", {}).get("items", [])
    }
    assert "Positive" in port_names


# ---------------------------------------------------------------------------
# Test 5: delete-edge / rewire-edge unknown branch raises
# ---------------------------------------------------------------------------


def test_delete_edge_unknown_branch_raises(tmp_path):
    """delete-edge: unknown branch on from-node raises FlowEditError."""
    doc = _build(tmp_path, "manifest_conditional_assign.yaml")
    bundle = _bundle(doc)

    comp, _ = _comp_fe(bundle)
    details = _uw(comp["details"])
    talk_uuid = next(u for u, n in details.items() if n.get("type") == 1)

    with pytest.raises((FlowEditError, ValueError)):
        mutate.delete_edge(bundle, {
            "component": 0,
            "from": {"uuid": talk_uuid},
            "branch": "NoSuchBranch",
        }, MINTER)


def test_rewire_edge_unknown_branch_raises(tmp_path):
    """rewire-edge: unknown branch on from-node raises FlowEditError."""
    doc = _build(tmp_path, "manifest_conditional_assign.yaml")
    bundle = _bundle(doc)

    comp, _ = _comp_fe(bundle)
    details = _uw(comp["details"])
    talk_uuid = next(u for u, n in details.items() if n.get("type") == 1)
    exit_uuid = next(u for u, n in details.items() if n.get("type") == 2)

    with pytest.raises((FlowEditError, ValueError)):
        mutate.rewire_edge(bundle, {
            "component": 0,
            "from": {"uuid": talk_uuid},
            "branch": "NoSuchBranch",
            "to": {"uuid": exit_uuid},
        }, MINTER)


# ---------------------------------------------------------------------------
# Task 6: delete-node tests
# ---------------------------------------------------------------------------


def test_delete_node_removes_from_flow(tmp_path):
    """delete-node: removes node from details/routes; inbound re-wires are cleared;
    SentenceCutSpeech row count drops for the deleted node's rows."""
    doc = _build(tmp_path, "manifest_conditional_assign.yaml")
    bundle = _bundle(doc)

    comp, fe = _comp_fe(bundle)
    details = _uw(comp["details"])

    # Find the conditional node (type=7) and its "Default" branch target.
    # The Default branch points at the second talk node ("greet_unpaid").
    conditional_uuid = next(u for u, n in details.items() if n.get("type") == 7)
    # The Default branch target: scan fe routes for the conditional node
    default_target = None
    for branch, tgt in fe.out_edges(conditional_uuid):
        if branch == "Default":
            default_target = tgt
            break
    assert default_target is not None, "Expected a Default branch on conditional node"

    # Confirm the target is a talk node with an SCS row
    assert details[default_target].get("type") == 1

    # Count SCS rows before
    scs_before = json.loads(doc.get("SentenceCutSpeech", "[]"))
    comp_uuid = comp["componentUuid"]
    scs_node_before = [
        r for r in scs_before
        if r.get("componentUuid") == comp_uuid and r.get("id") == default_target
    ]
    assert scs_node_before, "Expected at least one SCS row for target node before delete"

    mutate.delete_node(bundle, {
        "component": 0,
        "node": {"uuid": default_target},
    }, MINTER)

    # Re-parse details from bundle
    comp2, fe2 = _comp_fe(bundle)
    details2 = _uw(comp2["details"])

    # Node must be gone from details
    assert default_target not in details2

    # Node must be gone from routes
    routes2 = json.loads(comp2["routes"])
    assert default_target not in routes2

    # No route in any other node should still target the deleted node
    for port_map in routes2.values():
        if not isinstance(port_map, dict):
            continue
        for edge in port_map.values():
            target_uuid = (edge.get("target") or {}).get("uuid")
            assert target_uuid != default_target, (
                "Expected no remaining route targeting deleted node"
            )

    # SCS rows for this node must be gone from bundle
    scs_after = json.loads(bundle.data.get("SentenceCutSpeech", "[]"))
    scs_node_after = [
        r for r in scs_after
        if r.get("componentUuid") == comp_uuid and r.get("id") == default_target
    ]
    assert len(scs_node_after) == 0, "Expected SCS rows removed after delete-node"
    assert len(scs_after) < len(scs_before), "Expected total SCS count to drop"


def test_delete_node_unknown_raises(tmp_path):
    """delete-node: unknown node ref raises FlowEditError."""
    doc = _build(tmp_path, "manifest_conditional_assign.yaml")
    bundle = _bundle(doc)

    with pytest.raises((FlowEditError, ValueError)):
        mutate.delete_node(bundle, {
            "component": 0,
            "node": {"uuid": "00000000-0000-0000-0000-000000000000"},
        }, MINTER)


# ---------------------------------------------------------------------------
# Task 6: rename-node tests
# ---------------------------------------------------------------------------


def test_rename_node_label_changes_data_name(tmp_path):
    """rename-node with label: data.name is updated in the re-parsed export."""
    doc = _build(tmp_path, "manifest_conditional_assign.yaml")
    bundle = _bundle(doc)

    comp, fe = _comp_fe(bundle)
    details = _uw(comp["details"])

    # Target: the first talk node (type=1) — it has a wired Positive branch
    talk_uuid = next(u for u, n in details.items() if n.get("type") == 1)

    mutate.rename_node(bundle, {
        "component": 0,
        "node": {"uuid": talk_uuid},
        "label": "renamed_talk_node",
    }, MINTER)

    comp2, _ = _comp_fe(bundle)
    details2 = _uw(comp2["details"])
    assert details2[talk_uuid]["data"]["name"] == "renamed_talk_node"


def test_rename_node_prompt_updates_dialog_and_scs(tmp_path):
    """rename-node with prompt: editorValue text + SCS sentenceText updated."""
    doc = _build(tmp_path, "manifest_conditional_assign.yaml")
    bundle = _bundle(doc)

    comp, _ = _comp_fe(bundle)
    details = _uw(comp["details"])

    # Target: the first talk node (type=1) which has an SCS row
    talk_uuid = next(u for u, n in details.items() if n.get("type") == 1)
    comp_uuid = comp["componentUuid"]

    # Confirm it has an SCS row before rename
    scs_before = json.loads(doc.get("SentenceCutSpeech", "[]"))
    scs_talk = [
        r for r in scs_before
        if r.get("componentUuid") == comp_uuid and r.get("id") == talk_uuid
    ]
    assert scs_talk, "Expected SCS row for talk node before rename"

    new_prompt = "Updated greeting text for rename test"
    mutate.rename_node(bundle, {
        "component": 0,
        "node": {"uuid": talk_uuid},
        "prompt": new_prompt,
    }, MINTER)

    # Check details — dialog_list text
    comp2, _ = _comp_fe(bundle)
    details2 = _uw(comp2["details"])
    node2 = details2[talk_uuid]
    dialog_list = (node2.get("data") or {}).get("dialog_list", [])
    assert dialog_list, "Expected dialog_list to be present after rename"
    assert dialog_list[0]["text"] == new_prompt

    # Check SCS row
    scs_after = json.loads(bundle.data.get("SentenceCutSpeech", "[]"))
    scs_rows = [
        r for r in scs_after
        if r.get("componentUuid") == comp_uuid and r.get("id") == talk_uuid
    ]
    assert scs_rows, "Expected SCS row to exist after rename"
    assert scs_rows[0]["sentenceText"] == new_prompt


def test_rename_node_neither_raises(tmp_path):
    """rename-node with neither label nor prompt raises ValueError."""
    doc = _build(tmp_path, "manifest_conditional_assign.yaml")
    bundle = _bundle(doc)

    comp, _ = _comp_fe(bundle)
    details = _uw(comp["details"])
    talk_uuid = next(u for u, n in details.items() if n.get("type") == 1)

    with pytest.raises(ValueError, match="label.*prompt|prompt.*label"):
        mutate.rename_node(bundle, {
            "component": 0,
            "node": {"uuid": talk_uuid},
        }, MINTER)


# ---------------------------------------------------------------------------
# Task 7: move-node tests (cross-component re-parent)
# ---------------------------------------------------------------------------


def _build_multi(tmp_path: Path) -> dict:
    """Compile manifest_multi_canvas.yaml → parsed export dict."""
    return _build(tmp_path, "manifest_multi_canvas.yaml")


def test_move_node_leaves_src_enters_dst(tmp_path):
    """move-node: node uuid GONE from source component details, PRESENT in dest."""
    doc = _build_multi(tmp_path)
    bundle = _bundle(doc)

    comps = get_components(bundle)
    assert len(comps) >= 2, "Expected at least 2 components from manifest_multi_canvas"

    # Use the first (non-entry) talk node of comp 0, which has an outbound edge
    # to the second talk node (which stays in comp 0). This gives us a
    # cross-boundary outbound edge to check.
    fe0 = FlowEditor(comps[0])
    # Find the node in comp 0 that has outbound edges (i.e. greet-root node)
    node_to_move = next(
        u for u in fe0.details if fe0.out_edges(u)
    )

    dst_name = comps[1]["name"]

    result = mutate.move_node(bundle, {
        "node": {"uuid": node_to_move},
        "to_component": dst_name,
    }, MINTER)

    assert result["moved"] == node_to_move

    # Re-parse from bundle
    comps_after = get_components(bundle)
    details_a = _uw(comps_after[0]["details"])
    details_b = _uw(comps_after[1]["details"])

    assert node_to_move not in details_a, "Moved node must be removed from source comp"
    assert node_to_move in details_b, "Moved node must be present in dest comp"


def test_move_node_inbound_unwired(tmp_path):
    """move-node: an A-internal edge that targeted the moved node is cleared;
    it is reported in unwired_inbound."""
    doc = _build_multi(tmp_path)
    bundle = _bundle(doc)

    comps = get_components(bundle)
    fe0 = FlowEditor(comps[0])

    # greet-pitch node is the TARGET of greet-root's Unclassified edge.
    # Move greet-pitch → comp 1 and check that the edge from greet-root is cleared.
    node_to_move = next(
        u for u in fe0.details if not fe0.out_edges(u)
    )

    # Find which node points to it (should be greet-root)
    inbound_before = fe0.in_edges(node_to_move)
    assert inbound_before, "Expected at least one inbound edge to greet-pitch before move"

    dst_name = comps[1]["name"]
    result = mutate.move_node(bundle, {
        "node": {"uuid": node_to_move},
        "to_component": dst_name,
    }, MINTER)

    # unwired_inbound should report the cleared inbound edge(s)
    assert len(result["unwired_inbound"]) >= 1, (
        "Expected at least one entry in unwired_inbound"
    )

    # Verify the route is actually gone from comp 0
    comps_after = get_components(bundle)
    routes0 = _uw(comps_after[0]["routes"])
    for port_map in routes0.values():
        if not isinstance(port_map, dict):
            continue
        for edge in port_map.values():
            tgt = (edge.get("target") or {}).get("uuid")
            assert tgt != node_to_move, (
                "No route in comp 0 should still target the moved node"
            )


def test_move_node_cross_outbound_dropped(tmp_path):
    """move-node: outbound edge from moved node to a node staying in src is dropped
    and reported in dropped_cross_edges."""
    doc = _build_multi(tmp_path)
    bundle = _bundle(doc)

    comps = get_components(bundle)
    fe0 = FlowEditor(comps[0])

    # Move the node that HAS an outbound edge (greet-root → greet-pitch).
    # After moving greet-root to comp 1, its edge to greet-pitch (staying in comp 0)
    # is cross-boundary and must be dropped + reported.
    node_to_move = next(u for u in fe0.details if fe0.out_edges(u))
    out_edges_before = fe0.out_edges(node_to_move)
    assert out_edges_before, "Expected outbound edges on greet-root"
    # All targets stay in comp 0 (since we're moving the node to comp 1)
    staying_in_src = {tgt for _, tgt in out_edges_before}

    dst_name = comps[1]["name"]
    result = mutate.move_node(bundle, {
        "node": {"uuid": node_to_move},
        "to_component": dst_name,
    }, MINTER)

    dropped = result["dropped_cross_edges"]
    assert dropped, "Expected at least one dropped cross-boundary edge"

    dropped_targets = {tgt for _, tgt in dropped}
    # All reported dropped targets must have been in src comp
    assert dropped_targets.issubset(staying_in_src), (
        "Dropped edges should be the ones to nodes that stayed in src"
    )

    # The moved node in comp 1 must NOT have any routes pointing to src nodes
    comps_after = get_components(bundle)
    fe1_after = FlowEditor(comps_after[1])
    routes_of_moved = fe1_after.routes.get(node_to_move, {})
    details_b = comps_after[1]["details"]  # raw, but we compare uuids
    details_b_parsed = _uw(details_b)
    for edge in routes_of_moved.values():
        tgt = (edge.get("target") or {}).get("uuid")
        if tgt:
            assert tgt in details_b_parsed, (
                "Moved node routes in dest must only target nodes in dest"
            )


def test_move_node_unknown_to_component_raises(tmp_path):
    """move-node: to_component not found raises ValueError."""
    doc = _build_multi(tmp_path)
    bundle = _bundle(doc)

    comps = get_components(bundle)
    fe0 = FlowEditor(comps[0])
    some_node = next(iter(fe0.details))

    with pytest.raises(ValueError, match="NoSuchCanvas|not found"):
        mutate.move_node(bundle, {
            "node": {"uuid": some_node},
            "to_component": "NoSuchCanvas",
        }, MINTER)


def test_move_node_same_component_raises(tmp_path):
    """move-node: src == dst raises ValueError with a clear message."""
    doc = _build_multi(tmp_path)
    bundle = _bundle(doc)

    comps = get_components(bundle)
    fe0 = FlowEditor(comps[0])
    some_node = next(iter(fe0.details))
    src_name = comps[0]["name"]  # same as src

    with pytest.raises(ValueError, match="same"):
        mutate.move_node(bundle, {
            "node": {"uuid": some_node},
            "to_component": src_name,
        }, MINTER)
