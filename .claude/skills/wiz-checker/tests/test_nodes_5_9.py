import json
from pathlib import Path
from wizcheck.parser import parse_dict
from wizcheck.flowmodel import build_flow_model

FIX = Path(__file__).parent / "fixtures" / "nodes_5_9.json"


def _fm():
    data = json.loads(FIX.read_text(encoding="utf-8"))
    return build_flow_model(data)


def test_type9_is_talk_goto_with_edge():
    fm = _fm()
    nodes = {u: n for c in fm.components for u, n in c.nodes.items()}
    t9 = [n for n in nodes.values() if n.node_type == "talk_goto"]
    assert t9, "type-9 node must classify as talk_goto (not unknown)"
    # it emits exactly one cross-component edge to the Target component
    edges = [b for n in t9 for b in n.branches if b.target_component]
    assert edges, "talk_goto must emit a cross-component edge from multiple_appoint_id"


def test_type5_talk_continue_no_crash_and_appoint_edge():
    fm = _fm()
    nodes = {u: n for c in fm.components for u, n in c.nodes.items()}
    t5 = [n for n in nodes.values() if n.node_type == "talk_continue"]
    assert t5, "type-5 nodes classify as talk_continue"
    # the appoint-bearing type-5 yields a cross-component edge; terminal one does not crash
    assert any(b.target_component for n in t5 for b in n.branches)
