import json
from pathlib import Path
from wizcheck.parser import parse_dict
from wizcheck.flowmodel import build_flow_model
from wizcheck.checks import run_all_checks

FIX = Path(__file__).parent / "fixtures" / "nodes_5_9.json"


def _fm():
    data = json.loads(FIX.read_text(encoding="utf-8"))
    return build_flow_model(data)


def _codes(data):
    wf = parse_dict(data)
    return [f.code for f in run_all_checks(wf)]


def test_type9_is_goto_mr_with_edge():
    fm = _fm()
    nodes = {u: n for c in fm.components for u, n in c.nodes.items()}
    t9 = [n for n in nodes.values() if n.node_type == "goto_mr"]
    assert t9, "type-9 node must classify as goto_mr (not unknown)"
    # it emits exactly one cross-component edge to the Target component
    edges = [b for n in t9 for b in n.branches if b.target_component]
    assert edges, "goto_mr must emit a cross-component edge from multiple_appoint_id"


def test_type5_talk_continue_no_crash_and_appoint_edge():
    fm = _fm()
    nodes = {u: n for c in fm.components for u, n in c.nodes.items()}
    t5 = [n for n in nodes.values() if n.node_type == "talk_continue"]
    assert t5, "type-5 nodes classify as talk_continue"
    # the appoint-bearing type-5 yields a cross-component edge; terminal one does not crash
    assert any(b.target_component for n in t5 for b in n.branches)


def test_wiz110_absent_target_warns():
    data = json.loads(FIX.read_text(encoding="utf-8"))
    # point the type-9 node at a non-existent component uuid
    # Replace only in BizSpeechComponent[0].details (first component's nodes)
    comp = data["BizSpeechComponent"][0]
    details_str = comp["details"]
    details = json.loads(details_str)
    # Find the type-9 node and change its target
    for node_uuid, node_obj in details.items():
        d = node_obj.get("data", {})
        if d.get("type") == 9:
            d["multiple_appoint_id"] = "ffffffff-ffff-ffff-ffff-ffffffffffff"
        elif d.get("type") == 5 and d.get("appoint_node_id"):
            d["appoint_node_id"] = "ffffffff-ffff-ffff-ffff-ffffffffffff"
    comp["details"] = json.dumps(details)
    assert "WIZ110" in _codes(data)


def test_wiz110_clean_when_target_present():
    data = json.loads(FIX.read_text(encoding="utf-8"))
    assert "WIZ110" not in _codes(data)


def test_wiz110_type5_absent_target_warns():
    """WIZ110 independently fires for type-5 (talk_continue) with dangling appoint_node_id."""
    data = json.loads(FIX.read_text(encoding="utf-8"))
    # Point ONLY the type-5 node's appoint_node_id at a non-existent component uuid,
    # leaving the type-9 node's multiple_appoint_id intact
    comp = data["BizSpeechComponent"][0]
    details_str = comp["details"]
    details = json.loads(details_str)
    # Find the type-5 node with appoint_node_id (dddddddd...) and change its target
    for node_uuid, node_obj in details.items():
        d = node_obj.get("data", {})
        if d.get("type") == 5 and d.get("appoint_node_id"):
            d["appoint_node_id"] = "ffffffff-ffff-ffff-ffff-ffffffffffff"
    comp["details"] = json.dumps(details)
    assert "WIZ110" in _codes(data)


def test_wiz111_goto_mr_outside_multiround_warns():
    data = json.loads(FIX.read_text(encoding="utf-8"))
    assert "WIZ111" in _codes(data)  # type-9 node sits in a non-category:2 component


def test_wiz111_clean_when_container_is_multiround():
    data = json.loads(FIX.read_text(encoding="utf-8"))
    # mark every component that holds a type-9 node as category:2
    comps = json.loads(data["BizSpeechComponent"]) if isinstance(data["BizSpeechComponent"], str) else data["BizSpeechComponent"]
    for c in comps:
        det = c.get("details")
        if not det or det in ("null", ""):
            continue
        tree = json.loads(det) if isinstance(det, str) else det
        if any((n.get("data") or {}).get("type") == 9 for n in tree.values()):
            c["category"] = 2
    data["BizSpeechComponent"] = json.dumps(comps) if isinstance(data["BizSpeechComponent"], str) else comps
    assert "WIZ111" not in _codes(data)
